"""Tests for statement processing pipeline."""

from types import SimpleNamespace
from unittest.mock import patch

from erpocr_integration.statement_api import (
	_populate_ocr_statement,
	_reconcile_statements_for_pi,
	_run_statement_matching,
	update_statements_on_pi_submit,
)


class TestPopulateOcrStatement:
	def test_populates_header_fields(self):
		doc = SimpleNamespace(items=[], append=lambda t, r: doc.items.append(SimpleNamespace(**r)))
		extracted = {
			"header_fields": {
				"supplier_name": "Louma Trading",
				"statement_date": "2026-02-28",
				"period_from": "2026-02-01",
				"period_to": "2026-02-28",
				"opening_balance": 5000.0,
				"closing_balance": 12000.0,
				"currency": "ZAR",
			},
			"transactions": [
				{
					"reference": "INV-001",
					"date": "2026-02-05",
					"description": "Tax Invoice",
					"debit": 1000.0,
					"credit": 0.0,
					"balance": 6000.0,
				},
			],
			"raw_response": "{}",
		}

		_populate_ocr_statement(doc, extracted)

		assert doc.supplier_name_ocr == "Louma Trading"
		assert doc.statement_date == "2026-02-28"
		assert doc.opening_balance == 5000.0
		assert doc.closing_balance == 12000.0
		assert len(doc.items) == 1
		assert doc.items[0].reference == "INV-001"

	def test_handles_missing_fields(self):
		doc = SimpleNamespace(items=[], append=lambda t, r: doc.items.append(SimpleNamespace(**r)))
		extracted = {
			"header_fields": {"supplier_name": "Test"},
			"transactions": [
				{
					"reference": "X",
					"date": None,
					"description": "",
					"debit": 0,
					"credit": 0,
					"balance": 0,
				}
			],
			"raw_response": "",
		}

		_populate_ocr_statement(doc, extracted)

		assert doc.supplier_name_ocr == "Test"
		assert doc.opening_balance == 0.0

	def test_populates_multiple_transactions(self):
		doc = SimpleNamespace(items=[], append=lambda t, r: doc.items.append(SimpleNamespace(**r)))
		extracted = {
			"header_fields": {"supplier_name": "ACME Corp", "currency": "USD"},
			"transactions": [
				{
					"reference": "INV-A",
					"date": "2026-01-10",
					"description": "Invoice A",
					"debit": 500.0,
					"credit": 0.0,
					"balance": 500.0,
				},
				{
					"reference": "PMT-001",
					"date": "2026-01-15",
					"description": "Payment received",
					"debit": 0.0,
					"credit": 500.0,
					"balance": 0.0,
				},
			],
			"raw_response": "{}",
		}

		_populate_ocr_statement(doc, extracted)

		assert len(doc.items) == 2
		assert doc.items[0].debit == 500.0
		assert doc.items[1].credit == 500.0
		assert doc.currency == "USD"

	def test_sets_raw_payload(self):
		doc = SimpleNamespace(items=[], append=lambda t, r: doc.items.append(SimpleNamespace(**r)))
		extracted = {
			"header_fields": {"supplier_name": "Test"},
			"transactions": [],
			"raw_response": '{"raw": true}',
		}

		_populate_ocr_statement(doc, extracted)

		assert doc.raw_payload == '{"raw": true}'

	def test_none_numeric_fields_default_to_zero(self):
		doc = SimpleNamespace(items=[], append=lambda t, r: doc.items.append(SimpleNamespace(**r)))
		extracted = {
			"header_fields": {
				"supplier_name": "Test",
				"opening_balance": None,
				"closing_balance": None,
			},
			"transactions": [],
			"raw_response": "",
		}

		_populate_ocr_statement(doc, extracted)

		assert doc.opening_balance == 0.0
		assert doc.closing_balance == 0.0


class TestRunStatementMatching:
	def test_matches_supplier_via_alias(self, mock_frappe):
		doc = SimpleNamespace(supplier_name_ocr="Louma Trading", supplier=None, supplier_match_status=None)

		with patch(
			"erpocr_integration.tasks.matching.match_supplier",
			return_value=("SUP-LOUMA", "Auto Matched"),
		):
			_run_statement_matching(doc)

		assert doc.supplier == "SUP-LOUMA"
		assert doc.supplier_match_status == "Auto Matched"

	def test_unmatched_supplier(self, mock_frappe):
		doc = SimpleNamespace(supplier_name_ocr="Unknown Corp", supplier=None, supplier_match_status=None)

		mock_settings = SimpleNamespace(matching_threshold=80)
		mock_frappe.get_single.return_value = mock_settings

		with patch("erpocr_integration.tasks.matching.match_supplier", return_value=(None, "Unmatched")):
			with patch(
				"erpocr_integration.tasks.matching.match_supplier_fuzzy",
				return_value=(None, "Unmatched", 0),
			):
				_run_statement_matching(doc)

		assert doc.supplier_match_status == "Unmatched"
		assert doc.supplier is None

	def test_falls_back_to_fuzzy_match(self, mock_frappe):
		doc = SimpleNamespace(supplier_name_ocr="Louma Tradng", supplier=None, supplier_match_status=None)

		mock_settings = SimpleNamespace(matching_threshold=80)
		mock_frappe.get_single.return_value = mock_settings

		with patch("erpocr_integration.tasks.matching.match_supplier", return_value=(None, "Unmatched")):
			with patch(
				"erpocr_integration.tasks.matching.match_supplier_fuzzy",
				return_value=("SUP-LOUMA", "Suggested", 92),
			):
				_run_statement_matching(doc)

		assert doc.supplier == "SUP-LOUMA"
		assert doc.supplier_match_status == "Suggested"

	def test_empty_supplier_name_sets_unmatched(self, mock_frappe):
		doc = SimpleNamespace(supplier_name_ocr="", supplier=None, supplier_match_status=None)

		_run_statement_matching(doc)

		assert doc.supplier_match_status == "Unmatched"
		assert doc.supplier is None

	def test_uses_default_threshold_when_not_set(self, mock_frappe):
		doc = SimpleNamespace(supplier_name_ocr="Some Supplier", supplier=None, supplier_match_status=None)

		mock_settings = SimpleNamespace(matching_threshold=None)
		mock_frappe.get_single.return_value = mock_settings

		with patch("erpocr_integration.tasks.matching.match_supplier", return_value=(None, "Unmatched")):
			with patch(
				"erpocr_integration.tasks.matching.match_supplier_fuzzy",
				return_value=(None, "Unmatched", 0),
			) as mock_fuzzy:
				_run_statement_matching(doc)
				# Should be called with default threshold of 80
				mock_fuzzy.assert_called_once_with("Some Supplier", 80)


class TestReconcileStatementsForPi:
	def test_returns_empty_when_no_supplier(self, mock_frappe):
		pi = SimpleNamespace(supplier=None)
		assert _reconcile_statements_for_pi(pi) == []
		mock_frappe.get_all.assert_not_called()

	def test_only_touches_reconciled_statements(self, mock_frappe):
		"""Query must filter to status=Reconciled (not Reviewed)."""
		pi = SimpleNamespace(supplier="SUP-001")
		mock_frappe.get_all.return_value = []

		_reconcile_statements_for_pi(pi)

		call = mock_frappe.get_all.call_args_list[0]
		filters = call.kwargs.get("filters") or call.args[1] if len(call.args) > 1 else call.kwargs["filters"]
		assert filters == {"supplier": "SUP-001", "status": "Reconciled"}

	def test_rereconciles_each_matching_statement(self, mock_frappe):
		pi = SimpleNamespace(supplier="SUP-001")
		mock_frappe.get_all.return_value = [{"name": "OCR-STMT-001"}, {"name": "OCR-STMT-002"}]

		stmt1 = SimpleNamespace(
			name="OCR-STMT-001",
			items=[
				SimpleNamespace(
					recon_status="Missing from ERPNext",
					matched_invoice="",
					erp_amount=0,
					erp_outstanding=0,
					difference=0,
				),
				SimpleNamespace(
					recon_status="Not in Statement",
					matched_invoice="PINV-old",
					erp_amount=0,
					erp_outstanding=0,
					difference=0,
				),
			],
			reverse_check_skipped=1,
			save=lambda **kw: None,
		)
		stmt2 = SimpleNamespace(
			name="OCR-STMT-002", items=[], reverse_check_skipped=0, save=lambda **kw: None
		)
		mock_frappe.get_doc.side_effect = [stmt1, stmt2]

		with patch("erpocr_integration.tasks.reconcile.reconcile_statement") as mock_reconcile:
			touched = _reconcile_statements_for_pi(pi)

		assert touched == ["OCR-STMT-001", "OCR-STMT-002"]
		# Prior "Not in Statement" rows must be dropped so reconcile can re-seed them
		assert all(getattr(i, "recon_status", "") != "Not in Statement" for i in stmt1.items)
		# reverse_check_skipped reset
		assert stmt1.reverse_check_skipped == 0
		assert mock_reconcile.call_count == 2

	def test_submit_hook_never_raises(self, mock_frappe):
		"""PI submit must never fail because statement reconciliation fails."""
		pi = SimpleNamespace(supplier="SUP-001")
		mock_frappe.get_all.side_effect = RuntimeError("boom")

		# Should not raise even though get_all blew up
		update_statements_on_pi_submit(pi)
		mock_frappe.log_error.assert_called_once()

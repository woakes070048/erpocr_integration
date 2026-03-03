"""Tests for OCR Fleet Slip controller (status, PI/JE creation, unlink, no action)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from erpocr_integration.erpnext_ocr.doctype.ocr_fleet_slip.ocr_fleet_slip import (
	OCRFleetSlip,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockSettings(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


def _make_settings(**overrides):
	defaults = dict(
		default_company="Test Company",
		default_cost_center="Main - TC",
		default_tax_template="SA VAT 15%",
		non_vat_tax_template="Non-VAT",
		fleet_fuel_item="FUEL-001",
		fleet_toll_item="TOLL-001",
		fleet_expense_account="5000 - Fuel Expense - TC",
		fleet_default_supplier="Default Supplier",
		default_item="DEFAULT-ITEM",
	)
	defaults.update(overrides)
	return _MockSettings(**defaults)


def _make_fleet_slip(**overrides):
	"""Create an OCRFleetSlip instance with sensible defaults."""
	doc = OCRFleetSlip.__new__(OCRFleetSlip)
	doc.name = "OCR-FS-00001"
	doc.status = "Matched"
	doc.slip_type = "Fuel"
	doc.merchant_name_ocr = "Shell Garage"
	doc.transaction_date = "2025-12-15"
	doc.total_amount = 1125.00
	doc.vat_amount = 0
	doc.currency = "ZAR"
	doc.description = ""
	doc.confidence = 92.0
	doc.vehicle_registration = "ABC 123 GP"
	doc.fleet_vehicle = "VEH-001"
	doc.vehicle_match_status = "Auto Matched"
	doc.posting_mode = "Fleet Card"
	doc.fleet_card_supplier = "WesBank"
	doc.expense_account = "3100 - Fleet Control - TC"
	doc.cost_center = "Transport - TC"
	doc.company = "Test Company"
	doc.litres = 50.0
	doc.price_per_litre = 22.50
	doc.fuel_type = "Diesel"
	doc.odometer_reading = 125000
	doc.toll_plaza_name = ""
	doc.route = ""
	doc.unauthorized_flag = 0
	doc.tax_template = ""
	doc.document_type = ""
	doc.purchase_invoice = None
	doc.no_action_reason = None
	doc.drive_link = None
	doc.drive_file_id = None
	doc.drive_folder_path = None
	doc.source_type = "Gemini Drive Scan"
	doc.raw_payload = ""
	doc.save = MagicMock()
	doc.reload = MagicMock()
	doc.db_set = MagicMock()
	doc.has_value_changed = MagicMock(return_value=False)

	for key, value in overrides.items():
		setattr(doc, key, value)
	return doc


# ---------------------------------------------------------------------------
# TestUpdateStatus
# ---------------------------------------------------------------------------


class TestUpdateStatus:
	def test_matched_when_all_ready(self):
		"""Status becomes Matched when data + vehicle + supplier are present."""
		doc = _make_fleet_slip(
			status="Pending",
			merchant_name_ocr="Shell",
			fleet_vehicle="VEH-001",
			fleet_card_supplier="WesBank",
		)
		doc._update_status()
		assert doc.status == "Matched"

	def test_needs_review_with_data_only(self):
		"""Status becomes Needs Review when only data is present."""
		doc = _make_fleet_slip(
			status="Pending",
			merchant_name_ocr="Shell",
			fleet_vehicle=None,
			vehicle_registration="",
			fleet_card_supplier="",
		)
		doc._update_status()
		assert doc.status == "Needs Review"

	def test_needs_review_no_supplier(self):
		"""Status stays Needs Review when supplier is missing."""
		doc = _make_fleet_slip(
			status="Pending",
			merchant_name_ocr="Shell",
			vehicle_registration="ABC",
			fleet_card_supplier="",
		)
		doc._update_status()
		assert doc.status == "Needs Review"

	def test_draft_created_when_pi_linked(self):
		"""Status becomes Draft Created when PI is linked."""
		doc = _make_fleet_slip(
			status="Pending",
			purchase_invoice="PI-00001",
		)
		doc._update_status()
		assert doc.status == "Draft Created"

	def test_preserves_completed(self):
		doc = _make_fleet_slip(status="Completed")
		doc._update_status()
		assert doc.status == "Completed"

	def test_preserves_draft_created(self):
		doc = _make_fleet_slip(status="Draft Created")
		doc._update_status()
		assert doc.status == "Draft Created"

	def test_preserves_no_action(self):
		doc = _make_fleet_slip(status="No Action")
		doc._update_status()
		assert doc.status == "No Action"

	def test_preserves_error(self):
		doc = _make_fleet_slip(status="Error")
		doc._update_status()
		assert doc.status == "Error"

	def test_matched_with_registration_only(self):
		"""Vehicle registration (without fleet_vehicle) counts as vehicle matched."""
		doc = _make_fleet_slip(
			status="Pending",
			merchant_name_ocr="Shell",
			fleet_vehicle=None,
			vehicle_registration="ABC 123",
			fleet_card_supplier="Default Supplier",
		)
		doc._update_status()
		assert doc.status == "Matched"

	def test_matched_from_total_amount(self):
		"""total_amount alone counts as has_data."""
		doc = _make_fleet_slip(
			status="Pending",
			merchant_name_ocr="",
			slip_type="",
			total_amount=100,
			vehicle_registration="ABC",
			fleet_card_supplier="WesBank",
		)
		doc._update_status()
		assert doc.status == "Matched"


# ---------------------------------------------------------------------------
# TestCreatePurchaseInvoice
# ---------------------------------------------------------------------------


class TestCreatePurchaseInvoice:
	def test_creates_pi_draft(self, mock_frappe):
		"""Successfully creates PI draft in fleet card mode."""
		mock_pi = MagicMock()
		mock_pi.name = "PI-00001"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings()
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			posting_mode="Fleet Card",
			fleet_card_supplier="WesBank",
		)
		doc.create_purchase_invoice()

		assert doc.purchase_invoice == "PI-00001"
		assert doc.status == "Draft Created"
		mock_pi.insert.assert_called_once()

	def test_blocks_wrong_status(self, mock_frappe):
		doc = _make_fleet_slip(status="Completed", document_type="Purchase Invoice")
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_blocks_wrong_document_type(self, mock_frappe):
		doc = _make_fleet_slip(status="Matched", document_type="")
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_blocks_no_supplier(self, mock_frappe):
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			fleet_card_supplier="",
		)
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_blocks_no_item(self, mock_frappe):
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings(
			fleet_fuel_item="", fleet_toll_item="", default_item=""
		)
		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
		)
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_blocks_duplicate_creation(self, mock_frappe):
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice="PI-EXISTS")
		doc = _make_fleet_slip(status="Matched", document_type="Purchase Invoice")
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_pi_has_expense_account(self, mock_frappe):
		"""PI item includes expense account when set."""
		mock_pi = MagicMock()
		mock_pi.name = "PI-00001"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings()
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			expense_account="3100 - Fleet Control - TC",
		)
		doc.create_purchase_invoice()

		pi_dict = mock_frappe.get_doc.call_args[0][0]
		assert pi_dict["items"][0]["expense_account"] == "3100 - Fleet Control - TC"

	def test_pi_has_cost_center(self, mock_frappe):
		"""PI item includes cost center when set."""
		mock_pi = MagicMock()
		mock_pi.name = "PI-00001"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings()
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			cost_center="Transport - TC",
		)
		doc.create_purchase_invoice()

		pi_dict = mock_frappe.get_doc.call_args[0][0]
		assert pi_dict["items"][0]["cost_center"] == "Transport - TC"

	def test_pi_cost_center_falls_back_to_settings(self, mock_frappe):
		"""PI item cost center falls back to OCR Settings default."""
		mock_pi = MagicMock()
		mock_pi.name = "PI-00001"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings()
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			cost_center="",  # no cost center on slip
		)
		doc.create_purchase_invoice()

		pi_dict = mock_frappe.get_doc.call_args[0][0]
		assert pi_dict["items"][0]["cost_center"] == "Main - TC"

	def test_pi_with_tax_template(self, mock_frappe):
		"""PI includes tax template when set."""
		mock_tax = MagicMock()
		mock_tax.company = "Test Company"
		mock_tax.taxes = [
			SimpleNamespace(
				category="Total",
				add_deduct_tax="Add",
				charge_type="On Net Total",
				row_id="",
				account_head="2300 - VAT Input - TC",
				description="VAT 15%",
				rate=15.0,
				cost_center="",
				account_currency="ZAR",
				included_in_print_rate=0,
				included_in_paid_amount=0,
			)
		]

		mock_pi = MagicMock()
		mock_pi.name = "PI-00001"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"

		def get_cached_side_effect(doctype, name=None):
			if doctype == "Purchase Taxes and Charges Template":
				return mock_tax
			return _make_settings()

		mock_frappe.get_cached_doc.side_effect = get_cached_side_effect
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Matched",
			document_type="Purchase Invoice",
			tax_template="SA VAT 15%",
		)
		doc.create_purchase_invoice()

		pi_dict = mock_frappe.get_doc.call_args[0][0]
		assert pi_dict["taxes_and_charges"] == "SA VAT 15%"
		assert len(pi_dict["taxes"]) == 1

	def test_pi_permission_check(self, mock_frappe):
		"""Permission check blocks unauthorized PI creation."""
		mock_frappe.has_permission.return_value = False
		doc = _make_fleet_slip(status="Matched", document_type="Purchase Invoice")
		with pytest.raises(Exception):
			doc.create_purchase_invoice()

	def test_needs_review_status_allowed(self, mock_frappe):
		"""PI creation allowed from Needs Review status."""
		mock_pi = MagicMock()
		mock_pi.name = "PI-00002"
		mock_pi.items = [MagicMock()]
		mock_pi.items[0].item_name = "FUEL-001"
		mock_frappe.get_doc.return_value = mock_pi
		mock_frappe.db.get_value.return_value = SimpleNamespace(purchase_invoice=None)
		mock_frappe.get_cached_doc.return_value = _make_settings()
		mock_frappe.get_all.return_value = []

		doc = _make_fleet_slip(
			status="Needs Review",
			document_type="Purchase Invoice",
		)
		doc.create_purchase_invoice()
		assert doc.purchase_invoice == "PI-00002"


# ---------------------------------------------------------------------------
# TestUnlinkDocument
# ---------------------------------------------------------------------------


class TestUnlinkDocument:
	def test_unlinks_pi(self, mock_frappe):
		"""Unlink & Reset deletes draft PI and resets."""
		mock_frappe.db.get_value.return_value = 0  # docstatus=0
		doc = _make_fleet_slip(
			status="Draft Created",
			purchase_invoice="PI-00001",
		)
		doc.unlink_document()

		doc.db_set.assert_any_call("purchase_invoice", "")
		doc.db_set.assert_any_call("document_type", "")
		doc.db_set.assert_any_call("status", "Pending")
		mock_frappe.delete_doc.assert_called_once_with("Purchase Invoice", "PI-00001", force=True)

	def test_blocks_submitted(self, mock_frappe):
		"""Cannot unlink submitted document."""
		mock_frappe.db.get_value.return_value = 1  # submitted
		doc = _make_fleet_slip(
			status="Draft Created",
			purchase_invoice="PI-00001",
		)
		with pytest.raises(Exception):
			doc.unlink_document()

	def test_blocks_non_draft_created(self, mock_frappe):
		"""Cannot unlink when status is not Draft Created."""
		doc = _make_fleet_slip(status="Matched")
		with pytest.raises(Exception):
			doc.unlink_document()

	def test_blocks_no_linked_document(self, mock_frappe):
		"""Cannot unlink when no document is linked."""
		doc = _make_fleet_slip(
			status="Draft Created",
			purchase_invoice=None,
		)
		with pytest.raises(Exception):
			doc.unlink_document()

	def test_unlinks_cancelled_document(self, mock_frappe):
		"""Can unlink a cancelled (docstatus=2) document."""
		mock_frappe.db.get_value.return_value = 2  # cancelled
		doc = _make_fleet_slip(
			status="Draft Created",
			purchase_invoice="PI-CANCELLED",
		)
		doc.unlink_document()

		mock_frappe.delete_doc.assert_called_once()

	def test_permission_check(self, mock_frappe):
		mock_frappe.has_permission.return_value = False
		doc = _make_fleet_slip(status="Draft Created", purchase_invoice="PI-00001")
		with pytest.raises(Exception):
			doc.unlink_document()


# ---------------------------------------------------------------------------
# TestMarkNoAction
# ---------------------------------------------------------------------------


class TestMarkNoAction:
	def test_marks_no_action(self, mock_frappe):
		doc = _make_fleet_slip(status="Needs Review")
		doc.mark_no_action("Unauthorized purchase")
		assert doc.status == "No Action"
		assert doc.no_action_reason == "Unauthorized purchase"

	def test_marks_from_error(self, mock_frappe):
		doc = _make_fleet_slip(status="Error")
		doc.mark_no_action("Bad scan")
		assert doc.status == "No Action"

	def test_marks_from_matched(self, mock_frappe):
		doc = _make_fleet_slip(status="Matched")
		doc.mark_no_action("Not needed")
		assert doc.status == "No Action"

	def test_marks_from_pending(self, mock_frappe):
		doc = _make_fleet_slip(status="Pending")
		doc.mark_no_action("Duplicate")
		assert doc.status == "No Action"

	def test_blocks_from_completed(self, mock_frappe):
		doc = _make_fleet_slip(status="Completed")
		with pytest.raises(Exception):
			doc.mark_no_action("test")

	def test_blocks_from_draft_created(self, mock_frappe):
		doc = _make_fleet_slip(status="Draft Created")
		with pytest.raises(Exception):
			doc.mark_no_action("test")

	def test_requires_reason(self, mock_frappe):
		doc = _make_fleet_slip(status="Needs Review")
		with pytest.raises(Exception):
			doc.mark_no_action("")

	def test_requires_non_whitespace_reason(self, mock_frappe):
		doc = _make_fleet_slip(status="Needs Review")
		with pytest.raises(Exception):
			doc.mark_no_action("   ")

	def test_permission_check(self, mock_frappe):
		mock_frappe.has_permission.return_value = False
		doc = _make_fleet_slip(status="Needs Review")
		with pytest.raises(Exception):
			doc.mark_no_action("reason")


# ---------------------------------------------------------------------------
# TestResolveItem
# ---------------------------------------------------------------------------


class TestResolveItem:
	def test_fuel_slip_uses_fuel_item(self):
		settings = _make_settings()
		doc = _make_fleet_slip(slip_type="Fuel")
		assert doc._resolve_item(settings) == "FUEL-001"

	def test_toll_slip_uses_toll_item(self):
		settings = _make_settings()
		doc = _make_fleet_slip(slip_type="Toll")
		assert doc._resolve_item(settings) == "TOLL-001"

	def test_other_slip_falls_back_to_fuel_item(self):
		settings = _make_settings()
		doc = _make_fleet_slip(slip_type="Other")
		assert doc._resolve_item(settings) == "FUEL-001"

	def test_toll_falls_back_to_fuel_then_default(self):
		settings = _make_settings(fleet_toll_item="", fleet_fuel_item="FUEL-001")
		doc = _make_fleet_slip(slip_type="Toll")
		assert doc._resolve_item(settings) == "FUEL-001"

	def test_toll_falls_back_to_default_item(self):
		settings = _make_settings(fleet_toll_item="", fleet_fuel_item="")
		doc = _make_fleet_slip(slip_type="Toll")
		assert doc._resolve_item(settings) == "DEFAULT-ITEM"

	def test_fuel_falls_back_to_default_item(self):
		settings = _make_settings(fleet_fuel_item="")
		doc = _make_fleet_slip(slip_type="Fuel")
		assert doc._resolve_item(settings) == "DEFAULT-ITEM"

	def test_no_item_configured(self):
		settings = _make_settings(fleet_fuel_item=None, fleet_toll_item=None, default_item=None)
		doc = _make_fleet_slip(slip_type="Fuel")
		assert doc._resolve_item(settings) is None


# ---------------------------------------------------------------------------
# TestBuildDescription
# ---------------------------------------------------------------------------


class TestBuildDescription:
	def test_fuel_description(self):
		doc = _make_fleet_slip(
			slip_type="Fuel",
			merchant_name_ocr="Shell",
			litres=50,
			fuel_type="Diesel",
			price_per_litre=22.50,
			vehicle_registration="ABC 123 GP",
		)
		desc = doc._build_description()
		assert "Fuel" in desc
		assert "Shell" in desc
		assert "50.0L" in desc
		assert "Diesel" in desc
		assert "22.5/L" in desc
		assert "[ABC 123 GP]" in desc

	def test_toll_description(self):
		doc = _make_fleet_slip(
			slip_type="Toll",
			merchant_name_ocr="SANRAL",
			toll_plaza_name="Huguenot Tunnel",
			vehicle_registration="XYZ 789",
		)
		desc = doc._build_description()
		assert "Toll" in desc
		assert "SANRAL" in desc
		assert "Huguenot Tunnel" in desc

	def test_empty_description(self):
		doc = _make_fleet_slip(
			slip_type="",
			merchant_name_ocr="",
			vehicle_registration="",
			litres=0,
			fuel_type="",
		)
		assert doc._build_description() == "Fleet Slip"

	def test_partial_fuel_description(self):
		doc = _make_fleet_slip(
			slip_type="Fuel",
			merchant_name_ocr="",
			litres=0,
			fuel_type="",
			vehicle_registration="ABC",
		)
		desc = doc._build_description()
		assert "Fuel" in desc
		assert "[ABC]" in desc


# ---------------------------------------------------------------------------
# TestCopyScanToDocument
# ---------------------------------------------------------------------------


class TestCopyScanToDocument:
	def test_copies_attachment(self, mock_frappe):
		mock_frappe.get_all.return_value = [
			SimpleNamespace(
				name="FILE-001",
				file_url="/private/files/scan.pdf",
				file_name="scan.pdf",
			)
		]
		mock_file = MagicMock()
		mock_frappe.get_doc.return_value = mock_file

		doc = _make_fleet_slip()
		doc._copy_scan_to_document("Purchase Invoice", "PI-00001")

		assert mock_frappe.get_doc.call_count >= 1

	def test_adds_drive_link_comment(self, mock_frappe):
		mock_frappe.get_all.return_value = []  # no attachments
		mock_doc = MagicMock()
		mock_frappe.get_doc.return_value = mock_doc

		doc = _make_fleet_slip(
			drive_link="https://drive.google.com/test",
			drive_folder_path="2025/12/Fleet Slips",
		)
		doc._copy_scan_to_document("Purchase Invoice", "PI-00001")

		mock_doc.add_comment.assert_called_once()
		comment_text = mock_doc.add_comment.call_args[0][1]
		assert "Google Drive" in comment_text

	def test_no_error_on_failure(self, mock_frappe):
		"""Copy scan failure should not raise."""
		mock_frappe.get_all.side_effect = Exception("File lookup failed")

		doc = _make_fleet_slip()
		# Should not raise
		doc._copy_scan_to_document("Purchase Invoice", "PI-00001")


# ---------------------------------------------------------------------------
# TestApplyVehicleConfigFromLink
# ---------------------------------------------------------------------------


class TestApplyVehicleConfigFromLink:
	def test_applies_fleet_card_config(self, mock_frappe):
		mock_frappe.db.exists.return_value = True
		mock_frappe.db.get_value.return_value = SimpleNamespace(
			name="VEH-001",
			registration="ABC 123",
			custom_fleet_card_provider="WesBank",
			custom_fleet_control_account="3100 - Control - TC",
			custom_cost_center="Transport - TC",
		)
		mock_frappe.get_cached_doc.return_value = _make_settings()

		doc = _make_fleet_slip(
			fleet_vehicle="VEH-001",
			vehicle_match_status="Confirmed",
			posting_mode="",
		)
		doc._apply_vehicle_config_from_link()

		assert doc.posting_mode == "Fleet Card"
		assert doc.fleet_card_supplier == "WesBank"

	def test_applies_direct_expense_config(self, mock_frappe):
		mock_frappe.db.exists.return_value = True
		mock_frappe.db.get_value.return_value = SimpleNamespace(
			name="VEH-002",
			registration="XYZ 789",
			custom_fleet_card_provider="",
			custom_fleet_control_account="",
			custom_cost_center="Head Office - TC",
		)
		mock_frappe.get_cached_doc.return_value = _make_settings()

		doc = _make_fleet_slip(
			fleet_vehicle="VEH-002",
			vehicle_match_status="Confirmed",
			posting_mode="",
		)
		doc._apply_vehicle_config_from_link()

		assert doc.posting_mode == "Direct Expense"
		assert doc.fleet_card_supplier == "Default Supplier"
		assert doc.expense_account == "5000 - Fuel Expense - TC"

	def test_skips_when_no_fleet_vehicle_doctype(self, mock_frappe):
		mock_frappe.db.exists.return_value = False

		doc = _make_fleet_slip(posting_mode="")
		doc._apply_vehicle_config_from_link()

		assert doc.posting_mode == ""  # unchanged

	def test_skips_when_vehicle_not_found(self, mock_frappe):
		mock_frappe.db.exists.return_value = True
		mock_frappe.db.get_value.return_value = None

		doc = _make_fleet_slip(posting_mode="")
		doc._apply_vehicle_config_from_link()

		assert doc.posting_mode == ""  # unchanged

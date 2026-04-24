"""Tests for OCR stats API endpoint."""

import pytest

from erpocr_integration.stats_api import _compute_stats, get_ocr_stats


class TestComputeStats:
	def test_touchless_rate_all_auto_drafted(self):
		records = [
			{"status": "Draft Created", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
		]
		stats = _compute_stats(records)
		assert stats["touchless_draft_rate"] == 100.0

	def test_touchless_rate_mixed(self):
		records = [
			{"status": "Draft Created", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
			{"status": "Needs Review", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Email"},
			{"status": "Completed", "auto_drafted": 1, "source_type": "Gemini Email"},
		]
		stats = _compute_stats(records)
		assert stats["touchless_draft_rate"] == 50.0

	def test_touchless_rate_zero_records(self):
		stats = _compute_stats([])
		assert stats["touchless_draft_rate"] == 0.0

	def test_exception_rate(self):
		records = [
			{"status": "Needs Review", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
			{"status": "Matched", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
		]
		stats = _compute_stats(records)
		assert stats["exception_rate"] == pytest.approx(66.7, abs=0.1)

	def test_volume_by_source(self):
		records = [
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Email"},
		]
		stats = _compute_stats(records)
		assert stats["by_source"]["Gemini Drive Scan"] == 2
		assert stats["by_source"]["Gemini Email"] == 1

	def test_status_breakdown(self):
		records = [
			{"status": "Completed", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
			{"status": "Needs Review", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Error", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
		]
		stats = _compute_stats(records)
		assert stats["by_status"]["Completed"] == 1
		assert stats["by_status"]["Needs Review"] == 1
		assert stats["by_status"]["Error"] == 1

	def test_manual_count(self):
		records = [
			{"status": "Completed", "auto_drafted": 1, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
			{"status": "Completed", "auto_drafted": 0, "source_type": "Gemini Drive Scan"},
		]
		stats = _compute_stats(records)
		assert stats["auto_drafted_count"] == 1
		assert stats["manual_count"] == 2


class TestRoleGate:
	"""Exercises the role gate + date-window validation in get_ocr_stats().

	The endpoint calls frappe.utils.getdate / add_days / today via attribute
	access on the frappe mock, then compares the results (> and subtraction),
	so the mock must return real datetime.date objects for that to succeed.
	"""

	@staticmethod
	def _install_date_mocks(mock_frappe):
		import datetime

		today = datetime.date(2026, 4, 24)
		mock_frappe.utils.today.return_value = today
		mock_frappe.utils.add_days.side_effect = lambda d, n: (
			(d if isinstance(d, datetime.date) else today) + datetime.timedelta(days=n)
		)
		mock_frappe.utils.getdate.side_effect = lambda v=None: v if isinstance(v, datetime.date) else today

	def test_accounts_manager_allowed(self, mock_frappe):
		mock_frappe.get_roles.return_value = ["Accounts Manager", "Employee"]
		mock_frappe.get_all.return_value = []
		self._install_date_mocks(mock_frappe)
		result = get_ocr_stats()
		assert result["total"] == 0

	def test_system_manager_allowed(self, mock_frappe):
		mock_frappe.get_roles.return_value = ["System Manager"]
		mock_frappe.get_all.return_value = []
		self._install_date_mocks(mock_frappe)
		result = get_ocr_stats()
		assert result["total"] == 0

	def test_other_roles_rejected(self, mock_frappe):
		mock_frappe.get_roles.return_value = ["OCR Manager", "Accounts User"]
		with pytest.raises(Exception):
			get_ocr_stats()

	def test_rejects_inverted_date_range(self, mock_frappe):
		mock_frappe.get_roles.return_value = ["System Manager"]
		self._install_date_mocks(mock_frappe)
		import datetime

		with pytest.raises(Exception):
			get_ocr_stats(
				from_date=datetime.date(2026, 4, 24),
				to_date=datetime.date(2026, 3, 1),
			)

	def test_rejects_oversized_range(self, mock_frappe):
		mock_frappe.get_roles.return_value = ["System Manager"]
		self._install_date_mocks(mock_frappe)
		import datetime

		with pytest.raises(Exception):
			get_ocr_stats(
				from_date=datetime.date(2024, 1, 1),
				to_date=datetime.date(2026, 4, 24),
			)

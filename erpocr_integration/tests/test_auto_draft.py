"""Tests for auto-draft logic."""

from types import SimpleNamespace

from erpocr_integration.tasks.auto_draft import _is_high_confidence


def _make_ocr_import(**overrides):
	"""Create a minimal OCR Import-like object for testing."""
	defaults = dict(
		supplier="SUP-001",
		supplier_match_status="Auto Matched",
		items=[],
		status="Matched",
	)
	defaults.update(overrides)
	return SimpleNamespace(**defaults)


def _make_item(**overrides):
	defaults = dict(
		item_code="ITEM-001",
		match_status="Auto Matched",
		description_ocr="Test item",
	)
	defaults.update(overrides)
	return SimpleNamespace(**defaults)


class TestIsHighConfidence:
	def test_high_confidence_all_auto_matched(self):
		doc = _make_ocr_import(items=[_make_item()])
		is_high, reason = _is_high_confidence(doc)
		assert is_high is True
		assert reason == ""

	def test_high_confidence_confirmed_supplier(self):
		doc = _make_ocr_import(
			supplier_match_status="Confirmed",
			items=[_make_item()],
		)
		is_high, _ = _is_high_confidence(doc)
		assert is_high is True

	def test_low_confidence_fuzzy_supplier(self):
		doc = _make_ocr_import(
			supplier_match_status="Suggested",
			items=[_make_item()],
		)
		is_high, reason = _is_high_confidence(doc)
		assert is_high is False
		assert "supplier" in reason.lower()

	def test_low_confidence_unmatched_supplier(self):
		doc = _make_ocr_import(
			supplier_match_status="Unmatched",
			supplier=None,
			items=[_make_item()],
		)
		is_high, _ = _is_high_confidence(doc)
		assert is_high is False

	def test_low_confidence_no_supplier(self):
		doc = _make_ocr_import(supplier=None, items=[_make_item()])
		is_high, _ = _is_high_confidence(doc)
		assert is_high is False

	def test_low_confidence_fuzzy_item(self):
		doc = _make_ocr_import(
			items=[_make_item(match_status="Suggested")],
		)
		is_high, reason = _is_high_confidence(doc)
		assert is_high is False
		assert "item" in reason.lower()

	def test_low_confidence_unmatched_item(self):
		doc = _make_ocr_import(
			items=[_make_item(item_code=None, match_status="Unmatched")],
		)
		is_high, _ = _is_high_confidence(doc)
		assert is_high is False

	def test_low_confidence_no_items(self):
		doc = _make_ocr_import(items=[])
		is_high, reason = _is_high_confidence(doc)
		assert is_high is False
		assert "no items" in reason.lower()

	def test_mixed_items_one_fuzzy(self):
		doc = _make_ocr_import(
			items=[
				_make_item(item_code="A", match_status="Auto Matched"),
				_make_item(item_code="B", match_status="Suggested"),
			],
		)
		is_high, _ = _is_high_confidence(doc)
		assert is_high is False

	def test_all_items_service_mapped(self):
		"""Service mapping returns 'Auto Matched' — should be high confidence."""
		doc = _make_ocr_import(
			items=[_make_item(match_status="Auto Matched")],
		)
		is_high, _ = _is_high_confidence(doc)
		assert is_high is True

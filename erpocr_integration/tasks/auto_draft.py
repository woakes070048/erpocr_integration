"""Auto-draft logic for high-confidence OCR Imports.

When extraction + matching produces high-confidence results (alias/exact matches,
not fuzzy), automatically creates the PI/PR draft — eliminating the manual
"review and click Create" ceremony.
"""

# High-confidence match statuses (NOT "Suggested" or "Unmatched")
_HIGH_CONFIDENCE_STATUSES = frozenset({"Auto Matched", "Confirmed"})


def _is_high_confidence(ocr_import) -> tuple[bool, str]:
	"""Check if an OCR Import has high-confidence matches suitable for auto-draft.

	Returns:
	    (is_high_confidence, reason_if_not)
	"""
	# Supplier must be resolved with high confidence
	if not ocr_import.supplier:
		return False, "No supplier matched"
	if ocr_import.supplier_match_status not in _HIGH_CONFIDENCE_STATUSES:
		return False, f"Supplier match is '{ocr_import.supplier_match_status}' (needs alias or exact)"

	# Must have at least one item
	if not ocr_import.items:
		return False, "No items extracted"

	# All items must be high-confidence matched
	for item in ocr_import.items:
		if item.match_status not in _HIGH_CONFIDENCE_STATUSES:
			return False, f"Item '{item.description_ocr or '?'}' match is '{item.match_status}'"
		if not item.item_code:
			return False, f"Item '{item.description_ocr or '?'}' has no item_code"

	return True, ""

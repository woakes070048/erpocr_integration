"""Auto-draft logic for high-confidence OCR Imports.

When extraction + matching produces high-confidence results (alias/exact matches,
not fuzzy), automatically creates the PI/PR draft — eliminating the manual
"review and click Create" ceremony.
"""

import frappe

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


def _auto_link_purchase_order(ocr_import) -> bool:
	"""Attempt to find and link an open PO for this OCR Import.

	Searches open POs by supplier + company, picks the one where all OCR item_codes
	appear in PO items. Sets `ocr_import.purchase_order` if found.

	Returns:
	    True if a PO was linked (or already linked), False otherwise.
	"""
	if ocr_import.purchase_order:
		return True  # Already linked

	if not ocr_import.supplier or not ocr_import.company:
		return False

	ocr_item_codes = {item.item_code for item in ocr_import.items if item.item_code}
	if not ocr_item_codes:
		return False

	# Find open POs for this supplier
	open_pos = frappe.get_list(
		"Purchase Order",
		filters={
			"supplier": ocr_import.supplier,
			"company": ocr_import.company,
			"docstatus": 1,
			"status": ["in", ["To Receive and Bill", "To Receive", "To Bill"]],
		},
		fields=["name", "transaction_date", "grand_total", "status"],
		order_by="transaction_date desc",
		limit_page_length=20,
		ignore_permissions=True,
	)

	if not open_pos:
		return False

	# Find PO where all OCR items have matching PO items
	best_po = None
	for po in open_pos:
		po_doc = frappe.get_doc("Purchase Order", po.name)
		po_item_codes = {item.item_code for item in po_doc.items}

		if ocr_item_codes.issubset(po_item_codes):
			best_po = po.name
			break  # First full match wins (most recent due to ordering)

	if best_po:
		ocr_import.purchase_order = best_po
		return True

	return False


def _auto_detect_document_type(ocr_import) -> str:
	"""Auto-detect the appropriate document type for this OCR Import.

	Current logic: always returns Purchase Invoice. PI is the safest default
	because it accepts unmatched items via default_item, doesn't require
	warehouse config, and is the most common document type.

	Future: could detect PR (all stock items + PO) or JE (expense receipts).
	"""
	return "Purchase Invoice"

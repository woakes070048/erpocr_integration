"""OCR stats API — aggregation endpoint for the stats dashboard.

Role-gated to System Manager + Accounts Manager (owner/finance roles).
Not visible to regular accounts users or the OCR Manager operations role.
"""

import frappe
from frappe import _

_STATS_ROLES = frozenset({"System Manager", "Accounts Manager"})


@frappe.whitelist()
def get_ocr_stats(from_date=None, to_date=None):
	"""Return OCR processing statistics for the stats dashboard.

	Args:
	    from_date: Start date filter (default: 90 days ago)
	    to_date: End date filter (default: today)
	"""
	if not _STATS_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only System Managers and Accounts Managers can view OCR stats."))

	# Validate + clamp the window. Arbitrary date strings from the client
	# (or no client at all, via direct API call) could widen the scan beyond
	# useful — cap the range at 365 days and reject unparseable input.
	try:
		from_date = (
			frappe.utils.getdate(from_date)
			if from_date
			else frappe.utils.getdate(frappe.utils.add_days(frappe.utils.today(), -90))
		)
		to_date = frappe.utils.getdate(to_date) if to_date else frappe.utils.getdate(frappe.utils.today())
	except Exception:
		frappe.throw(_("Invalid date range."))

	if from_date > to_date:
		frappe.throw(_("from_date must be on or before to_date."))
	if (to_date - from_date).days > 365:
		frappe.throw(_("Date range cannot exceed 365 days."))

	records = frappe.get_all(
		"OCR Import",
		filters={"creation": ["between", [from_date, to_date]]},
		fields=[
			"name",
			"status",
			"auto_drafted",
			"source_type",
			"supplier",
			"supplier_match_status",
			"creation",
			"auto_draft_skipped_reason",
		],
		limit_page_length=0,
		ignore_permissions=True,
	)

	stats = _compute_stats(records)
	stats["from_date"] = str(from_date)
	stats["to_date"] = str(to_date)
	return stats


def _compute_stats(records: list[dict]) -> dict:
	"""Compute aggregate stats from a list of OCR Import records."""
	total = len(records)
	if total == 0:
		return {
			"total": 0,
			"touchless_draft_rate": 0.0,
			"exception_rate": 0.0,
			"by_status": {},
			"by_source": {},
			"auto_drafted_count": 0,
			"manual_count": 0,
		}

	auto_drafted = sum(1 for r in records if r.get("auto_drafted"))
	# Exception = anything that needs/needed manual intervention
	# (Needs Review, Matched without auto_drafted, Error)
	exceptions = sum(
		1
		for r in records
		if not r.get("auto_drafted") and r.get("status") in ("Needs Review", "Matched", "Error")
	)

	by_status = {}
	by_source = {}
	for r in records:
		status = r.get("status", "Unknown")
		by_status[status] = by_status.get(status, 0) + 1
		source = r.get("source_type", "Unknown")
		by_source[source] = by_source.get(source, 0) + 1

	return {
		"total": total,
		"touchless_draft_rate": round(auto_drafted / total * 100, 1) if total else 0.0,
		"exception_rate": round(exceptions / total * 100, 1) if total else 0.0,
		"by_status": by_status,
		"by_source": by_source,
		"auto_drafted_count": auto_drafted,
		"manual_count": total - auto_drafted,
	}

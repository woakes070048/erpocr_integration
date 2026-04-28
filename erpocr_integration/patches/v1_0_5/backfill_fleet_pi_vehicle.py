"""Manual-trigger backfill: tag historical Purchase Invoices created from
OCR Fleet Slips with their fleet_vehicle.

NOT registered in patches.txt — this is intentionally a manual one-shot. Run
when fleet_management is installed and the operator is ready to consolidate
historical fleet PIs into the vehicle-level cost reports.

Usage:
    bench --site <site> execute \\
        erpocr_integration.patches.v1_0_5.backfill_fleet_pi_vehicle.execute

Scope:
    - Only Purchase Invoices with posting_date >= 2026-01-01 (fleet_management
      data scope; older PIs aren't tracked in vehicle reports anyway).
    - Only PIs whose custom_fleet_vehicle is currently empty (idempotent —
      safe to re-run; will not overwrite manual edits).
    - Only PIs reachable from an OCR Fleet Slip whose fleet_vehicle is set.

Implementation notes:
    - Writes via frappe.db.set_value with update_modified=False — does NOT
      bump the PI's modified timestamp or write a Version log entry. This is
      a deliberate trade-off: the source of truth (the OCR Fleet Slip with
      its fleet_vehicle link) is preserved, and we don't want to noisy-up
      the PI audit trail with a synthetic system change.
    - Feature-detect: bails out early with a clear message if the
      custom_fleet_vehicle field doesn't exist on Purchase Invoice (i.e.,
      fleet_management isn't installed on this site).
"""

import frappe

BACKFILL_FROM_DATE = "2026-01-01"


def execute():
	if not frappe.get_meta("Purchase Invoice").has_field("custom_fleet_vehicle"):
		print(
			"Purchase Invoice has no custom_fleet_vehicle field. "
			"fleet_management is not installed on this site — nothing to backfill."
		)
		return

	slips = frappe.get_all(
		"OCR Fleet Slip",
		filters={
			"purchase_invoice": ["is", "set"],
			"fleet_vehicle": ["is", "set"],
		},
		fields=["name", "purchase_invoice", "fleet_vehicle"],
	)

	if not slips:
		print("No OCR Fleet Slips with linked Purchase Invoices found. Nothing to do.")
		return

	updated = 0
	skipped_already_tagged = 0
	skipped_out_of_scope = 0
	skipped_pi_missing = 0

	for slip in slips:
		pi = frappe.db.get_value(
			"Purchase Invoice",
			slip.purchase_invoice,
			["name", "posting_date", "custom_fleet_vehicle"],
			as_dict=True,
		)
		if not pi:
			skipped_pi_missing += 1
			continue
		if str(pi.posting_date) < BACKFILL_FROM_DATE:
			skipped_out_of_scope += 1
			continue
		if pi.custom_fleet_vehicle:
			skipped_already_tagged += 1
			continue

		frappe.db.set_value(
			"Purchase Invoice",
			pi.name,
			"custom_fleet_vehicle",
			slip.fleet_vehicle,
			update_modified=False,
		)
		updated += 1

	frappe.db.commit()  # nosemgrep

	print(
		f"Fleet PI backfill complete: {updated} updated, "
		f"{skipped_already_tagged} already tagged, "
		f"{skipped_out_of_scope} out of scope (posting_date < {BACKFILL_FROM_DATE}), "
		f"{skipped_pi_missing} PI not found."
	)

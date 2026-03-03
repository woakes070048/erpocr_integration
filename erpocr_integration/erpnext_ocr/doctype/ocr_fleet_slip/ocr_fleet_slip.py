# Copyright (c) 2025, ERPNext OCR Integration Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class OCRFleetSlip(Document):
	def before_save(self):
		self._update_status()

	def _update_status(self):
		"""Auto-update status based on current state."""
		if self.status in ("Completed", "Draft Created", "No Action", "Error"):
			return

		# If PI or JE already created, mark as Draft Created
		if self.purchase_invoice or self.journal_entry:
			self.status = "Draft Created"
			return

		# Check readiness for document creation
		has_data = bool(self.merchant_name_ocr or self.total_amount or self.slip_type)
		vehicle_matched = bool(self.fleet_vehicle) or bool(self.vehicle_registration)
		posting_ready = bool(self.posting_mode)

		if has_data and vehicle_matched and posting_ready:
			self.status = "Matched"
		elif has_data:
			self.status = "Needs Review"

	def on_update(self):
		"""Save vehicle alias when user confirms a vehicle match."""
		# When user manually links a Fleet Vehicle, re-apply config
		if self.has_value_changed("fleet_vehicle") and self.fleet_vehicle:
			if self.vehicle_match_status == "Confirmed":
				self._apply_vehicle_config_from_link()

	def _apply_vehicle_config_from_link(self):
		"""Re-apply posting config when user manually links a Fleet Vehicle."""
		if not frappe.db.exists("DocType", "Fleet Vehicle"):
			return

		vehicle = frappe.db.get_value(
			"Fleet Vehicle",
			self.fleet_vehicle,
			[
				"name",
				"registration",
				"custom_fleet_card_provider",
				"custom_fleet_control_account",
				"custom_cost_center",
			],
			as_dict=True,
		)
		if not vehicle:
			return

		settings = frappe.get_cached_doc("OCR Settings")

		if vehicle.custom_fleet_card_provider:
			self.posting_mode = "Fleet Card"
			self.fleet_card_supplier = vehicle.custom_fleet_card_provider
			self.expense_account = vehicle.custom_fleet_control_account
		else:
			self.posting_mode = "Direct Expense"
			self.expense_account = settings.get("fleet_expense_account")
			self.credit_account = settings.get("fleet_credit_account")

		if vehicle.custom_cost_center:
			self.cost_center = vehicle.custom_cost_center

	@frappe.whitelist()
	def create_purchase_invoice(self):
		"""Create a Purchase Invoice draft for fleet card mode."""
		if not frappe.has_permission("Purchase Invoice", "create"):
			frappe.throw(_("You don't have permission to create Purchase Invoices."))

		if self.status not in ("Matched", "Needs Review"):
			frappe.throw(
				_("Cannot create Purchase Invoice from a record with status '{0}'.").format(self.status)
			)

		if self.document_type != "Purchase Invoice":
			frappe.throw(_("Document Type must be 'Purchase Invoice' to create a Purchase Invoice."))

		# Row-lock to prevent duplicate creation
		current = frappe.db.get_value(
			"OCR Fleet Slip",
			self.name,
			["purchase_invoice", "journal_entry"],
			as_dict=True,
			for_update=True,
		)
		if current.purchase_invoice or current.journal_entry:
			frappe.throw(_("A document has already been created for this fleet slip."))

		supplier = self.fleet_card_supplier
		if not supplier:
			frappe.throw(_("No fleet card supplier set. Link a Fleet Vehicle with a fleet card provider."))

		settings = frappe.get_cached_doc("OCR Settings")

		# Determine item from slip_type
		item_code = self._resolve_item(settings)
		if not item_code:
			frappe.throw(_("No item configured. Set Fleet Fuel Item or Fleet Toll Item in OCR Settings."))

		pi_item = {
			"item_code": item_code,
			"qty": 1,
			"rate": flt(self.total_amount),
			"description": self._build_description(),
		}

		if self.expense_account:
			pi_item["expense_account"] = self.expense_account

		if self.cost_center:
			pi_item["cost_center"] = self.cost_center
		elif settings.get("default_cost_center"):
			pi_item["cost_center"] = settings.default_cost_center

		pi_dict = {
			"doctype": "Purchase Invoice",
			"supplier": supplier,
			"company": self.company,
			"currency": self.currency or frappe.get_cached_value("Company", self.company, "default_currency"),
			"set_posting_time": 1,
			"posting_date": self.transaction_date or frappe.utils.today(),
			"items": [pi_item],
		}

		# Apply tax template
		if self.tax_template:
			template = frappe.get_cached_doc("Purchase Taxes and Charges Template", self.tax_template)
			if template.company and template.company != self.company:
				frappe.throw(
					_("Tax Template '{0}' belongs to company '{1}', not '{2}'").format(
						self.tax_template, template.company, self.company
					)
				)

			pi_dict["taxes_and_charges"] = self.tax_template
			pi_dict["taxes"] = []
			for tax_row in template.taxes:
				pi_dict["taxes"].append(
					{
						"category": tax_row.category,
						"add_deduct_tax": tax_row.add_deduct_tax,
						"charge_type": tax_row.charge_type,
						"row_id": tax_row.row_id,
						"account_head": tax_row.account_head,
						"description": tax_row.description,
						"rate": tax_row.rate,
						"cost_center": tax_row.cost_center,
						"account_currency": tax_row.account_currency,
						"included_in_print_rate": tax_row.included_in_print_rate,
						"included_in_paid_amount": tax_row.included_in_paid_amount,
					}
				)

		pi = frappe.get_doc(pi_dict)
		pi.flags.ignore_mandatory = True
		pi.insert()

		# Restore description (ERPNext overwrites from Item master)
		desc = self._build_description()
		if desc and pi.items and desc != pi.items[0].item_name:
			pi.items[0].db_set({"item_name": desc, "description": desc})

		# Copy scan attachment to PI
		self._copy_scan_to_document("Purchase Invoice", pi.name)

		# Link back
		self.purchase_invoice = pi.name
		self.status = "Draft Created"
		self.save()

		frappe.msgprint(
			_("Purchase Invoice {0} created as draft.").format(
				frappe.utils.get_link_to_form("Purchase Invoice", pi.name)
			),
			indicator="green",
		)

		return pi.name

	@frappe.whitelist()
	def create_journal_entry(self):
		"""Create a Journal Entry draft for direct expense mode."""
		if not frappe.has_permission("Journal Entry", "create"):
			frappe.throw(_("You don't have permission to create Journal Entries."))

		if self.status not in ("Matched", "Needs Review"):
			frappe.throw(
				_("Cannot create Journal Entry from a record with status '{0}'.").format(self.status)
			)

		if self.document_type != "Journal Entry":
			frappe.throw(_("Document Type must be 'Journal Entry' to create a Journal Entry."))

		# Row-lock
		current = frappe.db.get_value(
			"OCR Fleet Slip",
			self.name,
			["purchase_invoice", "journal_entry"],
			as_dict=True,
			for_update=True,
		)
		if current.purchase_invoice or current.journal_entry:
			frappe.throw(_("A document has already been created for this fleet slip."))

		settings = frappe.get_cached_doc("OCR Settings")

		expense_account = self.expense_account or settings.get("fleet_expense_account")
		if not expense_account:
			frappe.throw(
				_(
					"Please set an Expense Account on this slip or configure "
					"Fleet Expense Account in OCR Settings."
				)
			)

		credit_account = self.credit_account or settings.get("fleet_credit_account")
		if not credit_account:
			frappe.throw(
				_(
					"Please set a Credit Account on this slip or configure "
					"Fleet Credit Account in OCR Settings."
				)
			)

		self._validate_account(expense_account, _("Expense Account"))
		self._validate_account(credit_account, _("Credit Account"))

		total_debit = flt(self.total_amount, 2)

		accounts = [
			{
				"account": expense_account,
				"debit_in_account_currency": total_debit,
				"credit_in_account_currency": 0,
				"cost_center": self.cost_center or settings.get("default_cost_center"),
			},
		]

		# Tax line if VAT detected
		if self.tax_template and flt(self.vat_amount) > 0:
			template = frappe.get_cached_doc("Purchase Taxes and Charges Template", self.tax_template)
			tax_account = None
			for tax_row in template.taxes:
				if tax_row.account_head:
					tax_account = tax_row.account_head
					break

			if tax_account:
				self._validate_account(tax_account, _("Tax Account"))
				tax_amt = flt(self.vat_amount, 2)
				total_debit += tax_amt
				accounts.append(
					{
						"account": tax_account,
						"debit_in_account_currency": tax_amt,
						"credit_in_account_currency": 0,
						"cost_center": settings.get("default_cost_center"),
					}
				)

		# Credit line (balances total debits)
		credit_line = {
			"account": credit_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": flt(total_debit, 2),
		}

		credit_account_type = frappe.db.get_value("Account", credit_account, "account_type")
		if credit_account_type in ("Payable", "Receivable") and self.fleet_card_supplier:
			credit_line["party_type"] = "Supplier"
			credit_line["party"] = self.fleet_card_supplier

		if settings.get("default_cost_center"):
			credit_line["cost_center"] = settings.default_cost_center

		accounts.append(credit_line)

		desc = self._build_description()

		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"set_posting_time": 1,
				"posting_date": self.transaction_date or frappe.utils.today(),
				"user_remark": "OCR Fleet Slip: {} — {}".format(
					self.name,
					frappe.utils.escape_html(desc or ""),
				),
				"accounts": accounts,
			}
		)
		je.flags.ignore_mandatory = True
		je.insert()

		# Copy scan attachment to JE
		self._copy_scan_to_document("Journal Entry", je.name)

		# Link back
		self.journal_entry = je.name
		self.status = "Draft Created"
		self.save()

		frappe.msgprint(
			_("Journal Entry {0} created as draft.").format(
				frappe.utils.get_link_to_form("Journal Entry", je.name)
			),
			indicator="green",
		)

		return je.name

	@frappe.whitelist()
	def unlink_document(self):
		"""Unlink and delete the draft PI/JE, resetting for re-use."""
		if not frappe.has_permission("OCR Fleet Slip", "write", self.name):
			frappe.throw(_("You don't have permission to modify this record."))

		if self.status != "Draft Created":
			frappe.throw(_("Can only unlink documents when status is 'Draft Created'."))

		linked_doctype = None
		linked_name = None
		link_field = None

		if self.purchase_invoice:
			linked_doctype = "Purchase Invoice"
			linked_name = self.purchase_invoice
			link_field = "purchase_invoice"
		elif self.journal_entry:
			linked_doctype = "Journal Entry"
			linked_name = self.journal_entry
			link_field = "journal_entry"

		if not linked_name:
			frappe.throw(_("No linked document found to unlink."))

		docstatus = frappe.db.get_value(linked_doctype, linked_name, "docstatus")
		if docstatus == 1:
			frappe.throw(
				_("{0} {1} is submitted. Amend or cancel it first.").format(linked_doctype, linked_name)
			)

		# Clear link FIRST via db_set (Frappe blocks deletion of docs with incoming Link refs)
		self.db_set(link_field, "")
		self.db_set("document_type", "")
		self.db_set("status", "Pending")

		deleted = False
		if docstatus is not None:
			frappe.delete_doc(linked_doctype, linked_name, force=True)
			deleted = True

		self.reload()
		self.save()

		if deleted:
			frappe.msgprint(
				_("{0} {1} deleted. You can now create a different document.").format(
					linked_doctype, linked_name
				),
				indicator="blue",
			)
		else:
			frappe.msgprint(
				_("Link cleared. {0} {1} was already deleted.").format(linked_doctype, linked_name),
				indicator="blue",
			)

	@frappe.whitelist()
	def mark_no_action(self, reason):
		"""Mark this fleet slip as No Action Required."""
		if not frappe.has_permission("OCR Fleet Slip", "write", self.name):
			frappe.throw(_("You don't have permission to modify this record."))

		if self.status in ("Completed", "Draft Created"):
			frappe.throw(_("Cannot mark as No Action when status is '{0}'.").format(self.status))

		reason = (reason or "").strip()
		if not reason:
			frappe.throw(_("Please provide a reason for marking as No Action."))

		self.status = "No Action"
		self.no_action_reason = reason
		self.save()

		frappe.msgprint(
			_("Marked as No Action: {0}").format(reason),
			indicator="blue",
		)

	def _resolve_item(self, settings):
		"""Get the appropriate item code based on slip_type."""
		if self.slip_type == "Fuel":
			return settings.get("fleet_fuel_item") or settings.get("default_item")
		elif self.slip_type == "Toll":
			return (
				settings.get("fleet_toll_item")
				or settings.get("fleet_fuel_item")
				or settings.get("default_item")
			)
		return settings.get("fleet_fuel_item") or settings.get("default_item")

	def _build_description(self):
		"""Build a human-readable description for the created document line item."""
		parts = []
		if self.slip_type:
			parts.append(self.slip_type)
		if self.merchant_name_ocr:
			parts.append(self.merchant_name_ocr)

		if self.slip_type == "Fuel":
			fuel_parts = []
			if self.litres:
				fuel_parts.append(f"{flt(self.litres, 2)}L")
			if self.fuel_type:
				fuel_parts.append(self.fuel_type)
			if self.price_per_litre:
				fuel_parts.append(f"@ {flt(self.price_per_litre, 2)}/L")
			if fuel_parts:
				parts.append(" ".join(fuel_parts))
		elif self.slip_type == "Toll" and self.toll_plaza_name:
			parts.append(self.toll_plaza_name)

		if self.vehicle_registration:
			parts.append(f"[{self.vehicle_registration}]")

		return " — ".join(parts) if parts else "Fleet Slip"

	def _copy_scan_to_document(self, doctype, docname):
		"""Copy the scan attachment from this fleet slip to the created document."""
		try:
			files = frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": "OCR Fleet Slip",
					"attached_to_name": self.name,
					"is_private": 1,
				},
				fields=["name", "file_url", "file_name"],
				limit=1,
			)
			if files:
				frappe.get_doc(
					{
						"doctype": "File",
						"file_url": files[0].file_url,
						"file_name": files[0].file_name,
						"attached_to_doctype": doctype,
						"attached_to_name": docname,
						"is_private": 1,
					}
				).insert(ignore_permissions=True)

			# Add Drive link as comment
			if self.drive_link and self.drive_link.startswith("https://"):
				from frappe.utils import escape_html

				safe_link = escape_html(self.drive_link)
				safe_path = escape_html(self.drive_folder_path or "N/A")
				doc = frappe.get_doc(doctype, docname)
				doc.add_comment(
					"Comment",
					f"<b>Original Fleet Slip Scan:</b> "
					f"<a href='{safe_link}' target='_blank' rel='noopener noreferrer'>View in Google Drive</a><br>"
					f"<small>Archive path: {safe_path}</small>",
				)
		except Exception:
			# Non-critical — don't fail document creation
			frappe.log_error("Failed to copy scan attachment to fleet slip document")

	def _validate_account(self, account, label):
		"""Validate that an account belongs to this company, is not a group, and is not disabled."""
		account_details = frappe.db.get_value(
			"Account", account, ["company", "is_group", "disabled"], as_dict=True
		)
		if not account_details:
			frappe.throw(_("{0}: Account '{1}' does not exist.").format(label, account))
		if account_details.company != self.company:
			frappe.throw(
				_("{0}: Account '{1}' belongs to company '{2}', not '{3}'.").format(
					label, account, account_details.company, self.company
				)
			)
		if account_details.is_group:
			frappe.throw(
				_("{0}: Account '{1}' is a group account. Please select a ledger account.").format(
					label, account
				)
			)
		if account_details.disabled:
			frappe.throw(_("{0}: Account '{1}' is disabled.").format(label, account))

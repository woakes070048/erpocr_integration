# Independent Audit of REVIEW.md

No HIGH-severity issues found.

## 1. CONFIRMED

| Original # | File:Line | Verdict |
|---|---|---|
| C1 | `erpocr_integration/api.py:822`, `erpocr_integration/api.py:878`, `erpocr_integration/patches/v0_4/normalize_document_type.py:21` | Confirmed: raw SQL uses MariaDB backtick table quoting. LOW is correct because ERPNext v15 production here is MariaDB-backed. |
| I3 | `erpocr_integration/api.py:822`, `erpocr_integration/api.py:878` | Confirmed: raw child-table JOIN SQL is correct and parameterized, but less idiomatic than `frappe.qb`/structured APIs. LOW is correct. |
| I4 | `erpocr_integration/patches/v0_4/normalize_document_type.py:21` | Confirmed: patch SQL is harmless and one-shot, but would be more idiomatic as a structured update. LOW is correct. |

## 2. DISPUTED

| Original # | File:Line | Verdict | Reason |
|---|---|---|---|
| S1 | `erpocr_integration/public/js/ocr_import.js:558` | Disputed as a security finding | `po_qty` and `po_rate` come from ERPNext Float fields on Purchase Order Item via server-side document APIs. I found no realistic user-controlled string path short of DB corruption or framework type bypass. Treat as optional hardening, not a finding. |
| S2 | `erpocr_integration/public/js/ocr_import.js:567` | Disputed as a security finding | `m.qty` and `m.rate` come from OCR Import child Float/Currency fields. Same concern: escaping is cheap, but XSS requires impossible/non-normal typed data. |
| S3 | `erpocr_integration/public/js/ocr_import.js:580` | Disputed as a security finding | `p.qty` is a Purchase Order Item Float. This is defense-in-depth only. |
| I1 | `erpocr_integration/erpnext_ocr/doctype/ocr_service_mapping/ocr_service_mapping.py:145-147` | Real issue, wrong severity | The untranslated `frappe.throw(f"...")` is reachable through normal validation when expense account company mismatches, but it is one user-facing string in a controller. LOW, not MEDIUM. |
| I2 | 28 `ignore_permissions=True` sites | Partially real, overbroad/noisy | The convention says comments or justified context. Many cited sites are self-justifying background-job, internal alias-table, or role-gated aggregation contexts. A smaller list of genuinely unclear sites would be useful; “28 violations” is too blunt. |

## 3. MISSED

| # | File:Line | Pattern | Severity | Confidence |
|---:|---|---|---|---|
| M1 | `erpocr_integration/tasks/email_monitor.py:118-147` | Email UID is marked `\\Seen` before `_move_to_processed_folder()`. If the move fails, the UID remains in `uids_to_move`, so the later failed-UID `\\Seen` removal guard does not clear it. The message can remain in `OCR Invoices` but be skipped by future `UNSEEN` polls; if the enqueued OCR job later fails, automatic retry from email is lost. | MEDIUM | LIKELY |
| M2 | `erpocr_integration/statement_api.py:174-205`, `erpocr_integration/hooks.py:73-84` | Every Purchase Invoice submit/cancel synchronously re-reconciles every `Reconciled` statement for that supplier inside the PI transaction path. With 50 statements for a supplier, each submit can load, mutate, and save 50 statement documents before returning. | MEDIUM | CERTAIN |
| M3 | `erpocr_integration/tasks/reconcile.py:23-41` | `reconcile_statement()` fetches all submitted Purchase Invoices for the supplier with `limit_page_length=0`; if statement period dates are missing, there is no date bound. This can become a 10k-PI scan and is multiplied by M2. | MEDIUM | LIKELY |
| M4 | `erpocr_integration/tasks/drive_integration.py:322-340`, `erpocr_integration/tasks/drive_integration.py:781-799`, `erpocr_integration/tasks/drive_integration.py:959-979` | Drive pollers list all files and enqueue/process all eligible files in one scheduler run, sleeping 5s after each enqueue. A large drop folder can make a 15-minute cron run last far longer than 15 minutes and overlap the next run. | MEDIUM | LIKELY |
| M5 | `erpocr_integration/tasks/drive_integration.py:575-585`, `erpocr_integration/tasks/drive_integration.py:611-619`, `erpocr_integration/tasks/drive_integration.py:663-711` | Google Drive SDK calls use `.execute()` / `next_chunk()` without an explicit per-request timeout or bounded retry budget in this module. A slow Drive response can tie up scheduler/background workers. Gemini HTTP calls do have explicit timeouts; Drive does not. | LOW | UNCERTAIN |
| M6 | `erpocr_integration/api.py:874-895` | `purchase_receipt_link_query()` parameterizes SQL, so this is not SQL injection, but `txt` is not length-capped or LIKE-escaped and the SQL fetches all matching PR candidates before slicing. A wildcard/empty `txt` on a PO with many receipts can force unnecessary DB work. | LOW | LIKELY |
| M7 | `erpocr_integration/erpnext_ocr/doctype/ocr_import/ocr_import.py:365-568`, `erpocr_integration/erpnext_ocr/doctype/ocr_import/ocr_import.py:579-723`, `erpocr_integration/erpnext_ocr/doctype/ocr_import/ocr_import.py:739-916`, `erpocr_integration/erpnext_ocr/doctype/ocr_delivery_note/ocr_delivery_note.py:93-173`, `erpocr_integration/erpnext_ocr/doctype/ocr_delivery_note/ocr_delivery_note.py:184-295`, `erpocr_integration/erpnext_ocr/doctype/ocr_fleet_slip/ocr_fleet_slip.py:75-188` | Whitelisted create methods check permission to create the target ERPNext document, but do not explicitly check write permission on the source OCR document before mutating it. This may be covered by `frappe.client.run_doc_method`; I could not prove that statically. Add explicit source-doc write checks or confirm framework behavior with a runtime permission test. | MEDIUM | UNCERTAIN |
| M8 | `erpocr_integration/erpnext_ocr/doctype/ocr_fleet_slip/ocr_fleet_slip.json:211-229`, `erpocr_integration/erpnext_ocr/doctype/ocr_fleet_slip/ocr_fleet_slip.json:424-436`, `erpocr_integration/hooks.py:123-124` | The new `OCR Fleet Slip Reader` role has read access to all permlevel-0 Fleet Slip fields, including supplier/account/cost-center link fields, and there is no custom `permission_query_conditions` / `has_permission` hook. The scope test only verifies fixture placement, not REST/list field or filter behavior. Runtime API permission tests are needed to prove no supplier-data leakage. | MEDIUM | UNCERTAIN |
| M9 | `erpocr_integration/tasks/matching.py:131-154`, `erpocr_integration/tasks/matching.py:191-214` | Fuzzy matching loads all active suppliers/items and all aliases with `limit_page_length=0`. Since item fuzzy matching can run once per OCR line, large item/alias tables can create repeated full-table scans during extraction. | LOW | LIKELY |
| M10 | `erpocr_integration/stats_api.py:13-43` | `get_ocr_stats()` is role-gated, but accepts arbitrary date strings/ranges and then reads all matching OCR Import rows with `limit_page_length=0` and `ignore_permissions=True`. Wide ranges can become expensive; invalid date input relies on downstream framework behavior. | LOW | LIKELY |

Overall assessment: the original review is reasonable but missed important performance and workflow-state issues.

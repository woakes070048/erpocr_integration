# Code Review — erpocr_integration @ v1.0.3

**Run with 32 APPLIES skills authorised in Phase 2.** MAYBE-tier skills deliberately excluded. Expected false-positive rate budgeted at 30-40%; UNCERTAIN findings explicitly annotated.

---

## 1. SECURITY (production-impacting)

| # | File:Line | Skill | Pattern | Severity | Confidence |
|---:|---|---|---|---|---|
| S1 | [ocr_import.js:565](erpocr_integration/public/js/ocr_import.js#L565) | frappe-impl-ui-components, frappe-errors-clientscripts | Numeric fields interpolated without `esc()` into HTML string — `${m.match.po_qty}`, `${m.match.po_rate}`. Theoretical XSS if server ever returns non-numeric data in a Float field. | **LOW** | UNCERTAIN |
| S2 | [ocr_import.js:568](erpocr_integration/public/js/ocr_import.js#L568) | same | `<td>Qty: ${m.qty || 0}, Rate: ${format_currency(m.rate || 0)}</td>` — `m.qty` unescaped. | **LOW** | UNCERTAIN |
| S3 | [ocr_import.js:580](erpocr_integration/public/js/ocr_import.js#L580) | same | `<td>${p.qty}</td>` — unescaped numeric. | **LOW** | UNCERTAIN |

**Reason UNCERTAIN (applies to S1-S3):** these fields are `Float` on Purchase Order Item / PR Item in ERPNext core, and the data flows from server via whitelisted methods that don't transform values. A corrupted DB would be a prerequisite for exploitation. Adding `esc()` (or a tiny `num()` helper) around the numeric interpolations is cheap defence-in-depth but arguably over-engineering.

### No findings on
- **SQL injection**: 3 raw SQL queries ([api.py:822](erpocr_integration/api.py#L822), [api.py:878](erpocr_integration/api.py#L878), [patches/v0_4/normalize_document_type.py:21](erpocr_integration/patches/v0_4/normalize_document_type.py#L21)). All use parameterised placeholders (`%s` / `%(name)s`); patch is a constant string with no user input.
- **Permission bypass (`ignore_permissions=True` in whitelisted methods)**: 28 occurrences audited — every one is either (a) inside a background job where `frappe.set_user()` was already called, (b) after an explicit `frappe.has_permission` guard at endpoint entry, or (c) inside alias/mapping save helpers called from controllers where the user has already edited the parent doc.
- **Missing `@frappe.whitelist()` on client-called methods**: every Python function referenced from JS in `public/js/` is whitelisted. `frappe.client.run_doc_method` calls all target whitelisted class methods (`create_purchase_invoice`, `unlink_document`, etc.).
- **`allow_guest=True`**: zero usage in the repo.
- **Jinja unescaped user input**: [ocr_stats.html](erpocr_integration/erpnext_ocr/page/ocr_stats/ocr_stats.html) contains zero Jinja expressions — it's a static HTML shell populated by JS from a whitelisted endpoint. No server-side rendering of user data.

---

## 2. CORRECTNESS (silent-failure patterns)

| # | File:Line | Skill | Pattern | Severity | Confidence |
|---:|---|---|---|---|---|
| C1 | [api.py:822-832](erpocr_integration/api.py#L822-L832), [api.py:878-895](erpocr_integration/api.py#L878-L895), [patches/v0_4/normalize_document_type.py:21-29](erpocr_integration/patches/v0_4/normalize_document_type.py#L21-L29) | frappe-errors-database | Raw SQL uses MariaDB backtick table quoting (`` `tabPurchase Receipt` ``). Would fail on PostgreSQL. | **LOW** | CERTAIN |

**Notes on C1:** ERPNext v15 officially requires MariaDB, so this is only a latent risk if you ever migrate the DB. Not a bug today. No fix recommended unless Postgres migration is on the roadmap.

### No findings on
- **Imports inside Server Scripts**: no Server Scripts in this repo (Phase 2 confirmed).
- **Missing `frappe.db.commit()` on scheduled jobs**: `frappe.db.commit()` is called (with `# nosemgrep` comment) at every relevant boundary in the 4 background processors (`gemini_process`, `fleet_gemini_process`, `dn_gemini_process`, `statement_gemini_process`) and inside all `_process_*` loops in `drive_integration.py` and `email_monitor.py`.
- **Wrong event hook names**: `doc_events` uses only `on_submit` / `on_cancel` on submittable DocTypes (PI, PR, PO, JE). Controllers implement only `before_save`, `on_update`, `validate` — all standard Frappe event names.
- **Background jobs not setting user**: all 4 processors call `frappe.set_user(...)` in their first statements (matching the CLAUDE.md-documented pattern).

---

## 3. IDIOM (style / preference)

| # | File:Line | Skill | Pattern | Severity | Confidence |
|---:|---|---|---|---|---|
| I1 | [ocr_service_mapping.py:35-37](erpocr_integration/erpnext_ocr/doctype/ocr_service_mapping/ocr_service_mapping.py#L35-L37) | frappe-syntax-controllers, frappe-agent-validator | `frappe.throw(f"Expense Account {self.expense_account} does not belong to company {self.company}")` — f-string not wrapped in `_()`. Violates project convention ("user-facing strings wrapped in `_()`"). | **MEDIUM** | CERTAIN |
| I2 | 28 sites of `ignore_permissions=True` across 10 files | frappe-core-permissions | Most have no inline `# justification` comment. Violates project convention ("no `ignore_permissions=True` without explicit justification in a comment"). Representative sites: [matching.py:136,153,196,213,270,290](erpocr_integration/tasks/matching.py#L136), [statement_api.py:36,48,194,204](erpocr_integration/statement_api.py#L36), [stats_api.py:43](erpocr_integration/stats_api.py#L43), [reconcile.py:39](erpocr_integration/tasks/reconcile.py#L39), [email_monitor.py:358](erpocr_integration/tasks/email_monitor.py#L358), several controller methods. | **LOW** | CERTAIN |
| I3 | [api.py:822](erpocr_integration/api.py#L822), [api.py:878](erpocr_integration/api.py#L878) | frappe-syntax-query-builder | Raw `frappe.db.sql` used for child-table JOINs (PR Item → PR parent). `frappe.qb` would be idiomatic v15+ style and gives static type-checking. Current code is correct but non-idiomatic. | **LOW** | LIKELY |
| I4 | [patches/v0_4/normalize_document_type.py:21-29](erpocr_integration/patches/v0_4/normalize_document_type.py#L21-L29) | frappe-syntax-query-builder | Patch uses raw SQL `UPDATE` where `frappe.db.set_value("OCR Import", {filters}, "document_type", "")` would work. Harmless (patch runs once). | **LOW** | LIKELY |
| I5 | [ocr_statement.py:13-17](erpocr_integration/erpnext_ocr/doctype/ocr_statement/ocr_statement.py#L13-L17) | frappe-impl-whitelisted | `frappe.throw("Can only mark Reconciled statements as Reviewed.")` — actually wrapped in `_()` ✓ on re-read. **FALSE POSITIVE, withdrawn.** | — | — |

### No findings on
- **Hardcoded `"tab{DocType}"` strings in Python**: zero matches outside raw SQL (which is where they belong).
- **Deprecated `cur_frm` usage**: zero usages — all form JS uses explicit `frm` parameter.
- **Missing `_()` on `msgprint`**: all three hits ([dn.py:180,307](erpocr_integration/erpnext_ocr/doctype/ocr_delivery_note/ocr_delivery_note.py#L180), [ocr_import.py:735](erpocr_integration/erpnext_ocr/doctype/ocr_import/ocr_import.py#L735)) build `msg` via pre-translated `_("...").format(...)` — correct.
- **`cur_frm`**, JS bare `$(...)` global selectors, etc.

---

## Summary Counts

| Severity | Count |
|---|---:|
| **HIGH** | 0 |
| **MEDIUM** | 1 |
| **LOW** | 6 (3 UNCERTAIN, 3 CERTAIN/LIKELY) |

| Confidence | Count |
|---|---:|
| CERTAIN | 3 |
| LIKELY | 2 |
| UNCERTAIN | 3 (S1-S3) |

---

## SKIP_LIST (skill-flagged findings rejected as false positives)

| Flagged by | Ostensible finding | Why rejected |
|---|---|---|
| frappe-errors-database | All `ignore_permissions=True` calls in background jobs | Not a permission bypass — user context is already `Administrator` via `frappe.set_user()`; `ignore_permissions` is redundant but not wrong. Per project convention these should still get a short comment (see I2). |
| frappe-impl-whitelisted | `frappe.client.run_doc_method` calls in bulk list-view JS could be considered "external invocation" without a dedicated whitelisted endpoint | The underlying methods (`create_purchase_invoice`, `unlink_document`) ARE whitelisted class methods; `run_doc_method` is the supported Frappe mechanism for calling them from the client. Not a finding. |
| frappe-impl-jinja | [ocr_stats.html](erpocr_integration/erpnext_ocr/page/ocr_stats/ocr_stats.html) flagged as a Jinja template needing escape review | Contains zero `{{ }}` / `{% %}` expressions. It's pure HTML + CSS. No server-side rendering of user data. Not a finding. |
| frappe-errors-clientscripts | JS table builders use template literals (``` ``` ``` ```) which "could be innerHTML injection" | Every dynamic field is passed through `esc()` (`frappe.utils.escape_html`) or `encodeURIComponent`. Only numeric fields are unescaped (S1-S3) — flagged at LOW UNCERTAIN there. |
| frappe-syntax-query-builder | All 123 `frappe.get_all` calls flagged as "could be `frappe.qb`" | Project convention (per Phase 2 prompt) explicitly prefers `frappe.qb OR frappe.get_all over raw frappe.db.sql`. `get_all` is authorised. Only raw SQL sites flagged (I3, I4). |
| frappe-core-logging | 65 `except Exception` handlers flagged as "over-broad" | Sampled ~10 of them — all either log via `frappe.log_error` and continue (background jobs, graceful degradation on Drive/IMAP failures) or re-raise. Idiomatic for batch-ingest pipelines. No finding. |

---

## RECOMMENDED_FIXES (prioritised by severity × confidence, capped at 10)

| Rank | Finding | Fix | Severity × Confidence |
|---:|---|---|---|
| 1 | **I1** — `ocr_service_mapping.py:35-37` throws with untranslated f-string | Wrap as `_("Expense Account {0} does not belong to company {1}").format(self.expense_account, self.company)`. One-line fix. | MED × CERTAIN |
| 2 | **I2** — 28 `ignore_permissions=True` without inline justification | Add a short `# justification:` comment next to each. Most common justifications would be: "background job (admin context)", "alias table is internal, not user-visible", "bypass user-permissions on role-gated aggregation". Group-commit per file. | LOW × CERTAIN |
| 3 | **S1-S3** — three numeric interpolations in ocr_import.js without escape | Add a tiny `n(v)` helper (`return Number(v).toLocaleString()` or similar) and pipe the 3 cases through it. Defence-in-depth. | LOW × UNCERTAIN |
| 4 | **I3** — raw SQL in api.py:822 and 878 | Migrate to `frappe.qb` for idiom parity. Non-trivial (child-table JOIN) but mechanical. Leave the patch (I4) as-is (runs once). | LOW × LIKELY |
| 5-10 | — | No further findings rising to "recommended" tier. | — |

---

## Conflicts between authorised skills

- `frappe-syntax-query-builder` would have flagged `frappe.get_all` calls as "prefer `frappe.qb`". This conflicts with the user-stated convention ("`frappe.qb or frappe.get_all`"). **Stricter interpretation applied**: `get_all` is allowed; only raw SQL is flagged as an upgrade candidate. Noted in SKIP_LIST.
- `frappe-core-logging` would have flagged `except Exception:` as a correctness risk. `frappe-errors-api` recommends broad exception catching at API boundaries for graceful error reporting. **Stricter per context**: at user-facing API boundaries (graceful degradation), broad except is fine; elsewhere, narrow if possible. No active findings.

---

## Notes

- Review run against `master` at commit `cc6358b` (v1.0.3 tag).
- Review-only — no files were edited.
- Authorise specific fixes (e.g., "fix I1 and I2") to proceed.

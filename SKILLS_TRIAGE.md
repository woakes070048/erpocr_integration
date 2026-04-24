# Skills Triage — erpocr_integration

Repo: `/home/willie/dev/OCRIntegration` (erpocr_integration, Frappe v15, prod on starpops.co.za + cactuscraft.co.za).

**Evidence gathered up front** (from repo scan):

| Pattern | Present? | Evidence |
|---|---|---|
| Server Scripts (fixture-based) | ❌ No | no `fixtures/server_script*` |
| Client Scripts (fixture-based) | ❌ No | no `fixtures/client_script*` |
| Workflows (Frappe DocType) | ❌ No | no `workflow*` fixtures or doctype refs |
| Web Forms | ❌ No | no `web_form*` directory |
| Print Formats | ❌ No | no `print_format*` directory |
| Reports (Script/Query) | ❌ No | no `report/` subdir under doctypes |
| Portal / Website | ❌ No | `website_generators` commented out in hooks.py |
| Custom DocTypes | ✅ Yes | `erpnext_ocr/doctype/{ocr_import, ocr_fleet_slip, ocr_delivery_note, ocr_statement, ocr_settings, …}/` |
| Custom DocType Controllers | ✅ Yes | `ocr_import.py`, `ocr_fleet_slip.py`, `ocr_delivery_note.py`, `ocr_statement.py` |
| Page (with Jinja HTML) | ✅ Yes | `erpnext_ocr/page/ocr_stats/ocr_stats.html`, `.js`, `.json` |
| Workspace | ✅ Yes | `erpnext_ocr/workspace/` |
| hooks.py doc_events | ✅ Yes | `hooks.py:71-99` (PI/PR/PO/JE on_submit + on_cancel) |
| hooks.py scheduler_events | ✅ Yes | `hooks.py:109-113` (hourly email, 15-min cron for Drive polls) |
| Fixtures shipped | ✅ Yes | `fixtures/{role, custom_field, dashboard_chart, number_card}.json` |
| Patches | ✅ Yes | `erpocr_integration/patches/v0_4/normalize_document_type.py` |
| @frappe.whitelist() endpoints | ✅ 29 count | across `api.py`, `dn_api.py`, `fleet_api.py`, `statement_api.py`, `stats_api.py`, controllers |
| `frappe.db.sql` raw queries | ⚠️ 3 usages | `api.py:822`, `api.py:878`, `patches/v0_4/normalize_document_type.py:21` |
| `frappe.qb` usages | ❌ 0 | none |
| `frappe.get_all` / `db.get_all` | ✅ 123 usages | dominant query pattern |
| `ignore_permissions=True` | ⚠️ 28 occurrences across 10 files | across background jobs, auto-draft, matching, fixture bootstrap |
| `allow_guest=True` | ❌ No | none |
| External API callers | ✅ Yes | `gemini_extract.py` (Gemini HTTP), `drive_integration.py` (Google Drive SDK), `email_monitor.py` (IMAP), `classify_document.py` (Gemini HTTP) |
| Jinja templates | ✅ Yes (1) | `erpnext_ocr/page/ocr_stats/ocr_stats.html` |
| Custom fields on external DocType | ✅ Yes | `fixtures/custom_field.json` → `Fleet Vehicle-custom_*` |
| Multi-app integration | ✅ Yes | reads `Fleet Vehicle` DocType from `fleet_management` app |
| Test suite | ✅ Yes | `tests/` — 587 pytest tests |
| Docker build / bench ops | ✅ Yes | this repo uses `frappe-migrate` skill for deploys |
| Workflows (custom_state transitions) | ❌ No | statuses are managed via `_update_status()` controller logic, not Frappe Workflow |
| Cache / Redis usage | ❌ No | `frappe.cache_manager` not imported anywhere; only Redis usage is via `frappe.enqueue` (implicit) |
| Notifications (Frappe Notification DocType) | ❌ No | error surfacing is via `frappe.log_error` + desk msgprint, not Notification docs |
| Cur_frm deprecated | ❌ No | 0 usages; client JS uses explicit `frm` |

---

## Triage Decisions

| # | Skill | Decision | Evidence | Reason |
|---:|---|---|---|---|
| 1 | frappe-agent-architect | **APPLIES** | repo integrates with `fleet_management` (shared Fleet Vehicle custom fields), new v1.0.3 cross-app role | multi-app coordination is a first-class concern; prod incident last week was caused by a sister app |
| 2 | frappe-agent-debugger | **MAYBE** | n/a | meta-skill about using bench console / reading logs — useful for debugging but not pattern-based review |
| 3 | frappe-agent-migrator | **SKIP** | `requires-python=">=3.10"`, ERPNext v15 only | no version migration ongoing |
| 4 | frappe-agent-validator | **APPLIES** | whole review task | literally a best-practices validator |
| 5 | frappe-core-api | **APPLIES** | 29 whitelisted methods, external API calls (Gemini, Drive) | core API patterns dominate the codebase |
| 6 | frappe-core-cache | **SKIP** | no `frappe.cache` usage; grep clean | skill doesn't apply to code that doesn't cache |
| 7 | frappe-core-database | **APPLIES** | 123 `get_all` calls, 3 raw SQL, heavy `db.get_value` | DB operations are the bulk of the codebase |
| 8 | frappe-core-files | **APPLIES** | `api.py:upload_pdf`, `File` DocType used for attachment persistence | upload flow + attachment handling central to pipeline |
| 9 | frappe-core-logging | **APPLIES** | `frappe.log_error` used 61 times across 11 files (error handling audit) | logging surface is heavy |
| 10 | frappe-core-notifications | **SKIP** | no `Notification` DocType usage, no Auto Repeat, no Assignment Rule | skill domain not touched |
| 11 | frappe-core-permissions | **APPLIES** | v1.0.3 just added a narrow role; recent prod incident was perm-related; multiple `has_permission` checks on whitelisted endpoints | most recent dev energy has gone here |
| 12 | frappe-core-utils | **APPLIES** | `frappe.utils` imports present (`flt`, `cint`, `now`, `escape_html`, `add_days`, …) | standard usage to audit |
| 13 | frappe-core-workflow | **SKIP** | no Workflow fixtures, status mgmt in controllers | skill targets Frappe's Workflow DocType which isn't used |
| 14 | frappe-errors-api | **APPLIES** | 29 whitelisted methods; v0.8.4/v1.0.2 added explicit `has_permission` checks | API error patterns directly relevant |
| 15 | frappe-errors-clientscripts | **APPLIES** | `public/js/ocr_import.js` (~850 lines), DN/Fleet/Statement JS, list script | JS error surface sizeable |
| 16 | frappe-errors-controllers | **APPLIES** | 4 custom controllers with `before_save`/`on_update`/`on_submit`/etc. handlers | controllers are central to the pipeline |
| 17 | frappe-errors-database | **APPLIES** | 3 raw SQL queries, 123 `get_all` calls | DB-error patterns directly relevant |
| 18 | frappe-errors-hooks | **APPLIES** | `hooks.py` uses `doc_events` on 4 external DocTypes (PI, PR, PO, JE), scheduler_events, fixtures | hook misfires have bitten this project before |
| 19 | frappe-errors-permissions | **APPLIES** | literally last week's prod incident; 28 `ignore_permissions=True` occurrences to audit | prod-relevant |
| 20 | frappe-errors-serverscripts | **SKIP** | no Server Scripts | skill domain absent |
| 21 | frappe-impl-clientscripts | **APPLIES** | large client-side JS surface | pattern review |
| 22 | frappe-impl-controllers | **APPLIES** | 4 controllers | pattern review |
| 23 | frappe-impl-customapp | **SKIP** | app established, 1.0.3 released | skill targets new-app scaffolding |
| 24 | frappe-impl-hooks | **APPLIES** | `hooks.py` is 145 lines with doc_events, scheduler, fixtures | pattern review |
| 25 | frappe-impl-integrations | **MAYBE** | external API callers exist (Gemini, Drive) but NOT via Frappe Webhook/OAuth/Connected App DocTypes; no Payment Gateway; no Data Import | skill targets Frappe-native integration features that aren't used; flag UNCERTAIN |
| 26 | frappe-impl-jinja | **APPLIES** | `ocr_stats.html` is a Jinja Page template | one file but worth reviewing for escaping |
| 27 | frappe-impl-reports | **SKIP** | no `report/` subdirectories | skill domain absent |
| 28 | frappe-impl-scheduler | **APPLIES** | `hooks.py` scheduler_events fires hourly + 4 cron tasks | core runtime |
| 29 | frappe-impl-serverscripts | **SKIP** | no Server Scripts | skill domain absent |
| 30 | frappe-impl-ui-components | **APPLIES** | `ocr_stats` Page, list view JS, custom dialogs (`frappe.ui.Dialog`), realtime via `frappe.publish_realtime` | several custom UI patterns |
| 31 | frappe-impl-website | **SKIP** | no Web Forms, no portal routes | skill domain absent |
| 32 | frappe-impl-whitelisted | **APPLIES** | 29 endpoints | core review target |
| 33 | frappe-impl-workflow | **SKIP** | no Workflow | skill domain absent |
| 34 | frappe-impl-workspace | **APPLIES** | `erpnext_ocr/workspace/` exists | one workspace file |
| 35 | frappe-migrate | **APPLIES** | this repo is the one the skill targets | just used it 3 turns ago for v1.0.3 deploy |
| 36 | frappe-ops-app-lifecycle | **MAYBE** | app has full lifecycle (scaffolded, CI, tests, deployed, versioned) | mostly useful for app creation; some sections on tests/deploy apply |
| 37 | frappe-ops-backup | **SKIP** | no backup config in this repo | skill scoped to backup/DR |
| 38 | frappe-ops-bench | **MAYBE** | repo uses `bench` via the frappe-migrate flow | ops-adjacent; not code-review scope |
| 39 | frappe-ops-deployment | **SKIP** | Nginx/SSL/Supervisor not in this repo (lives in `erpnext-docker`) | out of review scope |
| 40 | frappe-ops-frontend-build | **MAYBE** | `bench build --app erpocr_integration` used in the migrate flow | esbuild pipeline is used but not configured here — no `build.json` or custom esbuild config in repo |
| 41 | frappe-ops-performance | **SKIP** | no DB tuning / gunicorn config in repo | out of review scope |
| 42 | frappe-ops-upgrades | **SKIP** | repo is v15-only, no pending upgrade | skill targets major version upgrades |
| 43 | frappe-ops-website-deploy | **SKIP** | no website content | skill domain absent |
| 44 | frappe-syntax-clientscripts | **APPLIES** | `public/js/*.js` surface | pattern review |
| 45 | frappe-syntax-controllers | **APPLIES** | Python controllers | pattern review |
| 46 | frappe-syntax-customapp | **MAYBE** | app established | skill targets app structure — mostly useful for new apps; could catch structural drift |
| 47 | frappe-syntax-doctypes | **APPLIES** | 12+ DocType JSONs, several child tables, permissions arrays | pattern review — recently edited for v1.0.3 |
| 48 | frappe-syntax-hooks | **APPLIES** | `hooks.py` | pattern review |
| 49 | frappe-syntax-hooks-events | **APPLIES** | `doc_events` on 4 external DocTypes | pattern review — cross-app event handlers |
| 50 | frappe-syntax-jinja | **APPLIES** | `ocr_stats.html` | pattern review |
| 51 | frappe-syntax-print | **SKIP** | no print formats | skill domain absent |
| 52 | frappe-syntax-query-builder | **MAYBE** | 0 usages of `frappe.qb` | skill would flag the 3 raw SQL queries as candidates for qb — idiom-level finding; flag UNCERTAIN since get_all is also fine |
| 53 | frappe-syntax-reports | **SKIP** | no reports | skill domain absent |
| 54 | frappe-syntax-scheduler | **APPLIES** | scheduler_events active | pattern review |
| 55 | frappe-syntax-serverscripts | **SKIP** | no Server Scripts | skill domain absent |
| 56 | frappe-syntax-whitelisted | **APPLIES** | 29 endpoints | pattern review |
| 57 | frappe-testing-unit | **APPLIES** | 587 pytest tests, mock_frappe conftest pattern | pattern review |

---

## Summary

**32 APPLIES, 7 MAYBE, 18 SKIP.**

### APPLIES (32)
frappe-agent-architect, frappe-agent-validator,
frappe-core-api, frappe-core-database, frappe-core-files, frappe-core-logging, frappe-core-permissions, frappe-core-utils,
frappe-errors-api, frappe-errors-clientscripts, frappe-errors-controllers, frappe-errors-database, frappe-errors-hooks, frappe-errors-permissions,
frappe-impl-clientscripts, frappe-impl-controllers, frappe-impl-hooks, frappe-impl-jinja, frappe-impl-scheduler, frappe-impl-ui-components, frappe-impl-whitelisted, frappe-impl-workspace,
frappe-migrate,
frappe-syntax-clientscripts, frappe-syntax-controllers, frappe-syntax-doctypes, frappe-syntax-hooks, frappe-syntax-hooks-events, frappe-syntax-jinja, frappe-syntax-scheduler, frappe-syntax-whitelisted,
frappe-testing-unit

### MAYBE (7)
frappe-agent-debugger, frappe-impl-integrations, frappe-ops-app-lifecycle, frappe-ops-bench, frappe-ops-frontend-build, frappe-syntax-customapp, frappe-syntax-query-builder

### SKIP (18)
frappe-agent-migrator, frappe-core-cache, frappe-core-notifications, frappe-core-workflow,
frappe-errors-serverscripts,
frappe-impl-customapp, frappe-impl-integrations (arguable — see MAYBE), frappe-impl-reports, frappe-impl-serverscripts, frappe-impl-website, frappe-impl-workflow,
frappe-ops-backup, frappe-ops-deployment, frappe-ops-performance, frappe-ops-upgrades, frappe-ops-website-deploy,
frappe-syntax-print, frappe-syntax-reports, frappe-syntax-serverscripts

### Notes on the MAYBE list

- **frappe-syntax-query-builder**: 0 usages of `frappe.qb` in this repo. Skill might produce lots of "use qb instead of get_all" findings that don't match your conventions (you prefer `get_all` per project prefs). Including it only adds noise unless you specifically want `frappe.db.sql` → `qb` recommendations for the 3 raw SQL queries.
- **frappe-impl-integrations**: targets Frappe-native integration DocTypes (Webhook, OAuth, Connected App, Payment Gateway, Data Import). This repo integrates via plain HTTP `requests` and Google SDK — none of those DocTypes. Including will likely produce 0 findings or hallucinated ones.
- **frappe-ops-app-lifecycle / frappe-ops-bench / frappe-ops-frontend-build**: ops-adjacent. Most useful during initial app setup; for a code review of an established app, likely low yield.
- **frappe-agent-debugger / frappe-syntax-customapp**: meta-skills about development process rather than pattern-matching. Can generate structural-drift findings but mostly at LOW severity.

### Recommendation for Phase 3

Run Phase 3 with the **32 APPLIES** skills only. Tell me **"go Phase 3"** to run with APPLIES only, or **"go Phase 3, include MAYBE"** to also pull in the 7 MAYBEs. Including MAYBEs will widen the false-positive rate you already expect (~30-40%) because those skills don't cleanly match this repo's patterns.

**Stopping here as instructed.**

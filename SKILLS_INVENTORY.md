# Skills Inventory

Source: `~/.claude/skills/` (user-level). Project-level `.claude/skills/` does not exist.

**Total: 57 skills** (all `frappe-*` themed — single skill family).

| Skill | Words | Description (first line) |
|---|---:|---|
| frappe-agent-architect | 1614 | Use when designing multi-app Frappe architectures, deciding whether to split functionality into separate apps, or implementing cross-app communication patterns. |
| frappe-agent-debugger | 1636 | Use when debugging Frappe errors, using bench console for live inspection, analyzing tracebacks, or reading Frappe log files. |
| frappe-agent-migrator | 1626 | Use when migrating a Frappe app between major versions, detecting breaking API changes, or resolving post-migration errors. |
| frappe-agent-validator | 1587 | Use when reviewing or validating Frappe/ERPNext code against best practices. |
| frappe-core-api | 1595 | Use when building ERPNext/Frappe API integrations (v14/v15/v16). |
| frappe-core-cache | 1411 | Use when implementing Redis caching, cache invalidation, or distributed locking in Frappe. |
| frappe-core-database | 1796 | Use when performing database operations in ERPNext/Frappe v14-v16. |
| frappe-core-files | 1144 | Use when handling file uploads, attachments, private/public file access, or S3 storage configuration. |
| frappe-core-logging | 881 | Use when implementing logging, error tracking, or monitoring in Frappe. |
| frappe-core-notifications | 1355 | Use when implementing email notifications, system alerts, Assignment Rules, Auto Repeat, or ToDo items. |
| frappe-core-permissions | 1536 | Use when implementing the Frappe/ERPNext permission system. Covers roles... |
| frappe-core-utils | 972 | Use when working with utility functions in Frappe v14-v16. |
| frappe-core-workflow | 1537 | Use when creating or modifying Frappe Workflows, defining states and transitions, adding action conditions, or troubleshooting workflow permission errors. |
| frappe-errors-api | 1837 | Use when debugging or handling API errors in Frappe/ERPNext v14/v15/v16. |
| frappe-errors-clientscripts | 1294 | Use when debugging or preventing errors in Frappe Client Scripts. |
| frappe-errors-controllers | 1644 | Use when debugging or preventing errors in Frappe Document Controllers. |
| frappe-errors-database | 1837 | Use when handling database errors in Frappe/ERPNext. |
| frappe-errors-hooks | 2071 | Use when debugging hooks.py errors in Frappe/ERPNext. Covers hook not firing... |
| frappe-errors-permissions | 1691 | Use when debugging or handling permission errors in Frappe/ERPNext. |
| frappe-errors-serverscripts | 1547 | Use when debugging or preventing errors in Frappe Server Scripts. |
| frappe-impl-clientscripts | 1233 | Use when implementing client-side form features in Frappe/ERPNext. |
| frappe-impl-controllers | 1252 | Use when building Document Controllers in a custom Frappe app. |
| frappe-impl-customapp | 1468 | Use when building a custom Frappe app from scratch. |
| frappe-impl-hooks | 1501 | Use when implementing hooks.py configurations in a Frappe custom app. |
| frappe-impl-integrations | 1747 | Use when implementing OAuth providers, Connected Apps, Webhooks, Payment Gateways, or Data Import/Export in Frappe. |
| frappe-impl-jinja | 1814 | Use when building Jinja templates in Frappe: Print Formats, Email... |
| frappe-impl-reports | 1356 | Use when building Script Reports, Query Reports, dashboard charts, or Number Cards in ERPNext. |
| frappe-impl-scheduler | 1214 | Use when implementing scheduled tasks and background jobs in Frappe. |
| frappe-impl-serverscripts | 1307 | Use when implementing server-side features via Setup > Server Script. |
| frappe-impl-ui-components | 1957 | Use when building custom dialogs, extending List View, creating Page controllers, or adding Kanban/Calendar views and realtime updates. |
| frappe-impl-website | 1416 | Use when building portal pages, Web Forms, website routes, or configuring themes and SEO in Frappe. |
| frappe-impl-whitelisted | 1474 | Use when building API endpoints with @frappe.whitelist() in Frappe. |
| frappe-impl-workflow | 1678 | Use when implementing document Workflows, approval chains, or state-based transitions in Frappe. |
| frappe-impl-workspace | 1777 | Use when creating or customizing Workspace pages in Frappe v14-v16. |
| frappe-migrate | 2735 | Rebuild the custom ERPNext image and run bench migrate for any Frappe app on the WSL Docker stack. |
| frappe-ops-app-lifecycle | 1647 | Use when scaffolding a new Frappe app, configuring app settings, building assets, running tests, deploying, updating, or publishing to marketplace. |
| frappe-ops-backup | 1545 | Use when configuring backups, restoring sites, encrypting backup files, scheduling automated backups, or planning disaster recovery. |
| frappe-ops-bench | 1860 | Use when running bench commands, managing sites, configuring multi-tenancy, or setting up domains. |
| frappe-ops-deployment | 1286 | Use when deploying Frappe/ERPNext to production, configuring Nginx or Supervisor, setting up Docker, enabling SSL, or hardening security. |
| frappe-ops-frontend-build | 1450 | Use when configuring frontend asset bundling, migrating from build.json (v14) to esbuild (v15+), or troubleshooting SCSS/CSS compilation. |
| frappe-ops-performance | 1699 | Use when tuning MariaDB, configuring Redis memory, sizing Gunicorn workers, setting up CDN, or profiling slow queries. |
| frappe-ops-upgrades | 1878 | Use when upgrading Frappe/ERPNext between major versions (v14 to v15, v15 to v16), troubleshooting failed migrations, or planning rollback. |
| frappe-ops-website-deploy | 1371 | Deploy HTML/CSS websites to ERPNext/Frappe (v15/v16) as Web Pages via the REST API. |
| frappe-syntax-clientscripts | 1254 | Use when writing client-side JavaScript for ERPNext/Frappe form events. |
| frappe-syntax-controllers | 1545 | Use when writing Python Document Controllers for ERPNext/Frappe DocTypes. |
| frappe-syntax-customapp | 1532 | Use when building Frappe custom apps from scratch. Covers app structure. |
| frappe-syntax-doctypes | 1784 | Use when creating or modifying DocType JSON definitions, choosing fieldtypes, configuring naming rules, adding child tables, or setting up tree structures. |
| frappe-syntax-hooks | 1684 | Use when configuring Frappe hooks.py for app events, scheduler tasks. |
| frappe-syntax-hooks-events | 1574 | Use when implementing document lifecycle hooks via doc_events in hooks.py, understanding event execution order, or extending/overriding document behavior from another app. |
| frappe-syntax-jinja | 1734 | Use when writing Jinja templates for ERPNext/Frappe Print Formats, Email. |
| frappe-syntax-print | 1698 | Use when creating print formats or generating PDFs in Frappe v14-v16. |
| frappe-syntax-query-builder | 775 | Use when building database queries with frappe.qb in Frappe v14-v16. |
| frappe-syntax-reports | 1221 | Use when building Query Reports, Script Reports, or configuring Report Builder, including chart data integration. |
| frappe-syntax-scheduler | 1296 | Use when configuring scheduler events and background jobs in Frappe/ERPNext. |
| frappe-syntax-serverscripts | 1518 | Use when writing Python code for ERPNext/Frappe Server Scripts. |
| frappe-syntax-whitelisted | 1294 | Use when creating Frappe Whitelisted Methods (Python API endpoints). |
| frappe-testing-unit | 1337 | Use when writing unit tests, integration tests, creating test fixtures, or running tests with bench run-tests. |

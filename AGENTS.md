# Repository Instructions

## Shape

- This is a flat collection of Odoo 19 addons, not an installable root Python package; each top-level directory containing `__manifest__.py` is an independent module.
- `partyon_presupuestacion` is the main PartyOn estimation workflow; `partyon_reports` changes its reporting surface. The other top-level directories are separate workshop, OCR/digitization, UI/responsive, menu-visibility, purchase-cost, WhatsApp, and chatter addons.
- Module dependencies, XML/data load order, assets, and external Python requirements are declared in each module's `__manifest__.py`; update those files when adding dependencies or resources.

## Tests

- There is no configured root lint, formatter, typecheck, or test command. Odoo tests require a running-compatible Odoo environment and PostgreSQL.
- Python tests are declared in `partyon_presupuestacion/tests/` and `web_responsive/tests/`; they require the external Odoo test environment rather than `pytest`.
- `web_responsive` also registers browser-side QUnit tests in its manifest (`static/tests/`); they need Odoo's web test runner rather than `pytest`.

## Gotchas

- Preserve manifest load order when changing XML: security files and data must load before views/reports that reference them.
- `highest_purchase_cost/__manifest__.py` currently contains a stray `x` in its `depends` list, so the manifest must be corrected before Odoo can load that addon.
- `dx_all_one_digitization` declares required Python packages (`pytesseract`, `pypdf`, `pdf2image`, `numpy`, `Pillow`, `fuzzywuzzy`, `litellm`) and system OCR/PDF prerequisites.
- `partyon_presupuestacion` contains versioned migrations under `migrations/`; upgrades should be tested from the relevant prior module version.

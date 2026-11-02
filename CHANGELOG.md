# Changelog

All notable changes to MarginPilot are recorded here. The project follows [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-11-01

### Added

- **Price elasticity of demand.** An optional scenario control (0 to -5, off by default) links sales volume to the price change using a constant-elasticity model. With elasticity set, the Profit Sensitivity chart becomes a real demand curve and marks the most profitable price change in the -20% to +20% range.
- **Executive-summary export.** **Export → Executive summary (PDF)** (Ctrl+P) saves a one-page A4 report with the management assessment, both charts, a current-versus-proposed table, and the scenario settings. **Export → Scenario figures (CSV)** (Ctrl+Shift+S) saves the unrounded figures for spreadsheet analysis. Both are written locally.
- Glossary entries for price elasticity, the most profitable price change, and percentage points.
- A dashed break-even line on the sensitivity chart when profit crosses zero.
- Headless UI tests (pytest-qt) covering CSV loading, sliders, elasticity, reset, invalid files, simulation, theme switching, and exports; tests for chart axis rounding and the report service. The suite grew from 32 to 68 tests.
- Ruff linting, mypy type checking, and a GitHub Actions workflow running lint, type checks, and tests on Python 3.11 and 3.13.

### Changed

- Chart value axes use round tick steps (for example $0M, $1M, $2M) and put the minus sign before the currency symbol (`-$0.4M`, not `$-0.4M`).
- Profit-margin changes are shown in percentage points (`-2.8 pp`) instead of a misleading relative percentage.
- Scenario controls are more compact: each value flow now sits beside its control name.
- Whole-number CSV columns, such as units sold, preview without decimals.
- The Management Assessment notes the elasticity assumption when one is set.

### Fixed

- A grey size-grip block in the bottom-right corner of the themed status bar.

## [1.0.0] — 2026-09-25

- Initial release: manual and CSV baselines, five scenario levers, KPI comparison cards, current-versus-proposed and price-sensitivity charts, deterministic management assessment, business glossary, Light and Dark themes, and a reproducible Monte Carlo risk analysis.

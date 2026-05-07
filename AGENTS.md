# Unified Offer Automation Platform Rules

This project is the unified Streamlit platform for customer questionnaires,
offer preparation, pricing helpers, and future business automation pages.

## Product Direction

- Keep one Streamlit application with multiple focused pages under `pages/`.
- Keep reusable business logic in `utils/` instead of embedding calculations in page files.
- Prefer small, explicit modules over broad abstractions until at least two pages share the same behavior.
- Preserve the original business rules from migrated apps unless the user explicitly requests a rule or price change.
- Treat the old repositories and source apps as read-only references. Do not delete, move, or modify them from this project.

## Business Rules And Prices

- Do not change prices, capacities, discounts, subsidies, formulas, or recommendation rules without explicit user approval.
- When migrating another app, first copy the existing behavior faithfully, then refactor structure.
- If a rule is unclear, keep the current behavior and leave a short note in code only where it helps future migration.
- Keep calculations testable through pure functions in `utils/` where possible.

## UI Rules

- Keep the user-facing UI in Greek.
- Keep Streamlit pages operational and simple: forms, inputs, results, summaries, and download actions before decorative polish.
- Use Greek labels for page titles, form fields, buttons, warnings, and result text.
- Placeholder pages should clearly say that business logic has not been migrated yet.
- Do not modify existing migrated pages unless the user specifically asks for that page.

## File Organization

- Root `app.py` is the landing/navigation shell.
- Streamlit pages live in `pages/` with numeric prefixes that define order.
- Reusable logic lives in `utils/`.
- Add data files only when needed, and keep paths relative to the project.
- Avoid writing generated customer outputs into the repository unless the user asks for saved examples.

## Development Workflow

- Make additive, scoped changes when expanding the platform.
- Before changing migrated behavior, identify the source app and the exact rule being changed.
- Keep commits and diffs focused by feature/page.
- Do not edit unrelated pages while adding a new page.
- Do not introduce new dependencies unless they are necessary for a migrated feature.

## Current Migration Status

- Heat-pump questionnaire: migrated as a Streamlit page with summary generation in `utils/`.
- Solar questions: migrated as a Streamlit page with proposal calculations in `utils/`.
- Insulation: placeholder only.
- Radiators: placeholder only.
- Air conditioners: placeholder only.

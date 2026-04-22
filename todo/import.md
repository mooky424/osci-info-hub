# CSV Bulk Import Plan

## Goal

Implement a safe, idempotent bulk CSV import workflow for the OSCI Partner Hub that can create and update:

- Partners
- Contacts
- Needs (Needs Repository)
- Socioeconomic Profiles
- Past Interventions

The import should support preview/validation before writing, produce clear error reports, and avoid partial/invalid data persistence.

## Scope

### In scope

- Admin-only CSV upload endpoint and UI
- Schema validation + row-level business validation
- Dry-run preview mode
- Transactional import execution mode
- Error and summary reporting
- Optional upsert behavior by stable keys

### Out of scope (phase 1)

- XLSX support
- Background queue workers
- Multi-file ZIP import bundles
- Fully automated conflict resolution logic

## Recommended Data Contract

Use one CSV per entity type in phase 1 to reduce complexity and allow strict validation.

1. `partners.csv`
2. `contacts.csv`
3. `needs.csv`
4. `socioeconomic_profiles.csv`
5. `past_interventions.csv`

Each row includes a stable external key to associate related records.

- Partner key: `partner_external_id` (required)
- Related rows reference `partner_external_id`
- Optional row key for upsert per child entity (e.g. `need_external_id`, `contact_external_id`)

## Field Mapping Draft

### partners.csv

- `partner_external_id` (required, unique)
- `name` (required)
- `vision`, `mission`, `goals`, `description`, `core_values`
- `date_established` (required, ISO date)
- `sec_registration`, `bir_registration`, `tin`
- `moa_start_date`, `moa_end_date`, `moa_link`
- `is_archived` (optional boolean, default false)

### contacts.csv

- `contact_external_id` (optional but recommended)
- `partner_external_id` (required)
- `name` (required)
- `position` (required)
- `contact_number` (required, `09XXXXXXXXX`)
- `email` (optional)

### needs.csv

- `need_external_id` (optional but recommended)
- `partner_external_id` (required)
- `name` (required)
- `description`, `objectives`, `expected_outcomes`, `skills_needed`
- `is_archived` (optional boolean)

### socioeconomic_profiles.csv

- `profile_external_id` (optional but recommended)
- `partner_external_id` (required)
- profile fields from `SocioEconomicProfile`

### past_interventions.csv

- `intervention_external_id` (optional but recommended)
- `partner_external_id` (required)
- `name` (required)
- `description`, `outcomes`
- `formator_username` (optional; map to existing User)
- `date_started` (required), `date_ended`
- `output_link`, `pictures_link`, `evaluation_link`
- `is_archived` (optional boolean)

## Architecture Plan

### 1) Import service layer

Create a dedicated service module, e.g.:

- `partners/services/imports/csv_import.py`

Responsibilities:

- Parse CSV files with `csv.DictReader`
- Normalize values (trim strings, parse booleans/dates)
- Validate schema and required fields
- Collect row errors with row numbers
- Execute dry-run and actual import modes

### 2) Validation model

Represent issues in a structured way:

- `row`
- `field`
- `code` (e.g. `missing_required`, `invalid_date`, `unknown_partner`)
- `message`

Return per-file and global summaries:

- rows processed
- rows valid
- rows skipped
- created/updated/archived counts by entity

### 3) Persistence strategy

- Wrap execution mode in `transaction.atomic()`
- Fail-fast on critical schema mismatch
- Continue collecting row errors for business validation failures
- Only write valid rows in execution mode (or optionally strict-all-or-nothing flag)

### 4) Upsert strategy

Phase 1 default:

- If external ID exists, update existing record
- If not, create new record

Fallback matching when external ID missing:

- Partner: `name` + `date_established` (warn on ambiguity)
- Needs: `partner` + `name`
- Contacts: `partner` + `name` + `position`
- Interventions: `partner` + `name` + `date_started`

## Delivery Phases

### Phase A: Foundation

1. Add import endpoint (admin-only) and simple upload page
2. Add CSV parser + schema validators for `partners.csv` only
3. Add dry-run summary UI

### Phase B: Full entities

1. Add support for all CSV files
2. Add relational validation (`partner_external_id` linkage)
3. Add execution mode with `transaction.atomic()`

### Phase C: UX and operations

1. Downloadable error report CSV
2. Import history log model (who, when, result, file names)
3. Optional "archive missing children" mode

## Security and Access

- Restrict import views to authenticated admins only
- Enforce max upload size
- Validate MIME + extension
- Never execute arbitrary content
- Log import events for audit

## Testing Plan

### Unit tests

- CSV parsing and type coercion
- Required field validation
- Date and boolean parsing
- Relationship resolution by external ID

### Integration tests

- Dry-run returns summary and no DB writes
- Execution writes expected creates/updates
- Invalid rows are reported with row numbers
- Archive flag behavior for entities

### Regression checks

- Existing partner create/update flows still work
- PDF export still handles imported records

## Open Decisions

1. Single-file flat CSV vs multi-file entity CSV bundle (recommended: multi-file)
2. Strict all-or-nothing import vs partial success (recommended: partial + detailed report)
3. Whether to expose import in Django admin, app UI, or both (recommended: app UI + admin-only)

## Acceptance Criteria

- Admin can upload CSV files and run dry-run validation
- System reports row-level errors before execution
- Execution mode performs create/update/archive as defined
- Import summary is clear and auditable
- No partial inconsistent state when critical failures occur

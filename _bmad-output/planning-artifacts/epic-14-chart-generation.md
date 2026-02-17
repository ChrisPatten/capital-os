# Epic 14: Chart Generation and Visualization

## Goal
Enable agents to generate flexible, parameterized chart specifications from ledger data, providing visual insights into financial position, trends, and analysis through a standard tool API.

## Why This Epic Exists
- Agents can query financial data but cannot produce visual representations for stakeholder communication.
- Financial analysis often requires visual trends (cash flow over time, expense breakdown by category, asset allocation).
- Manual chart creation from raw data is time-consuming and error-prone.
- Visual dashboards are essential for family office reporting and decision-making.
- Chart specifications should be deterministic and reproducible for audit trails.

## Scope Boundaries
- In scope:
  - `generate_chart` read tool accepting flexible query parameters and chart configuration
  - Support for common financial chart types: line (trends), bar (comparisons), pie (composition), area (cumulative)
  - Flexible date range filtering and time-series aggregation
  - Account filtering by type, code pattern, or hierarchy
  - Entity-aware charting (single entity or consolidated)
  - JSON output format compatible with standard charting libraries (Chart.js, D3, Recharts)
  - Deterministic chart specification hashing for reproducibility
  - Event logging for audit trail
- Out of scope:
  - Actual image rendering (returns specification only, rendering is client responsibility)
  - Real-time streaming updates
  - Interactive drill-down state management
  - Custom chart type plugins
  - Multi-currency conversion for charting (uses ledger currency as-is)
  - Approval workflow (read-only operation)

## Story 14.1: Chart Query Engine and Data Aggregation

Build the core query and aggregation engine that transforms ledger data into chart-ready datasets. Support time-series grouping (daily, weekly, monthly, quarterly, yearly), account filtering, and entity scoping.

Acceptance Criteria:
- Query engine accepts date range (start_date, end_date)
- Time bucket aggregation: daily, weekly, monthly, quarterly, yearly
- Account filtering by: account_type, code_pattern (glob), account_ids (explicit list), parent_account hierarchy
- Entity filtering: single entity_id, consolidated (all entities), or entity comparison
- Aggregation functions: sum, average, min, max, count
- Balance vs flow semantics: point-in-time balances or period activity
- Returns structured data: array of {label, value(s)} or {x, y, series} depending on chart type
- Handles empty result sets gracefully (returns empty data array, not error)
- Performance: <500ms for queries spanning 1 year with daily buckets

## Story 14.2: Chart Specification Builder

Create the chart specification builder that wraps aggregated data in a standard JSON format suitable for popular charting libraries. Support chart type selection, styling hints, and metadata.

Acceptance Criteria:
- Chart types supported: line, bar, pie, area, stacked_bar, stacked_area
- Specification includes: chart_type, title, data (series), axes configuration, styling_hints
- Styling hints: colors (categorical palette), currency formatting, date formatting
- Multi-series support for entity comparison or account comparison
- Legend generation based on series labels
- Output format validates against a published JSON schema
- Specification is deterministic (same query → same JSON structure with canonical key ordering)
- Includes metadata: query_parameters, generation_timestamp, data_point_count

## Story 14.3: Generate Chart Tool Endpoint

Wire the chart generation pipeline to a tool endpoint with full observability, determinism, and security integration.

Acceptance Criteria:
- `POST /tools/generate_chart` accepts chart_type, query parameters, styling options, correlation_id
- Schema validation: 422 on invalid chart_type, missing required query params, invalid date ranges
- Auth/authz enforced: requires `tools:read` capability
- Event-logged with input_hash and output_hash (includes chart specification in output)
- Deterministic hashing: identical query → identical output_hash
- Returns: chart specification JSON, output_hash, correlation_id, metadata
- Error handling: 400 for invalid account_ids, 400 for invalid entity_id, 400 for future dates
- Agent skill files updated: CLAUDE_SKILL.md, CODEX_SKILL.md, tool-reference.md
- Example curl commands for common use cases (cash over time, expense breakdown, asset allocation)

## Story 14.4: Chart Generation Integration Tests and Examples

Comprehensive test coverage and example gallery demonstrating all supported chart types and query patterns.

Acceptance Criteria:
- Integration tests: happy path for each chart type (line, bar, pie, area, stacked variants)
- Time aggregation tests: daily, weekly, monthly, quarterly, yearly buckets
- Account filtering tests: by type, by code pattern, by hierarchy
- Entity filtering tests: single entity, consolidated, entity comparison
- Edge cases: empty data, single data point, large date ranges (5+ years)
- Determinism tests: identical queries produce identical output_hash
- Performance tests: 1-year daily query completes in <500ms (marked with @pytest.mark.performance)
- Security tests: 401 on missing auth, 403 on insufficient capability
- Example gallery: `docs/chart-examples.md` with 10+ real-world chart examples and their curl invocations

## Dependencies
- Requires existing query infrastructure (Epic 6 read query surface)
- Builds on multi-entity support (Epic 8)
- No dependency on backlog epics (Epic 11)

## Exit Criteria
1. Agent can generate any supported chart type via `POST /tools/generate_chart`.
2. Chart specifications are deterministic and reproducible.
3. Query engine handles all filtering, aggregation, and time bucketing requirements.
4. Full test coverage including performance validation.
5. Agent skill files document chart generation capabilities with examples.
6. Chart output format is validated and documented for client-side rendering.

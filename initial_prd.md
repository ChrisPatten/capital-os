PRD — Capital OS Back-End & Tooling Layer (BMAD Standard) 1. Executive Summary Vision Capital OS provides a deterministic, auditable financial truth layer 
(double-entry ledger) plus a computation/simulation layer that a family-office AI agent can safely query and propose actions through structured tools. Primary 
users
	• Family office AI agent (primary operator via tool calls)
	• Human approver (final authority for gated actions)
	• Engineering/finance maintainers (audit, extend, debug) Key differentiators
	• Double-entry canonical state with enforced balancing.
	• Deterministic computations and simulations that are replayable from persisted state.
	• Tool interfaces with schema validation, idempotency, and full audit logging.
	• Privilege boundaries and approval gates for high-impact writes. Problem statement Family office automation requires (a) reliable financial state, 
(b) explainable metrics, (c) safe proposal/approval flows, and (d) audit-ready traces. Typical “budget apps” optimize for UI/ingestion, not correctness, 
determinism, or agent-safe operations. ⸻ 2. Success Criteria Operational correctness
	• SC-01 Ledger balance integrity: 100% of committed transactions satisfy Σ(postings.amount) = 0.
	• SC-02 Deterministic outputs: Identical inputs/state yield byte-identical tool outputs (hash-stable) for computation/simulation tools. Auditability
	• SC-03 Tool trace completeness: 100% of tool invocations emit an event record containing tool name, correlation_id, input_hash, output_hash, 
timestamp, and duration.
	• SC-04 Replayability: For any correlation_id, system can reproduce output_hash from stored state + logged inputs. Safety / governance
	• SC-05 Approval enforcement: 100% of writes above configurable threshold return status="proposed" and do not mutate canonical ledger until approved.
	• SC-06 Boundary enforcement: Capital OS service performs 0 external network calls in production runtime. Performance
	• SC-07 Tool latency: p95 < 300ms for compute/simulate/analyze tools on a reference dataset size (define in test harness: e.g., 100k postings, 5k 
accounts, 2k obligations). ⸻ 3. Product Scope MVP (Phase 1 / In Scope)
	• Double-entry ledger schema and invariants
	• Account hierarchy and metadata
	• Balance snapshots (point-in-time account balances)
	• Obligations tracking
	• Capital posture computation
	• Decision simulation (non-mutating)
	• Debt sensitivity and payoff ranking
	• Tool API layer (schema-validated, idempotent, logged)
	• Observability event logging Out of Scope (Phase 1)
	• Automated ingestion (bank feeds, CSV pipelines, OCR, scraping)
	• Browser automation and password manager access
	• Agent orchestration (routing, memory, planning)
	• UI/dashboard Planned Extensions (Phase 2+)
	• Transaction ingestion pipelines + dedupe rules
	• Vendor rule engine / categorization
	• Forecast engine (cashflow, obligations, income variability)
	• Monte Carlo reserve simulation
	• Scenario comparison and portfolio allocation modeling
	• API versioning ⸻ 4. User Journeys UJ-01 Establish canonical ledger state
	1. Human or upstream system creates account hierarchy (assets/liabilities/income/expense/equity).
	2. Agent records transactions via record_transaction_bundle (balanced postings enforced).
	3. System persists transaction, postings, and emits an audit event. Outcome: Ledger is the canonical source of truth. UJ-02 Maintain point-in-time 
balances
	1. Upstream process provides authoritative balances (manual entry or imported artifact).
	2. Agent calls record_balance_snapshot for selected accounts.
	3. Capital OS stores snapshot and associates optional source artifact id. Outcome: System can reconcile ledger-derived balances vs authoritative 
snapshots. UJ-03 Understand capital posture (runway + reserves)
	1. Agent calls compute_capital_posture.
	2. System aggregates liquidity accounts, fixed/variable burn, buffers, reserve targets.
	3. Tool returns posture metrics and risk band with explanation fields. Outcome: Agent can reason about capacity for discretionary spend and debt 
actions. UJ-04 Simulate discretionary spend without committing
	1. Agent calls simulate_spend(amount, recurring_flag, category, time_horizon_months).
	2. System computes projected liquidity/reserve impacts without mutating state.
	3. Tool returns updated metrics, runway estimate, and risk band. Outcome: Agent proposes actions with quantified impact and can request approval if 
needed. UJ-05 Analyze debt payoff options
	1. Agent calls analyze_debt(optional_payoff_amount).
	2. System ranks liabilities by payoff score and computes scenarios.
	3. Tool returns interest saved, cashflow freed, reserve impact. Outcome: Agent proposes optimal payoff plan consistent with reserve policy. UJ-06 
Approval-gated high-impact changes
	1. Agent attempts to record a transaction above threshold.
	2. Tool returns status="proposed" with a proposal_id and projected effects.
	3. Human approves via explicit approval tool call.
	4. System commits transaction atomically, emits audit event linking proposal_id. Outcome: Safety-by-default governance for agent-initiated actions. ⸻ 
5. Domain Requirements (FinOps / Family Office / Audit) Capital OS must meet baseline “fintech-grade” control expectations for auditability and change 
governance. BMAD emphasizes domain requirements as first-class constraints.  ￼ DR-01 Audit trail immutability
	• Event logs are append-only (no updates/deletes in normal operation).
	• Any correction is represented as a new compensating entry. DR-02 Separation of duties
	• Agents cannot write directly to DB.
	• Writes occur only via tool layer enforcing validation and approval gates. DR-03 Data retention
	• Retain ledger + event logs for a configurable period (default: 7 years) or per policy. DR-04 Explainability
	• Computation outputs include a minimal explanation payload showing contributing balances/assumptions used (hashable inputs). DR-05 PII/data 
minimization
	• Metadata supports references to external artifacts without embedding secrets.
	• No secret material stored in event payloads. ⸻ 6. Functional Requirements (Capabilities Contract) BMAD guidance: FRs must be capability-focused, 
measurable, and avoid implementation leakage.  ￼ Ledger & State
	• FR-01 Account hierarchy management System stores accounts with type, parent-child hierarchy, and metadata. Acceptance criteria: supports ≥ 10,000 
accounts; retrieving subtree of 1,000 accounts completes p95 < 200ms.
	• FR-02 Record balanced transaction bundles Tool accepts a transaction + postings and commits only if sum(postings.amount)=0. Acceptance criteria: 
rejects any bundle with non-zero sum; commits atomically on success.
	• FR-03 Idempotent transaction recording If external_id is provided, repeated submissions with same external_id do not create duplicates. Acceptance 
criteria: second submission returns same transaction_id and emits an idempotency event.
	• FR-04 Record balance snapshots Tool stores point-in-time balances per account_id and snapshot_date. Acceptance criteria: snapshot retrieval by 
(account_id, date) returns a single canonical record.
	• FR-05 Track obligations Tool creates/updates obligations with cadence, expected_amount, variability_flag, next_due_date, and metadata. Acceptance 
criteria: obligations list query returns all active obligations; supports monthly/annual/custom cadence definitions. Computation & Simulation
	• FR-06 Compute capital posture Tool returns fixed_burn, variable_burn, volatility_buffer, reserve_target, liquidity, liquidity_surplus, 
reserve_ratio, risk_band. Acceptance criteria: output is deterministic and hash-stable for the same stored state + config.
	• FR-07 Simulate spend without mutation Tool returns projected liquidity/reserve metrics and runway over a specified horizon without changing ledger 
tables. Acceptance criteria: database state unchanged after simulation (verified by transaction isolation tests).
	• FR-08 Debt optimization analysis Tool returns per-liability metrics and ranked payoff options. Acceptance criteria: ranking is deterministic given 
same state; includes sensitivity for optional payoff_amount. Tooling / Governance
	• FR-09 Structured tool API with schema validation All tools accept/return JSON schemas and reject invalid inputs. Acceptance criteria: invalid 
payloads return 4xx with machine-readable validation errors.
	• FR-10 Tool invocation logging Every tool call emits an event log record with correlation_id, input_hash, output_hash, timestamp, duration. 
Acceptance criteria: 100% coverage, including failed validations.  ￼
	• FR-11 Approval gates for high-impact writes Transactions above approval_threshold_amount return proposed status and require explicit approval to 
commit. Acceptance criteria: no ledger mutation occurs until approval tool is called; approval tool is idempotent.
	• FR-12 Privilege boundaries Only the Capital OS service role can write ledger tables. Acceptance criteria: DB permissions prevent direct writes by 
agent role credentials. ⸻ 7. Non-Functional Requirements (Measurable) BMAD guidance: NFRs must be measurable with explicit conditions and measurement method.  
￼
	• NFR-01 Determinism System shall produce identical outputs for identical stored state + config as measured by output_hash equality across replays.
	• NFR-02 ACID System shall commit ledger writes atomically within a single Postgres transaction as verified by integration tests with forced failure 
injection.
	• NFR-03 Performance Compute/simulate/analyze tools shall respond in p95 < 300ms on reference dataset as measured by load tests in CI.
	• NFR-04 Observability Tool invocations shall be traceable end-to-end via correlation_id as measured by 100% presence in event_log and log pipeline.
	• NFR-05 Safety / isolation Capital OS runtime shall make zero outbound network calls as verified by egress-deny policy + runtime telemetry.
	• NFR-06 Migration control Schema migrations shall be versioned and reversible as measured by successful forward + rollback tests in CI.
	• NFR-07 Test coverage Financial math functions shall have 100% branch coverage as measured by coverage tooling on computation modules. ⸻ 8. 
Traceability Matrix (Minimum) BMAD emphasizes a traceability chain from vision → success → journeys → requirements.  ￼ Success Criteria User Journeys 
Functional Requirements SC-01, SC-02 UJ-01, UJ-02 FR-02, FR-03, FR-04 SC-03, SC-04 UJ-01–UJ-06 FR-10 SC-05, SC-06 UJ-06 FR-11, FR-12 SC-07 UJ-03–UJ-05 FR-06, 
FR-07, FR-08 ⸻ 9. Tool API Surface (Phase 1) Ledger tools
	• record_transaction_bundle(date, description, postings[], source?, external_id?)
	• record_balance_snapshot(account_id, snapshot_date, balance, source_artifact_id?)
	• create_or_update_obligation(name, account_id, cadence, expected_amount, variability_flag?, next_due_date, metadata?) Capital OS tools
	• compute_capital_posture()
	• simulate_spend(amount, recurring_flag, category, time_horizon_months)
	• analyze_debt(optional_payoff_amount?) Governance tools
	• propose_transaction_bundle(...) (or status return from record tool)
	• approve_proposed_transaction(proposal_id)
	• reject_proposed_transaction(proposal_id, reason?) ⸻ 10. Definition of Done (Phase 1)
	• Ledger schema deployed with invariants and permissioning
	• Tool endpoints implemented with schema validation + idempotency keys
	• Capital posture computation working and deterministic
	• Simulation working, guaranteed non-mutating
	• Debt analysis working and deterministic
	• Event logging emitted for all tool executions (success + failure)
	• Configurable reserve multiplier, volatility buffer method, approval threshold ⸻
If you want the PRD to be even closer to “BMAD workflow output,” the next refinement step is to add: (1) explicit MVP data set assumptions, (2) a risk register (data integrity, abuse cases, misconfiguration), and (3) a short open questions section that the PM/Architect workflows can close during tech design.

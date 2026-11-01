# Data Scientist Agent: Production Architecture and Workflow

Status: design baseline v7. It preserves the v4 design and closes remaining specification gaps for schema-retrieval evaluation, dirty-value linking, large-warehouse scaling tests, explicit Router/Planner/Clarification/Visualization Agent contracts, and consistency of retries, baselines, chart fallbacks, and acceptance priorities. Lineage: v4 (which retains the v3 approach and merges in the team's DataScientist_Agent_Architecture_v2 draft). Inputs: mentor session transcript, the two draw.io diagrams (Question to Answer Flow, Question Types and Engines), and three reference links (nao, Prophet quick start, GitHub synthetic-data topic).

**Current development scope (authoritative):** Build and test the application locally in incremental phases. Redis is **not used** and must not be added as a dependency. Use an in-process queue for local work and the application-owned SQLite store plus LangGraph-supported local checkpoint persistence. Do not implement Docker, Kubernetes, cloud queues, public hosting, or production deployment during the current coding task. Sections describing production/deployment are future design context only; they are not instructions for the current coding agent. The connected business database (`ecommerce.sqlite` or any user database) is strictly **read-only and immutable**; the agent must never expand, alter, create, or modify tables in the user database. All precomputed insight tables, curated views, memory, and traces are stored exclusively in the separate agent-owned store.

**Changes in v6:** extends the v5 baseline with a gated first-run onboarding wizard, durable asynchronous preparation jobs, provider/database configuration, multi-document business-context ingestion, a concrete Next.js frontend decision, a Nao-inspired visualization integration contract, and safe user-facing thought/progress streaming. **Changes in v7:** specifies a centralized shared `MemoryService`, memory categories and typed records, read/write contracts, retrieval and precedence rules, SQLite development/MySQL production profile, vector-index abstraction, retention/deletion, tenant isolation, and memory acceptance tests. Earlier decisions remain unless a later version explicitly standardizes or clarifies them.

---

## Table of Contents

- [1. Purpose, scope, principles](#1-purpose-scope-principles)
  - [1.1 Binding decisions](#11-binding-decisions)
- [2. Mentor requirements and sign-off matrix](#2-mentor-requirements-and-sign-off-matrix)
  - [2.1 Problem-statement traceability *(v4; extended in v5)*](#21-problem-statement-traceability-v4-extended-in-v5)
- [3. What we take from the reference links](#3-what-we-take-from-the-reference-links)
- [4. Question taxonomy (the scope contract)](#4-question-taxonomy-the-scope-contract)
  - [4.1 Router Agent rules *(v5; implementation node: IntentExtractor + route policy)*](#41-router-agent-rules-v5-implementation-node-intentextractor-route-policy)
  - [4.2 Clarification policy](#42-clarification-policy)
  - [4.3 Answerability gate and refusal policy *(v4)*](#43-answerability-gate-and-refusal-policy-v4)
- [5. System architecture](#5-system-architecture)
  - [5.1 Demo versus production](#51-demo-versus-production)
  - [5.2 Scaling model](#52-scaling-model)
  - [5.3 Diagram synchronization checklist *(v5)*](#53-diagram-synchronization-checklist-v5)
- [6. Workflow (runtime)](#6-workflow-runtime)
  - [6.1 Fast path and flex path](#61-fast-path-and-flex-path)
  - [6.2 Streaming event protocol *(v6: progress + safe thought summaries)*](#62-streaming-event-protocol-v6-progress-safe-thought-summaries)
  - [6.3 Degradation matrix](#63-degradation-matrix)
  - [6.4 Real-time operation *(v4)*](#64-real-time-operation-v4)
- [7. Agents and contracts](#7-agents-and-contracts)
  - [7.0.1 Explicit contracts for the four named agents *(v5)*](#701-explicit-contracts-for-the-four-named-agents-v5)
  - [7.1 Agent policies](#71-agent-policies)
  - [7.2 Verifier checks](#72-verifier-checks)
  - [7.3 Step result and confidence](#73-step-result-and-confidence)
  - [7.4 Error taxonomy](#74-error-taxonomy)
  - [7.5 Causal tiering](#75-causal-tiering)
- [8. Conversation memory and context *(v7: shared MemoryService contract)*](#8-conversation-memory-and-context-v7-shared-memoryservice-contract)
  - [8.1 Context as code and the context pack](#81-context-as-code-and-the-context-pack)
  - [8.2 Memory layers](#82-memory-layers)
  - [8.3 Learnings loop](#83-learnings-loop)
  - [8.4 Shared MemoryService: implementation contract *(v7)*](#84-shared-memoryservice-implementation-contract-v7)
- [9. Data and knowledge layer](#9-data-and-knowledge-layer)
  - [9.1 Warehouse](#91-warehouse)
  - [9.2 Context layer (files in git, nao-style)](#92-context-layer-files-in-git-nao-style)
  - [9.3 Ingestion pipeline (add any table set without code changes)](#93-ingestion-pipeline-add-any-table-set-without-code-changes)
  - [9.4 Insight store (precomputed intelligence, as the mentor suggested)](#94-insight-store-precomputed-intelligence-as-the-mentor-suggested)
  - [9.5 Ready-to-use warehouse and causal analysis scenarios](#95-ready-to-use-warehouse-and-causal-analysis-scenarios)
  - [9.6 Messy-warehouse hardening *(v4)*](#96-messy-warehouse-hardening-v4)
  - [9.7 Agent-owned store: where analysis tables, history and traces live *(v4)*](#97-agent-owned-store-where-analysis-tables-history-and-traces-live-v4)
- [10. Engines](#10-engines)
  - [10.1 SQL Agent](#101-sql-agent)
  - [10.2 Analysis toolkit (deterministic, typed, unit-tested)](#102-analysis-toolkit-deterministic-typed-unit-tested)
  - [10.3 Engine playbook](#103-engine-playbook)
  - [10.4 Churn and at-risk segments *(v4)*](#104-churn-and-at-risk-segments-v4)
- [11. Visualization *(v6: Nao-inspired reusable experience)*](#11-visualization-v6-nao-inspired-reusable-experience)
  - [11.1 Answer presentation contract](#111-answer-presentation-contract)
  - [11.2 Typed chart contract and renderer](#112-typed-chart-contract-and-renderer)
  - [11.3 Chart controls and trust](#113-chart-controls-and-trust)
  - [11.4 Implementation order](#114-implementation-order)
- [12. Evaluation and observability](#12-evaluation-and-observability)
  - [12.1 Observability view *(v4; extended in v5)*](#121-observability-view-v4-extended-in-v5)
  - [12.2 Naive baseline and deliberate trade-offs *(v4; clarified in v5)*](#122-naive-baseline-and-deliberate-trade-offs-v4-clarified-in-v5)
- [13. UX and streaming *(v6)*](#13-ux-and-streaming-v6)
- [14. Security and reliability](#14-security-and-reliability)
  - [14.1 Reliability, performance and cost](#141-reliability-performance-and-cost)
- [15. Technology choices](#15-technology-choices)
  - [15.1 Repository layout](#151-repository-layout)
  - [15.2 Decision records to write first](#152-decision-records-to-write-first)
- [16. Work breakdown and milestones](#16-work-breakdown-and-milestones)
  - [16.1 Prototype tags and per-tag evaluation *(v4)*](#161-prototype-tags-and-per-tag-evaluation-v4)
- [17. Risks and open decisions](#17-risks-and-open-decisions)
  - [17.1 Anti-patterns we reject](#171-anti-patterns-we-reject)
- [18. Demo script](#18-demo-script)
- [19. Future deployment design — not part of the current coding task *(v4)*](#19-future-deployment-design-not-part-of-the-current-coding-task-v4)
  - [19.1 Public deployment](#191-public-deployment)
  - [19.2 Protection for a public system](#192-protection-for-a-public-system)
  - [19.3 README (setup from scratch)](#193-readme-setup-from-scratch)
- [20. Submission deliverables map *(v4)*](#20-submission-deliverables-map-v4)
- [21. Prompt pack *(v4)*](#21-prompt-pack-v4)
- [22. Coding-agent setup *(v4)*](#22-coding-agent-setup-v4)
- [23. Worked walk-through of the two brief questions *(v4)*](#23-worked-walk-through-of-the-two-brief-questions-v4)
  - [23.1 "Weekly orders in one region dropped sharply last month — is that unusual, and what is driving it?"](#231-weekly-orders-in-one-region-dropped-sharply-last-month-is-that-unusual-and-what-is-driving-it)
  - [23.2 "Which customer segments are we most likely to lose next quarter, and where should we act first?"](#232-which-customer-segments-are-we-most-likely-to-lose-next-quarter-and-where-should-we-act-first)
- [24. Onboarding and connectivity flow *(v6: gated, asynchronous setup)*](#24-onboarding-and-connectivity-flow-v6-gated-asynchronous-setup)
  - [24.1 Step-by-step wizard](#241-step-by-step-wizard)
  - [24.2 Setup-job status and failure policy](#242-setup-job-status-and-failure-policy)
  - [24.3 Semantic layer and document grounding](#243-semantic-layer-and-document-grounding)
  - [24.4 Public demo versus configured installation](#244-public-demo-versus-configured-installation)
  - [24.5 Acceptance tests](#245-acceptance-tests)

---

## 1. Purpose, scope, principles

**Product:** a conversational "AI for BI" system that answers business questions from a warehouse at six levels: What, Why, So what, What next, What if, Now what. It also handles data discovery and asks clarifying questions when a question is incomplete.

**In scope:** multi-turn context, clarification, planning and decomposition, SQL plus Python analysis tools, charts for suitable numerical/analytical results (with a table or text fallback when a chart is unsuitable or unavailable), any-schema ingestion (15 to 20+ tables, extensible), evaluation, observability, refusal of questions the warehouse cannot answer, churn and at-risk-segment analysis, hardening for messy enterprise-style warehouses, large-warehouse retrieval stress tests, real-time streamed serving, and a public deployment that outsiders can use and inspect.

**Out of scope (v1):** write access to the customer's warehouse (the agent writes only to its own store, Section 9.7), free-form LLM-written Python executed on user data, multi-tenant billing, Slack/Teams channels.

**Design principles**

1. **LLM for language, code for numbers.** LLMs classify, rewrite, plan, generate SQL and narrate. All statistics, forecasts and optimisation run in deterministic, tested Python tools.
2. **Typed contracts first.** Every agent speaks versioned JSON (Section 6). Tracks can be built and tested independently.
3. **Evidence-grounded answers.** Every number in the narrative traces to a step result (an evidence record). No evidence, no claim.
4. **Cheap path first.** Precomputed insight tables, then SQL, then on-the-fly models. Tier the LLMs by task.
5. **Fail visibly.** Bounded retries, honest caveats, never a dead end (the demo showed a "risk analysis not enabled" dead end on a plain spikes question).
6. **Context is a versioned asset.** Schema docs, metric definitions and rules live as files in git and are tested like code.

### 1.1 Binding decisions

Each decision becomes a decision record (Section 15.2). Components are tagged **NOW** (needed for the demo) or **SEAM** (production interface designed now, body deferred): the interfaces are production-grade from day one, the bodies are demo-grade only where marked.

| # | Decision | Why |
| --- | --- | --- |
| D1 | Supervisor graph with typed workers; no free-roaming agent swarm | Bounded cost, replayable runs, per-agent tests |
| D2 | The plan is a typed DAG, not an opaque loop | Splits compound questions; allows parallel steps, retries and partial answers |
| D3 | The semantic layer is the only source of metric truth | "Revenue" cannot mean three things in three answers |
| D4 | Context lives as code in Git, assembled per call, and its version is stamped on every trace | Reliability comes from curated context; regressions become attributable |
| D5 | Hybrid compute: precomputed insight tables plus on-the-fly tools behind one result contract | The mentor's latency trade-off without forking the product |
| D6 | The LLM never computes numbers | Results must be reproducible |
| D7 | Every claim cites a step result, and numbers in prose are checked against it | Blocks invented numbers |
| D8 | Causal wording is tiered: A planted, B quasi-experimental, C observational | Honest attribution |
| D9 | Context resolution is a deterministic slot merge first, an LLM rewrite only when needed | Cheap and predictable for the common follow-up |
| D10 | Clarification is a policy with closed options and a 2-round cap | Never interrogate, never guess silently |
| D11 | Read-only database role, AST guard, sandboxed Python | The agent is a security boundary |
| D12 | Evaluation runs in CI with thresholds, and failures feed back into context | Reliability improves with every iteration |
| D13 (v4) | An answerability gate runs before planning, and refusal is a first-class outcome | The agent must refuse to invent a table or column and say plainly when the warehouse cannot answer |
| D14 (v4) | SQL targets canonical clean views and resolved entities, not raw messy tables | Cryptic names, duplicates and dirty values must not leak into numbers |
| D15 (v4) | Churn is a calibrated predictive model checked on a time-based holdout; its output is risk, never cause | "Likely to lose" is a prediction; "act first here" is a ranked hypothesis |
| D16 (v4) | Every prototype runs the same suites as a naive baseline, and trade-offs are chosen from a measured accuracy, latency and cost table | Trade-offs must be deliberate and visible |
| D17 (v4) | Runs are asynchronous and streamed; no user-facing call blocks on a full answer | The system behaves as a real-time application |
| D18 (v4) | A prototype tag exists only if its evaluation results are committed in the same release | How the system grew stays visible and checkable |
| D19 (v4) | The agent owns a separate writable store; analysis tables, history and traces live there, never in the customer's read-only warehouse | Read-only access to the source is kept, and precomputed intelligence still works |
| D20 (v4) | Onboarding is a defined flow: connect LLM, connect database, review the generated semantic layer, then chat | A new user can start without code changes |
| D21 (v5) | Schema retrieval, join-path selection, and value linking have dedicated quality and latency suites | Enterprise grounding is measured directly, not inferred only from end-to-end SQL accuracy |
| D22 (v5) | Router, Planner, Clarification, and Visualization Agent contracts are explicit and testable | Routing, decomposition, clarification, and chart handoff can be inspected independently |
| D23 (v6) | Chat remains locked until required onboarding checks pass; preparation runs asynchronously and is resumable | No confusing half-configured sessions; long indexing work does not block the API |
| D24 (v6) | Stream observable progress and concise decision summaries, never private hidden chain-of-thought | Users can inspect what the system is doing without exposing private internal reasoning |
| D25 (v6) | Adopt Nao-inspired chart/data/SQL inspection and Executive Story patterns through our own typed contracts | Reuse high-value UX patterns without coupling the product to Nao internals or license assumptions |
| D26 (v7) | All four agents use one scoped `MemoryService`; relational memory and semantic vector retrieval remain separate interfaces | Consistent context, access control, retention and portability across agents |

---

## 2. Mentor requirements and sign-off matrix

Every point the mentor made in the session and in the team action items is listed here with the component that satisfies it and the test that proves it. Sign-off means every acceptance test passes.

| # | Mentor said | What we build | Section | Acceptance test |
| --- | --- | --- | --- | --- |
| 1 | Define the scope first: the types of questions the system answers | Two-level taxonomy as the product contract; unsupported asks get a plain scope statement | 4 | 200-question router set, zero dead ends |
| 2 | Value is in why, forecasting and so what, not only what | Six analytical intents, each with an engine | 4, 10 | Per-class F1 ≥ 0.85; planted-driver recall at 3 ≥ 0.80 |
| 3 | Do not restrict to SQL; route some questions to Python and ML tools whose parameters come from the question | Analysis toolkit with typed parameters filled from extracted entities | 10.2 | Tool unit tests; forecast and anomaly gates |
| 4 | Break a compound question into parts (trend today plus forecast in 3 months) and combine the outputs | Planner builds a step DAG with a merge step | 6, 7 | 20 compound questions, every sub-question mapped to a step |
| 5 | Either run models on the fly or precompute result tables (anomalies, forecasts); tell the user which | Insight store plus fast and flex paths with distinct UI messages | 6.1, 9.4 | "Spikes across all months" answered from the anomaly table at p50 ≤ 2.5 s |
| 6 | When information is missing, either ask or assume defaults | Clarification policy; defaults recorded in an assumption ledger | 4.2 | Ask precision and recall ≥ 0.85 |
| 7 | "Summarize revenue" is underspecified | Clarifier offers closed options (total, trend, by region) | 4.2 | Case included in the clarifier suite |
| 8 | Upgrade metadata and synonyms | Semantic layer with synonyms, grain, dimensions and caveats | 9.2 | Synonym grounding test |
| 9 | Work for any dataset, 9 or 90 tables; make adding or connecting tables easy | Ingestion & introspection pipeline; schema slicing keeps prompts flat without modifying user tables | 5.2, 9.3 | Connect any table set with no user database changes; suites stay green |
| 10 | Why questions need causal factors in the data: stockouts, footfall, marketing budget | Candidate drivers mapped from pre-existing warehouse factors declared in semantics | 9.5 | Driver recall; a control period yields "no significant driver" |
| 11 | Handle data where external causes are absent or unmeasured | Operate directly on the ready-to-use database; do not synthesize or alter user tables; unmeasured drivers are flagged explicitly | 9.5 | Answerability & driver coverage check |
| 12 | Add visualization; an agent that picks the chart | Visualization agent with validated chart specs | 11 | ≥ 98% render; ≥ 85% appropriate |
| 13 | Data discovery questions go to the catalog | Discovery intent | 4, 9.2 | "What data do you have?" answered without SQL |
| 14 | Ask when the time range or metric is missing | Clarifier gate | 4.2 | Clarifier suite |
| 15 | Anomaly detection, Prophet forecasts, what-if (price +5%), prescriptive segments | Toolkit engines | 10 | Forecast error and coverage gates; what-if error ≤ 25% against ground truth |
| 16 | Context retention: "Mumbai in July" then "what about Delhi?"; keep the last 2 or 3 turns; an agent forms the final question | Context resolver with session memory | 8, 7.1 | ≥ 90% slot accuracy on 50 multi-turn dialogues |
| 17 | A planner decides the checks, for example five SQL steps plus one Python step | Planner | 6, 7.1 | Plan validity tests |
| 18 | Show which step is running while the user waits | Streaming event protocol and step timeline | 6.2, 13 | Ordered events on every run; no silent stage over 2 s |
| 19 | Divide the work into tracks, one owner each, then integrate | Four tracks with their own gates | 16 | Per-track exit gates |
| 20 | Define input and output JSON contracts first | Versioned contracts frozen after the first phase | 7 | Contract tests in CI; stub agents run end to end |
| 21 | Test each agent with 10, 15 up to 100 different questions | Per-agent evaluation suites | 12 | Suite sizes in Section 12 |
| 22 | Design before implementing | Decision records and the build order | 15.2, 16 | Records merged before code |
| 23 | Keep bounded SQL repair and re-planning | One initial SQL generation plus up to two repair attempts (three total SQL attempts); re-plan at most twice | 7.1, 7.2 | Retry caps tested, including exhaustion behaviour |
| 24 | Make a demo worth showing: why-style questions, context, clarification, data-science depth | Demo script | 18 | Two clean consecutive runs |

### 2.1 Problem-statement traceability *(v4; extended in v5)*

The mentor matrix above stays as is. This second matrix maps the build brief ("data scientist agent") to the design, so nothing in the brief is left implicit.

| # | Brief requirement | Where it is satisfied | Acceptance test |
| --- | --- | --- | --- |
| B1 | Work out what kind of analysis a question needs; the choice is visible in the answer | Section 4 taxonomy and router; `intent.classified` event; every answer opens with an "Analysis used" line | Router macro-F1 gate; 100% of answers carry the line |
| B2 | Data-science modules on real statistical and ML methods, each checked for correctness | Sections 10.2 to 10.4 | Per-module suites in Section 12 (anomaly F1, planted-driver recall, forecast gates, churn AUC-PR and calibration) |
| B3 | SQL only against the retrieved schema, validated by execution, repaired on failure | Sections 10.1 and 7.1, answerability gate 4.3 | SQL execution accuracy; hallucinated identifiers reaching execution = 0 |
| B4 | Refuse to invent a table or column; say plainly when the warehouse cannot answer | Section 4.3 and error codes `E_UNANSWERABLE`, `E_GROUNDING_NO_MATCH` | Refusal suite: recall, precision, over-refusal |
| B5 | A real warehouse: many tables, cryptic names, duplicated entities, messy values | Section 9.6 and the messy twin | Messy-warehouse SQL slice and entity-resolution suite |
| B6 | Root cause only as strong as the evidence; pattern kept apart from cause | Section 7.5 tiers, Section 10.3, composer sections "Observed pattern" and "Possible causes" | Control-month test; wording lint on every narrative |
| B7 | Show the queries, the method and the numbers behind each answer | Evidence panel (Section 13), step results (Section 7.3) | Numeric fidelity at least 98%; 100% of answers expose SQL and method |
| B8 | Accuracy, latency and cost against a naive baseline, with deliberate trade-offs | Section 12.2 | Comparison table committed for every tag |
| B9 | Evaluation framework with metrics for this problem, run on every prototype | Sections 12 and 16.1 | `evals/results/<tag>.json` exists for every tag |
| B10 | Observability showing problem metrics next to accuracy, latency and cost | Section 12.1 | Metrics page lists every gated metric per tag and live |
| B11 | Deployed at a public URL; any input inspectable step by step | Sections 19 and 13 | External smoke test; run inspector opens for any run id |
| B12 | Tagged prototypes from first end-to-end slice to final | Section 16.1 | Tags `v0.1` to `v1.0` in git |
| B13 | Repository contents: README, APPROACH.md, ARTEFACT.md, diagrams, data-generation code, prompt pack, eval framework, observability, coding-agent setup, no secrets | Sections 15.1, 20, 21, 22 | Repository checklist in Section 20 passes in CI |
| B14 | Both example situations work end to end | Section 23 | Two scripted runs in the demo |
| B15 *(v5)* | Schema retrieval must find and rank the correct tables, columns, and join paths | Sections 9.2 and 12 | Recall@K, MRR/nDCG, grounding accuracy, join-path accuracy, latency and cost are reported per prototype |
| B16 *(v5)* | Enterprise-scale behaviour must be tested beyond the 20-table demo | Sections 5.2 and 12 | Repeatable 20-, 200-, and 1,000+-table benchmarks plus large-row and concurrency tests |
| B17 *(v5)* | Dirty, misspelled, and ambiguous filter values must be resolved safely | Sections 9.6 and 12 | Labelled value-linking precision/recall; ambiguous values trigger clarification instead of silent guessing |
| B18 *(v5)* | Router, Planner, Clarification, and Visualization Agents have visible responsibilities and handoffs | Sections 4, 6, 7 and 11 | Dedicated contract tests and observable events for each agent |

---

## 3. What we take from the reference links

**nao (getnao.io, open-source agentic BI).** It is a BI builder rather than a data-science engine, so we borrow practices, not the product.

- *Context layer as files:* per-table `columns.md`, `preview.md`, `profiling.md`, plus `docs/business_definitions.md`, `glossary.md`, `semantics/main_metrics.md`, `RULES.md`, and `tests/*.yaml`. We adopt this layout for our knowledge layer (Section 9). Their published figures claim reliability rising from 15% with no context to 85% after context rework. This is vendor-reported, but the direction (context work beats model work) matches our experience, so we invest early.
- *Offline eval (`nao test`):* expected-SQL test cases scored per context change, reporting success %, an "always passes" %, cost and time. We adopt the same report shape for our CI gate (Section 12).
- *Online observation:* chat replay, and error/downvote mining that proposes context fixes as pull requests. We adopt a lighter version: trace store, thumbs feedback, and a weekly context-recommendation report.
- *Chart tool and stories:* the agent calls a `display_chart` tool, and reusable live dashboards exist. We adopt the chart tool pattern; "stories" is a stretch goal.
- *Operations:* identity passthrough with row-level security, bring-your-own LLM key with budgets, MCP exposure. We adopt RLS passthrough and per-user budgets in the security design; we do not use MCP, and all connectivity is through APIs.
- *Not adopted:* hosted product, SSO stack, Slack/Teams channels (out of scope).

**Prophet (quick start).**

- Input is a dataframe with `ds` (date) and `y` (numeric). The flow is `fit`, `make_future_dataframe(periods=...)`, `predict`, which returns `yhat`, `yhat_lower`, `yhat_upper`. `plot_components` gives trend and seasonality, and Plotly versions exist for interactive charts. The docs say fitting takes roughly 1 to 5 seconds for their example.
- Consequences: (a) the forecast tool's contract maps directly to `kpi, dimension, horizon` to a table of `ds, yhat, lower, upper`, (b) the prediction interval is mandatory output, (c) a few seconds per fit makes on-the-fly forecasting acceptable for a single series but too slow for every KPI x dimension, so we precompute common ones (Section 9), (d) component plots feed the narrative ("trend up, weekly seasonality peak on Fridays"), (e) Prophet needs enough history to see seasonality, so short series fall back to ETS or a naive baseline, and we report which method ran. Promotions or stockouts can be handled as extra regressors or special days (verify against Prophet's regressor docs when implementing).

**Database & Synthetic-Data Evaluation Note:**
- The application connects directly to a pre-existing, ready-to-use user database (`ecommerce.sqlite` or any supported relational database).
- Relational synthesis libraries (**SDV, CTGAN, Mimesis, Faker**) are **not required as application runtime dependencies**; the system does not alter or synthesize tables in the user's warehouse.
- Synthetic-data and planted-scenario concepts remain relevant only as offline evaluation benchmarks or reference test fixtures to verify diagnostic and refusal capabilities, never for expanding tables in the user's database.

---

## 4. Question taxonomy (the scope contract)

| Intent | Sub-intents | Example | Engine | Output |
| --- | --- | --- | --- | --- |
| discovery | catalog, schema, metric definition | "What data do you have?" | Catalog lookup | Tables, descriptions, sample questions |
| what | describe, trend, rank, compare, distribution | "Q3 sales by region" | SQL agent (+pandas) | Table + chart |
| why | diagnose, decompose, correlate | "Why did revenue drop in March?" | SQL + decomposition + tests | Ranked drivers + waterfall |
| so\_what | significance, impact, anomaly | "Is this dip significant?", "What are the spikes across all months?" | Statistics + insight tables | Verdict + impact in currency and % |
| what\_next | forecast, churn\_risk | "Forecast next quarter", "Which customer segments are we most likely to lose next quarter?" | Prophet or ETS with backtest; calibrated churn model (Section 10.4) | Forecast + interval; ranked at-risk segments with uncertainty |
| what\_if | scenario, sensitivity | "What if we raise price 5%?" | Elasticity + Monte Carlo | Range + tornado chart |
| now\_what | optimize, segment, recommend | "Which segment should we target?" | Optimization, clustering | Ranked actions + trade-offs |
| clarify | missing, ambiguous, out of scope | "Summarize revenue" | Clarifier | One question + options |
| refuse *(v4)* | unanswerable, out of data scope, insufficient history | "Revenue by sales rep" when no rep data exists | Answerability gate (Section 4.3) | Plain reason, what is missing, nearest answerable alternatives |

Typical chain: what, why, so what, what next, what if, now what. Follow-ups inherit metric, filters and time range, so "why?" after a "what" goes straight to the diagnostic engine.

### 4.1 Router Agent rules *(v5; implementation node: IntentExtractor + route policy)*

The **Router Agent** owns the first analytical routing decision and is distinct from the Planner. It emits `intent`, `sub_intent`, `route`, confidence, a one-line rationale, required slots, and any missing slots. Routes include catalog/data discovery, SQL lookup, SQL plus statistics, anomaly/root-cause analysis, forecasting/churn, what-if simulation, prescriptive optimization, clarification, or refusal. The implementation may keep the existing `IntentExtractor` node and `intent_extractor` prompt name, but its public contract must expose the Router Agent's route decision explicitly.

"What are the spikes across all months?" is `so_what/anomaly`, not a generic lookup or churn-risk route. Below a confidence floor of 0.65, the Router Agent requests clarification with options drawn from the taxonomy. It may not silently route an unknown intent to an arbitrary engine. No route may answer "X is not enabled": it falls back to the closest supported engine or states the supported scope in one sentence. Confidence comes from constrained-decoding log-probabilities or a small verifier model, not the model's self-report, and calibration error is reported in the router suite. Every answer displays the chosen route in its "Analysis used" line.

### 4.2 Clarification policy

```text
ask  iff  (a required slot is missing  OR  ambiguity_impact >= 0.6)
          AND rounds < 2  AND a closed option set exists
else proceed with defaults and record each default in the assumption ledger
```

Required slots: what = metric + time range; why = metric + period + population; what\_next = metric + horizon; what\_if = lever + magnitude; now\_what = objective + constraints. `ambiguity_impact` (0 to 1) is a cheap-model estimate of how far two readings of the question differ. Options must exist in the catalog or semantic layer and always include "something else". The target ask rate is 10 to 20% of questions: higher annoys users, lower means silent guessing.

**Independent trigger rule *(v5):** the Clarification Agent can be invoked by the Router (uncertain intent or missing required slot), Grounder (multiple candidate bindings or a low-confidence value/entity match), Answerability Gate (a resolvable missing metric/dimension/join choice), Planner (a sub-question cannot be planned without a decision), or Verifier/executor (a failure whose correction requires user intent, such as an empty result caused by an ambiguous filter). The caller passes the unresolved slot, available catalogue-backed options, and prior clarification count. Clarification cannot override a genuine `refuse` outcome: if required data does not exist, explain the missing data instead of asking the user to choose a fabricated field.

### 4.3 Answerability gate and refusal policy *(v4)*

The gate sits after the Grounder and before the Clarifier and Planner. It decides whether the warehouse can support the question at all, so the agent never reaches SQL generation with a request it cannot ground.

**Checks (all deterministic except the near-miss ranking):**

1. **Identifier grounding.** Every metric, entity, dimension and filter value in the question must resolve to a catalog or semantic-layer item with a match score at or above a threshold. The Grounder may only choose from a closed candidate list, and it has an explicit `NO_MATCH` output.
2. **Join path.** A join path from the metric's grain to each requested dimension exists in the join graph.
3. **Data sufficiency for the analysis.** Time coverage, row count and history meet the module's minimums (for example anomaly detection needs a stated minimum history per series, churn needs repeat purchases per customer, forecasting needs at least two seasonal cycles or falls back to a simpler method).
4. **Measured versus unmeasured causes.** For a why question, the candidate drivers in `drivers.yaml` that exist in the warehouse are listed. If the likely driver is unmeasured (for example competitor actions with no competitor data), the answer says so.
5. **Policy.** PII, unapproved tables and write requests are blocked (Section 14).

**Outcomes**

| Outcome | When | What the user gets |
| --- | --- | --- |
| answerable | All checks pass | Normal flow |
| answerable with assumptions | A default fills a non-blocking gap | Answer plus entries in the assumption ledger |
| partially answerable | Some sub-questions pass, some fail | The supported part, plus a plain statement of what could not be assessed and why |
| clarify | A closed option set can resolve the gap | One question with options (Section 4.2) |
| refuse | A required table, column, entity or history does not exist | A short refusal: what was asked, what is missing, what data would make it answerable, and 2 to 3 nearest questions the warehouse can answer |

**Refusal message contract**

```json
{"status": "refused", "code": "E_UNANSWERABLE",
 "asked_for": "revenue by sales rep",
 "missing": [{"kind": "column", "term": "sales_rep", "closest": ["seller_id (marketplace seller)"], "score": 0.41}],
 "would_make_it_answerable": "A table or column that links orders to a sales representative.",
 "alternatives": ["Revenue by seller", "Revenue by state", "Revenue by product category"]}
```

**Rules that keep the system honest**

- A generated query is rejected before execution if any identifier is not in the schema slice (sqlglot lineage check). A rejection is logged as a would-be hallucination, and the measured rate reaching execution must stay at zero.
- Refusal and clarification are different: clarify when a closed option set exists, refuse when the data is absent. The gate never turns a refusal into a guess.
- Over-refusal is measured as carefully as under-refusal. Near-miss answerable questions are part of the suite (Section 12).
- Refusals are cheap: the gate uses retrieval scores and catalog checks, so no large-model call is spent on an unanswerable question.

---

## 5. System architecture

```text
 UI (chat + charts + live step stream)   <--- SSE events
        |
 API / Session service (auth, RLS identity, rate and cost budgets)
        |
 Orchestrator (LangGraph state machine, persisted state)
   ContextResolver -> IntentExtractor -> Grounder -> AnswerabilityGate -> [Clarifier | Refusal]
        -> Planner -> Executor (DAG of steps) -> Verifier
        -> Visualizer -> Composer -> (write to memory)
        |                  |                    |
   SQL Agent        Insight Store reader   Analysis Toolkit (Python)
        |                  |                    |
   Warehouse (read-only)  Insight tables    Sandboxed workers

 Knowledge layer: context files (git) + vector index + semantic/metric registry
 Platform: trace store, eval harness (CI), cost meter, feedback loop
```

**Layers**

1. **Experience:** web chat, chart renderer, step timeline, clarification buttons, suggested follow-ups.
2. **Orchestration:** LangGraph graph, state persisted per session; every node is idempotent and emits events.
3. **Agents:** LLM-driven nodes with strict JSON output.
4. **Engines:** SQL agent, insight-store reader, Python toolkit, catalog service.
5. **Data and knowledge:** warehouse, insight tables, context files, vector index, conversation store.
6. **Platform:** tracing, evaluation, security, cost control.

### 5.1 Demo versus production

| Concern | Demo (NOW) | Production (SEAM) |
| --- | --- | --- |
| Compute | Local API and web processes; run directly in the development environment | Future option: separate API and worker processes if measured workload requires it |
| Queue | In-process queue for current development | Future option only: a managed queue if measured requirements justify it; Redis is not part of the current stack |
| State | LangGraph checkpoint with local SQLite application store | Future option: selected durable relational store; do not introduce a second workflow engine without an approved design change |
| Warehouse | Supplied SQLite file (`ecommerce.sqlite`) | Read-only customer database connection or read replica (Snowflake, BigQuery, PostgreSQL, MySQL) |
| Vectors | Local vector index or test adapter behind `VectorMemoryIndex`; BM25 fallback | Future option: compatible vector service only if evaluation justifies it |
| Artifacts | Local filesystem/Parquet as needed for development | Future option: object storage if artifact size or sharing needs justify it |
| LLM | Model gateway, two to three providers | Same, plus per-tenant keys and cost quotas |
| Observability | Structured logs and traces in the application-owned database; local run inspector | Future option: external tracing and metrics infrastructure if needed |

### 5.2 Scaling model

- **More users:** API and orchestrator pods are stateless. Run state lives in the checkpointer, so any pod can resume any run. Autoscale on request rate and queue depth.
- **Heavy compute:** model fits and simulations run in a separate worker pool behind the queue, so a slow forecast cannot starve chat traffic. Per-user and per-tenant concurrency caps apply.
- **More tables:** the SQL agent receives a schema slice (relevant tables, columns, join keys, a few exemplars), never the full schema, so prompt size stays bounded at 20, 200, or 1,000+ tables. Retrieval indexes are partitioned by tenant.
- **Prove scale rather than assume it *(v5):** run the same frozen retrieval/SQL workloads at 20, 200, and 1,000+ tables with increasing distractor tables, look-alike names, and wide schemas; report retrieval quality, grounding errors, p50/p95 latency, token use, cost and memory. Separately test large row counts and concurrent sessions so schema scale and data-volume scale are not conflated.
- **More data:** insight jobs run incrementally by partition and publish a freshness stamp. The planner prefers fresh tables and falls back to the flex path.
- **More warehouse load:** every query passes a cost guard (limits, timeouts, no cross joins), results are cached by plan hash, and heavy analysis reads from replicas.
- **More teams or tenants:** per-tenant context repository, semantic layer, row policies, quotas and model keys (Section 14).

### 5.3 Diagram synchronization checklist *(v5)*

Keep both supplied diagrams aligned with the runtime contract; exported PNGs and editable draw.io sources must represent the same flow as Sections 4–13.

- **Question to Answer Flow:** show ContextResolver/memory; Router Agent; Grounder and Answerability Gate; separate Clarification and Refusal branches; Planner DAG; SQL and Python/ML execution; verification and bounded re-planning; Visualization Agent; evidence-backed Composer; saved answer/follow-up loop; data warehouse and insight-store boundaries.
- **Question Types and Engines:** show discovery plus What, Why, So what, What next, What if, and Now what routes; include anomaly/data-quality screening before treating a spike as a business event, churn prediction plus segment prioritisation, and the rule that observational associations are not stated as proven causes.
- Label the four named agents explicitly (Router, Planner, Clarification, Visualization), and keep retry counts and status/event names consistent with the text. Update the diagrams whenever a route, contract, or retry policy changes.

---

## 6. Workflow (runtime)

1. **Load context.** Fetch the last 3 turns (question, resolved question, answer summary, active filters).
2. **Resolve.** Rewrite the new input into a standalone question and an inherited-frame delta.
3. **Route and extract entities.** The Router Agent outputs route/intent, confidence, rationale, metric, dimensions, time range, horizon, and missing fields.
4. **Ground and check answerability.** Map terms to metrics and tables through the semantic layer and retrieval. Detect ambiguity (gross vs net) and missing coverage. *(v4)* Run the answerability gate (Section 4.3): answerable, answerable with assumptions, partially answerable, clarify, or refuse with a reason and alternatives.
5. **Clarify gate.** Any eligible upstream node can invoke the Clarification Agent. If blocking fields are missing or confidence is below threshold, ask one targeted question with catalogue-backed options (max 2 rounds, then proceed only with stated assumptions where safe). The user's reply re-enters at routing/entity extraction.
6. **Plan.** Decompose into a DAG of steps (for example 5 SQLs plus 1 Python step). Prefer insight-store lookups when a precomputed table covers the request.
7. **Execute.** Run steps in dependency order. Emit `step_started` / `step_finished` events.
8. **Verify.** Check results are sound (non-empty, plausible ranges, sample size, interval sanity). On failure, re-plan (max 2), else answer with caveats.
9. **Visualize.** The Visualization Agent receives verified result artifacts, selects and validates a chart where appropriate, and emits `chart.ready` to the UI; table/text remains the fallback.
10. **Compose.** Narrative, chart, assumptions, confidence, evidence references, follow-up suggestions.
11. **Persist.** Write the turn to the conversation store and trace store.

**Hard limits:** at most 2 clarification rounds; one initial SQL generation plus at most 2 SQL repair attempts (3 total SQL attempts); at most 2 plan re-plans; per-step timeout; row cap on returned data; per-question token, wall-clock, and cost budgets.

&#91;embedded content: runtime workflow · 8 stages, 1 decision, 2 loops&#93;

A question runs through context resolution, Router Agent classification, grounding and answerability. Any eligible node can request clarification (at most 2 rounds); unanswerable requests take the refusal branch. Otherwise the Planner Agent builds a typed DAG, the executor runs bounded steps, and the Verifier accepts the evidence or triggers at most 2 re-plans. The Visualization Agent hands a validated chart to the UI when useful, the Composer cites evidence, and the saved answer supplies inherited context for follow-ups.

Soft stage budgets: resolve 250 ms, classify 600 ms, ground 400 ms, plan 1.5 s, verify 300 ms, visualize 400 ms, compose 2 s. Execution is bounded per step and by a run budget of tokens, wall-clock time and step count that the orchestrator enforces.

### 6.1 Fast path and flex path

|  | Fast (precomputed) | Flex (on the fly) |
| --- | --- | --- |
| Trigger | The planner finds coverage in the insight index (KPI, dimension, period) | No coverage, a custom slice, or a scenario |
| Latency target | p50 ≤ 2.5 s, p95 ≤ 5 s | p50 ≤ 12 s, p95 ≤ 45 s, hard cap 90 s |
| UI message | "Looking up the anomaly table…" | "Running the forecast model…" with an elapsed timer |
| On failure | Fall back to flex | Partial answer with a caveat |

Both paths return the same step-result contract (Section 7.3), so downstream agents never know which path ran. This is the most important interface in the system.

### 6.2 Streaming event protocol *(v6: progress + safe thought summaries)*

Runs and onboarding jobs use durable, ordered event streams. SSE is the initial transport; clients reconnect with `Last-Event-ID` and can recover from the persisted event log. Event payloads are versioned, typed, redacted, and contain stable run/job identifiers.

```text
run.started                 {run_id, turn_id, status}
context.resolved            {standalone_question, inherited, is_followup}
agent.started               {agent, task_label}
intent.classified           {intent, sub_intent, confidence}
decision.summary            {stage, summary, evidence_refs[], confidence?}
grounded                    {tables[], metrics[], dims[]}
answerability.checked       {outcome, missing[], assumptions[]}
refusal.issued              {code, asked_for, missing[], alternatives[]}
clarification.required      {clarify_id, question, options[], round}
plan.created                {steps[{id,label,tool,path}], estimated_ms}
step.started                {id, label, agent?, tool?}
step.progress               {id, pct?, status_message?}
tool.started                {id, tool, safe_input_summary}
tool.completed              {id, elapsed_ms, artifact_id?, output_summary?}
step.completed              {id, elapsed_ms, artifact_id?}
tool.failed                 {id, error_code, safe_message, will_retry}
verification.completed      {status, checks[]}
chart.ready                 {spec_version, artifact_id, chart_type, source_step_ids, fallback?}
answer.delta                {text_delta}   # final answer only; optional
answer.ready                {answer_id, headline, followups[]}
run.completed               {elapsed_ms, tokens, cost}
run.failed                  {error_code, safe_message, retryable}
```

`decision.summary` is a short, user-safe explanation of the current action (for example, “Using the orders and order_items tables because they contain the requested date, region, and revenue fields”). It is not a raw reasoning trace. **Do not stream hidden chain-of-thought, private scratchpads, full internal deliberations, secret prompts, credentials, or unredacted sensitive row values.** Instead expose status, selected route, key evidence references, concise rationale, assumptions, checks, tool names, SQL after safety validation, and execution summaries. Token-by-token streaming is reserved for the final user-facing answer, not internal reasoning.

The UI renders events as an inspectable timeline; progress is real progress rather than invented percentage. A clarification pauses the run until the user responds. On reconnect, replay persisted events from the last event id. Events are idempotent and ordered per run.

### 6.3 Degradation matrix

| Failure | Degrade to | User sees |
| --- | --- | --- |
| Chart spec invalid | Table only | "Chart unavailable, showing the table." |
| Forecast fails or backtest is poor | Descriptive trend with a caveat | "Forecast unreliable for this horizon; showing the trend." |
| One plan branch fails | Partial answer from the other branches | "Partial result: driver X was not evaluated." |
| Grounding fails | Clarify with catalog options | "I don't have a metric for X. Did you mean…?" |
| Budget exhausted | Best available evidence plus a caveat | "Stopped early due to the time budget." |
| LLM provider down | Fallback model, then rules | "Running in degraded mode." |

### 6.4 Real-time operation *(v4)*

The system is built as a streaming, asynchronous application, not a request and response form.

**Request lifecycle**

1. `POST /runs` validates input, stores the run and returns `202` with `run_id` immediately (under 200 ms).
2. `GET /runs/{id}/events` is an SSE stream (a WebSocket is optional). Events carry ids and can be resumed from the last id after a dropped connection. A heartbeat every 10 s keeps proxies from closing it.
3. The orchestrator runs on a worker. Fast-path steps run in the API worker; flex-path model fits go to the worker pool through the queue, and the UI shows an elapsed timer.
4. Results arrive progressively: plan and steps first, then the evidence table, then the chart, then the narrative streamed token by token. The final `answer.ready` event closes the run.
5. `POST /runs/{id}/cancel` stops a run and releases its resources. A client disconnect does not cancel the run (it can be resumed), but an idle run expires.

**Freshness**

| Concern | Mechanism |
| --- | --- |
| New warehouse data | Insight jobs run incrementally by partition (micro-batch, interval set per KPI). Each insight table carries `as_of` and `run_id`. |
| Staleness shown to the user | Every answer states "Data as of ..." and flags any insight table older than its freshness limit; the planner then prefers the flex path. |
| Consistency inside a run | One data snapshot id per run (Section 14.1), so a mid-run refresh cannot mix two versions. |
| Proactive monitoring (optional, SEAM) | A scheduled detector runs `detect_anomalies` on registered KPIs and writes alerts to the insight store; the UI shows an "Unusual now" panel. |

**Capacity and protection**

- Admission control: per-user and per-IP concurrency caps, queue-depth limit with a clear "busy, retry in N s" response, and a global daily cost cap for the public deployment.
- Backpressure: flex-path jobs are queued FIFO per tier; fast-path requests are never blocked behind model fits because they use separate worker pools.
- Timeouts: stage budgets from Section 6, per-step timeouts, and the 90 s hard cap.
- Caching: plan-hash cache (Section 14.1) plus a semantic cache for paraphrases of the same standalone question, both keyed by context version and data snapshot id so a data or prompt change invalidates them.
- Live metrics: counters and histograms (run latency by stage and path, queue depth, tokens, cost, repair count, refusal count) are emitted per run and appear on the metrics page (Section 12.1) within seconds.

**Latency budget by path**

| Path | Target |
| --- | --- |
| Lookup on the fast path (precomputed or compiled metric) | p50 at most 2.5 s, p95 at most 5 s |
| Generated SQL lookup | p50 at most 6 s, p95 at most 15 s |
| Flex-path analysis (anomaly, driver analysis, churn scoring for a custom slice) | p50 at most 12 s, p95 at most 45 s |
| Refusal | p50 at most 1.5 s (no large-model call) |

---

## 7. Agents and contracts

| Agent | Responsibility | LLM tier | On failure |
| --- | --- | --- | --- |
| ContextResolver | Standalone rewrite, inherit frame | small | Use raw question, flag low confidence |
| **Router Agent / IntentExtractor** *(v5)* | Choose foundational route; classify intent/sub-intent; return confidence, rationale, required/missing slots | small + rules | Clarify; never route an unknown intent arbitrarily |
| Grounder | Retrieve and rank metrics/tables/columns/values; check grain and join path | small + hybrid retrieval | Clarify candidate ambiguity or request catalog discovery |
| AnswerabilityGate *(v4)* | Identifier, join, data-sufficiency and driver-coverage checks; refuse or partial-answer | rules + retrieval scores | Refuse with reason and alternatives |
| **Clarification Agent / Clarifier** *(v5)* | Independently handle resolvable missing/ambiguous inputs raised by Router, Grounder, Gate, Planner or Verifier | small + closed options | After 2 rounds, use safe stated defaults or return a clear limitation; never invent missing data |
| **Planner Agent / Planner** *(v5)* | Decompose compound request into a typed DAG with dependencies, parallel groups, merge rules, fallback, and estimated resources | large | Explicit single-step fallback or partial plan with caveat |
| SQL Agent | NL to SQL, validate, run, repair | large (generate), small (repair) | Report failure with reason after bounded attempts |
| Analysis Toolkit | Deterministic Python tools | none | Typed error, Verifier decides |
| Verifier | Soundness checks, re-plan trigger | rules + small | Caveated answer or bounded re-plan |
| **Visualization Agent / Visualizer** *(v5)* | Select suitable chart from verified result shape/intent, validate chart spec, hand off to UI | rules + small annotation model | Table/text fallback |
| Composer | Narrative with evidence refs | large | Template answer |
| Memory writer | Store turn summary and resolved slots | small/rules | Keep run result; log persistence error |

### 7.0.1 Explicit contracts for the four named agents *(v5)*

| Agent | Required input | Required output | Trigger / handoff | Minimum evaluation |
| --- | --- | --- | --- | --- |
| Router Agent | Standalone question, resolved frame, taxonomy/catalog snapshot | `route`, `intent`, `sub_intent`, confidence, rationale, required slots, missing slots | Runs after context resolution; sends route to Grounder/Answerability Gate and asks Clarification Agent on uncertainty | 200 labelled questions; macro-F1, per-class recall, calibration, zero dead ends |
| Planner Agent | Grounded standalone question, route, answerability outcome, available tools/insight coverage, budgets | Typed DAG of sub-questions/steps, dependencies, parallel groups, merge rule, fallback plan, estimated latency/cost/steps | Runs only when answerable/partially answerable; hands steps to Executor | Compound-question coverage and DAG validity; every sub-question maps to a step; dependencies acyclic; step cap obeyed |
| Clarification Agent | Triggering node, unresolved slot, valid candidate options, prior rounds, current frame | One targeted question, closed options, reason, round/max rounds, safe default if applicable | May be invoked independently by Router, Grounder, Answerability Gate, Planner, or Verifier/executor | Precision/recall, option validity, no fabricated options, max 2 rounds, refusal not converted to a guess |
| Visualization Agent | Verified result artifact/DataFrame, column types, units, intent, source step IDs | Chart/no-chart decision, chart type rationale, validated Vega-Lite/Plotly spec, title, axes/units, alt text, source-step refs | Runs after verification; emits `chart.ready` and sends artifact/spec to frontend renderer | 100 result-shape tests; render success ≥98%, appropriateness ≥85%, table fallback on invalid specs |

The four public agent names are product/architecture responsibilities. They may map to existing implementation nodes (`IntentExtractor`, `Planner`, `Clarifier`, `Visualizer`) without requiring four separate LLM processes. The route choice and handoffs must nevertheless appear in contracts and traces.

**Common envelope** (every message):

```json
{
  "schema_version": "1.0",
  "request_id": "uuid", "session_id": "uuid", "turn_id": 4, "trace_id": "...",
  "agent": "planner",
  "status": "ok | needs_clarification | partial | error",
  "payload": {},
  "error": null,
  "usage": {"tokens_in": 0, "tokens_out": 0, "cost": 0.0},
  "timings_ms": {},
  "context_version": "hash of the compiled context repository",
  "data_snapshot_id": "the snapshot every step of this run reads"
}
```

**Key payloads**

```json
// ContextResolver out
{"standalone_question": "Revenue in Delhi in July 2018",
 "inherited": {"metric": "revenue", "time_range": "2018-07", "filters": {}},
 "changed": {"filters": {"city": "Delhi"}}, "confidence": 0.92}

// Router Agent out (implemented by IntentExtractor + route policy)
{"route": "sql_plus_diagnostic", "intent": "why", "sub_intent": "decompose",
 "confidence": 0.86, "rationale": "The user asks what drove a metric change.",
 "required_slots": ["metric", "period", "population"],
 "entities": {"metric": "revenue", "dimensions": ["category"],
   "time_range": {"start": "2018-03-01", "end": "2018-03-31"},
   "compare_to": "previous_period", "horizon": null},
 "missing": []}

// Clarifier out
{"question": "Which revenue do you mean?", "options": ["Gross", "Net"],
 "round": 1, "max_rounds": 2, "default_if_skipped": "Net"}

// Planner Agent out
{"sub_questions": ["Summarise revenue trend", "Forecast revenue for 3 months"],
 "steps": [
  {"id": "s1", "tool": "sql_agent", "args": {"question": "..."}, "depends_on": [], "parallel_group": "a"},
  {"id": "s2", "tool": "forecast", "args": {"kpi": "revenue", "horizon_months": 3}, "depends_on": [], "parallel_group": "a"},
  {"id": "s3", "tool": "merge", "args": {}, "depends_on": ["s1", "s2"]}],
 "merge_rule": "align historical and forecast series by date",
 "fallback_plan": {"steps": ["s1"], "reason": "Forecast tool unavailable"},
 "estimated_ms": 8500, "estimated_cost": 0.02, "uses_insight_store": false}

// Step result (evidence record)
{"step_id": "s2", "tool": "forecast", "method": "prophet",
 "result_ref": "res_7f3", "columns": ["ds", "yhat", "lower", "upper"],
 "stats": {"backtest_mape": 0.08}, "assumptions": [], "confidence": "medium"}

// Composer out
{"narrative": "...", "claims": [{"text": "...", "evidence": ["res_7f3"]}],
 "chart": {"library": "vega-lite", "spec": {}}, "assumptions": [],
 "confidence": "medium", "follow_ups": ["What if we raise price 5%?"]}
```

Contracts are Pydantic models in a shared package. A schema change needs a version bump and sign-off from the producing and consuming owners.

### 7.1 Agent policies

- **ContextResolver:** tier 1 is deterministic: copy the previous slots and override only what the user names ("what about Delhi?" sets the city and keeps metric, period and grain). Tier 2, an LLM rewrite, runs only when tier 1 confidence is below 0.8 or the message has pronouns or ellipsis it cannot resolve. An explicit user statement always beats an inherited value, a topic shift resets filters, and it never invents a slot. An unresolvable reference becomes a clarification.
- **Router Agent / IntentExtractor *(v5)*:** temperature 0, structured output, few-shot examples per class plus hard negatives. It chooses an explicit foundational route and emits confidence, rationale, required/missing slots, and intent. Below 0.65 confidence it invokes the Clarification Agent and never maps an unknown class to an arbitrary engine.
- **Grounder:** exact alias match, then fuzzy or embedding top-k, then LLM disambiguation restricted to the candidate list (it may not invent). It checks that the metric exists, a join path exists, the grain fits, a time field exists and the dimension is allowed for that metric.
- **AnswerabilityGate *(v4)*:** implements Section 4.3. It consumes the Grounder's candidate scores and the catalog, never a free-form LLM judgement, and emits one of five outcomes. Thresholds are tuned on the refusal suite, and the chosen operating point (recall versus over-refusal) is recorded in a decision record.
- **Entity and value handling *(v4)*:** filter values are linked against the per-column value index (Section 9.6) so the agent filters on a value that exists (for example `'sao paulo'` versus `'São Paulo'`), and counts of people or accounts use the resolved entity id.
- **Planner Agent / Planner *(v5)*:** prefers the fast path when the insight index covers the request; emits each sub-question, step, dependencies, parallel group, merge rule, resource estimate, and fallback plan; independent branches run in parallel; at most 8 steps; every plan carries a fallback plan.
- **SQL agent:** schema slice only; sqlglot parse; reject DDL, DML, COPY and ATTACH; allow-list tables and columns; reject cross joins; enforce LIMIT and an explicit time filter; EXPLAIN dry run; statement timeout and row cap; one initial generation plus at most 2 repair attempts (3 total SQL attempts), driven by the error taxonomy. Each repair cause is logged as a candidate learning.
- **Analysis tool agent:** a thin wrapper that maps entities to typed parameters and checks preconditions (row count, date coverage, series length) before a tool runs.
- **Visualization Agent / Visualizer *(v5)*:** receives verified result artifacts rather than unverified intermediate tables; uses deterministic intent/result-shape rules to select a suitable chart; validates the chart spec; emits `chart.ready` with an artifact/source-step reference for the UI. If no useful chart exists or validation fails, the UI receives a table/text fallback.
- **Composer:** structured generation with step citations. Sections are headline, narrative, evidence, chart where suitable, assumptions, confidence, caveats and 2 to 3 follow-ups. Wording follows the causal tier, and a numeric-fidelity pass blocks any number not found in a step result.
- **Memory writer:** stores the turn summary, resolved slots and preferences; asynchronous and idempotent per session and turn.

### 7.2 Verifier checks

| Check | Fails when | Action |
| --- | --- | --- |
| Non-empty | Zero rows | Repair by relaxing the filter, then clarify |
| Grain and shape | Result grain differs from the request | Re-plan |
| Unit and scale | Wrong magnitude | Repair |
| Coverage | Requested window is not fully present | Caveat and state the coverage |
| Plan alignment | A sub-question has no step | Re-plan |
| Statistical validity | Sample too small or test assumptions violated | Switch test or lower confidence |
| Forecast quality | Backtest error above 20% or interval coverage outside 0.85 to 0.98 | Choose another model or caveat |
| Numeric fidelity | Numbers in the prose are absent from step results | Regenerate the narrative |
| Safety | PII or an unapproved table | Block |
| Entity integrity *(v4)* | A count of customers, orders or accounts ignores the entity map and duplicates inflate it | Re-run on the resolved entity id |

Retry budget: repair at most 2, re-plan at most 2, then compose with caveats. A bad answer is never returned silently.

### 7.3 Step result and confidence

Every SQL and tool step, fast or flex, returns this contract.

```python
class ToolResult(BaseModel):
    tool: str
    params: dict
    artifact_id: str            # Parquet or CSV in the artifact store
    columns: list[ColumnSpec]
    summary_stats: dict
    method: str                 # e.g. "prophet", "ets", "sql"
    assumptions: list[str]
    warnings: list[str]
    confidence: Confidence      # level, score, basis
    data_snapshot_id: str
    seed: int | None
    elapsed_ms: int

class Confidence(BaseModel):
    level: Literal["high", "medium", "low"]
    score: float                # 0..1, computed
    basis: list[str]            # e.g. "n=4821", "MAPE=7.2%"
```

Confidence is computed, not self-reported. High needs a sample of at least 1,000, statistical power of at least 0.8, an interval narrower than 20% of the estimate, full data coverage and a backtest error under 10%. Low applies for a sample under 100, coverage under 70%, a backtest error over 20%, or an observational-only causal claim. These are starting values to tune on the evaluation sets. The composer derives its wording from this object.

### 7.4 Error taxonomy

| Code | Meaning | Retry | Remediation |
| --- | --- | --- | --- |
| E\_INPUT\_INVALID | Malformed or empty input | No | Ask again |
| E\_GROUNDING\_NO\_MATCH | Term not in the catalog | No | Clarify |
| E\_UNANSWERABLE *(v4)* | The warehouse lacks a required table, column, entity or history | No | Refuse with reason, what is missing and alternatives |

| E\_ENTITY\_AMBIGUOUS *(v4)* | Several resolved entities could match the name or key | No | Clarify with the candidate entities |
| E\_IDENTIFIER\_NOT\_IN\_SCHEMA *(v4)* | A generated query names an identifier outside the schema slice | Yes (once, constrained) | Regenerate with the allowed list; count as a would-be hallucination |
| E\_AMBIGUOUS | Several possible bindings | No | Clarify |
| E\_SQL\_SYNTAX | Parse error | Yes | Repair |
| E\_SQL\_SEMANTIC | Wrong columns or grain | Yes | Repair |
| E\_SQL\_UNSAFE | DDL, DML or allow-list violation | No | Block and audit |
| E\_SQL\_TIMEOUT | Statement timeout | Once | Simplify |
| E\_TOOL\_INSUFFICIENT\_DATA | Sample or window too small | No | Caveat or alternate method |
| E\_TOOL\_RUNTIME | Exception in the sandbox | Once | Retry or degrade |
| E\_VERIFY\_FAILED | Checks failed | Yes | Re-plan |
| E\_BUDGET\_EXCEEDED | Tokens, time or steps used up | No | Partial answer |
| E\_MODEL\_ERROR | Provider failure | Yes | Fallback model |
| E\_DEPENDENCY\_DOWN | Database or tool down | Yes | Circuit break and degrade |
| E\_POLICY\_BLOCKED | PII, tenant or scope violation | No | Explain |

### 7.5 Causal tiering

| Tier | Source of the claim | Allowed wording |
| --- | --- | --- |
| A | Planted synthetic effect | "In this dataset, X caused Y by construction." |
| B | Quasi-experiment (before and after, difference-in-differences, synthetic control) | "Consistent with a causal effect of…" |
| C | Observational attribution (decomposition, correlation, tests) | "Associated with or contributing to…; this does not establish causation." |

The composer receives the tier and refuses stronger wording. This delivers the mentor's wish for causes rather than correlations without overclaiming on real data.

---

## 8. Conversation memory and context *(v7: shared MemoryService contract)*

- **State per session:** turns, active frame (metric, dimensions, filters, time range), last results (references only), unresolved clarification.
- **Rewrite, don't concatenate:** the ContextResolver sees the last 3 turns and outputs a standalone question. Downstream agents never see raw history.
- **Inheritance rules:** a new metric resets the frame; a new filter value replaces the old one on the same dimension ("what about Delhi?" replaces Mumbai); "why?", "and next quarter?" and "what if" keep metric, filters and time range.
- **Reset detection:** an unrelated topic or an explicit "new question" starts a fresh frame.
- **Storage:** Postgres/SQLite table keyed by session, plus the LangGraph checkpointer.

### 8.1 Context as code and the context pack

Context is a Git-tracked folder (Section 9.2) compiled into the database and vector index and stamped with a context version hash that appears in every trace and cache key. Each LLM call receives a deterministic context pack: sections with token budgets and provenance (semantics, schema slice, annotations, exemplars, learnings, history, profiles). When a pack is over budget, the lowest priority is trimmed first, in this order of keeping: semantics, schema slice, annotations, exemplars, learnings, history, profiles. Packs are cached by hash. Because every answer records the context version and the data snapshot, any answer can be reproduced and any regression traced to a context or data change.

### 8.2 Memory layers

| Layer | Contents | Retention |
| --- | --- | --- |
| Working | Current run state and step results | The run |
| Session | Resolved slots (authoritative), the last 3 turns verbatim, older turns summarized, result pointers | The session, 24 hours |
| Long term | User preferences (currency, default grain, favourite slices) and frequent questions | 90 days |

Resolved slots beat raw text, an explicit user statement beats an inherited value, and every answer stores a short summary for the next follow-up.

### 8.3 Learnings loop

SQL repairs, grounding misses and verifier failures become candidate learnings. A person approves each one as a pull request into the context repository, the index rebuilds, and the context version changes. Reliability improves without retraining, and the recurring-failure list is the best input for deciding what context to write next.

### 8.4 Shared MemoryService: implementation contract *(v7)*

**Decision:** all four product agents (Router, Planner, Clarification, Visualization) use one application-level `MemoryService` API. They do not open their own database connections or maintain private, conflicting memory stores. The service applies tenant/user/session scope, access policy, retention, provenance and audit rules consistently. LangGraph checkpoints remain responsible for durable workflow state and resuming a run; they complement rather than replace conversation and long-term memory.

**Storage profile:** use SQLite for local development and automated tests, and MySQL for the production application store if MySQL is the selected deployment database. Keep the implementation behind SQLAlchemy repositories and Alembic migrations; run integration tests against MySQL before release. The source customer warehouse is a separate connection and remains read-only. The architecture currently also describes PostgreSQL/pgvector in some deployment options: treat that as an alternative deployment profile, not as an implicit requirement alongside MySQL. Select one production relational store. The vector index is behind a `VectorMemoryIndex` interface and may use a compatible vector capability or a dedicated service such as Qdrant; do not assume SQLite or every MySQL version provides equivalent vector-search behavior. BM25/lexical search remains available as a fallback.

**Memory categories and canonical records:**

| Category | Store | Write rule | Retrieval rule |
| --- | --- | --- | --- |
| Working/run state | LangGraph checkpoint + run store | Persist each meaningful step transition and result reference | Only the active run reads it; used for recovery and step dependencies |
| Session/conversation | Relational `memory` tables | Store user/assistant messages, standalone-question rewrites, active frame and resolved slots; summarize older turns | ContextResolver retrieves current session context; normally pass the last 3 turns plus a bounded summary, not the entire transcript |
| User/tenant preferences | Relational `memory` tables | Save only explicit or confirmed preferences with provenance and timestamps | Apply only within the authorized tenant/user scope; explicit current instructions override stored preferences |
| Analysis and artifact references | Relational metadata and artifact store | Save IDs/URIs, run ID, data snapshot, model/method version and expiry; avoid duplicating large result sets | Retrieve only artifacts relevant to the current follow-up and re-check access/freshness before use |
| Semantic/document knowledge | Semantic registry + vector/lexical index | Index approved metric definitions, schema descriptions, synonyms and PDF chunks with source/page and version metadata | Retrieve by query relevance, selected database scope, permissions and current context version; retrieved text is untrusted evidence, not instructions |
| Reusable query examples/learnings | Versioned context repository plus retrieval index | Candidate from successful runs or repairs; require tests and human approval before promoting to shared examples | Retrieve only examples compatible with the current schema/context version; never blindly replay SQL against a changed schema |

**Logical relational schema:** define versioned, tenant-scoped tables such as `memory_sessions`, `memory_messages`, `memory_frames`, `memory_preferences`, `memory_summaries`, `memory_artifact_refs`, and `memory_audit_events`. Use stable IDs, timestamps, `tenant_id`, `user_id` where applicable, `session_id`, `source_run_id`, `context_version`, and `expires_at` fields as appropriate. Keep secrets, raw database credentials, unnecessary PII and full sensitive query results out of memory. Large files and generated artifacts belong in file/object storage; relational rows keep references and metadata.

**Service API (illustrative contracts):**

```python
class MemoryService(Protocol):
    async def load_context(self, scope: MemoryScope, question: str) -> MemoryContext: ...
    async def append_turn(self, scope: MemoryScope, turn: ConversationTurn) -> None: ...
    async def save_resolved_frame(self, scope: MemoryScope, frame: ResolvedFrame) -> None: ...
    async def save_artifact_ref(self, scope: MemoryScope, ref: ArtifactReference) -> None: ...
    async def search_knowledge(self, scope: MemoryScope, query: str, filters: RetrievalFilters) -> list[MemoryHit]: ...
    async def propose_learning(self, candidate: LearningCandidate) -> LearningReview: ...
    async def delete_user_memory(self, scope: MemoryScope) -> DeletionReceipt: ...
```

These are interface contracts, not a requirement to use this exact syntax. Every call must enforce authorization server-side; callers cannot supply an arbitrary tenant scope and thereby gain access. Memory retrieval returns typed records with source, confidence/relevance, version and timestamps so downstream agents can distinguish preference, conversation context, approved business definition and generated analysis.

**Runtime protocol:** (1) authenticate and establish tenant/user/session scope; (2) load the persisted run checkpoint and only relevant session memories; (3) resolve the latest question into a standalone question and explicit frame; (4) retrieve schema/business knowledge separately from conversational memory; (5) plan and execute using current authorized evidence; (6) verify outputs; (7) append the turn, save compact summaries and references to verified artifacts, and emit audit metadata. Do not save an unverified answer as a fact or automatically promote a SQL repair to a shared learning. The Clarification Agent stores unresolved slots and the user's answer; the Visualization Agent stores a chart specification and evidence/artifact references, not just a rendered image; the Router and Planner can read shared context but should write only their typed outputs.

**Conflict and precedence rules:** current explicit user statement > confirmed resolved slot for the active turn > scoped user preference > session summary > retrieved example. Schema/catalog and approved semantic definitions determine data validity; memory never overrides permissions, schema checks, or SQL validation. When memory is stale, contradictory or low-confidence, ask for clarification or ignore it and report the assumption rather than silently guessing.

**Retention, deletion and operations:** apply the Section 8.2 policy consistently (working state for the run; session memory for the session with 24-hour session retention; long-term preferences/frequent-question summaries for 90 days) unless a tenant policy sets a shorter period. Store creation/expiry timestamps and run scheduled cleanup. Provide user-scoped deletion across relational memory, summaries, vectorized memory chunks and cached references; emit a deletion audit event without retaining the deleted content. Use encryption in transit/at rest, least-privilege DB roles, parameterized queries, tenant filters, bounded result sizes and log redaction. Never place credentials or unrestricted PII in prompts, vector metadata or traces.

**Tests and metrics:** test cross-tenant isolation, current-turn precedence, session continuity, summarization, expiry, complete deletion, stale schema/example invalidation, retrieval relevance, checkpoint recovery and MySQL migration parity. Track memory retrieval hit/relevance, stale-memory use, context tokens per run, cross-session leakage (must be zero), write failures, deletion completion and latency. Memory retrieval is an optimization for continuity, not a substitute for grounding and verification.

---

## 9. Data and knowledge layer

### 9.1 Warehouse

Use SQLite for the supplied dataset and local development; SQLAlchemy plus sqlglot provide a consistent query/validation layer for supported customer connections such as PostgreSQL or MySQL when needed. The agent connects with a **strict read-only role**; row-level security and user identity pass through where the warehouse supports it. **Under no circumstances does the agent run DDL (`CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`), DML, or expand/modify tables in the user's database.** The user database is treated as an immutable source of truth; all agent-created artifacts, derived insight tables, curated views, and memory reside exclusively in the agent's own writable application store (Section 9.7).

### 9.2 Context layer (files in git, nao-style)

```text
context/
  databases/<table>/columns.md, preview.md, profiling.md
  docs/business_definitions.md, glossary.md
  semantics/metrics.yaml        # metric, grain, formula, synonyms, allowed dims
  semantics/drivers.yaml        # candidate drivers per metric (stockouts, footfall, promos, marketing)
  RULES.md                      # business rules and SQL conventions
  tests/*.yaml                  # question -> expected SQL/result
```

A vector index is built over column descriptions, synonyms and metric definitions for retrieval. `drivers.yaml` is what lets the Why engine know which tables can explain which metric.

**Schema retrieval and ranking *(v5)*:** use hybrid retrieval over table/column descriptions, aliases, DDL, metric definitions, constraints and join metadata. Retrieve candidates using lexical BM25 plus embedding similarity, fuse their ranks (for example reciprocal-rank fusion), then rerank a bounded candidate set with a cross-encoder or equivalent relevance scorer. Expand only valid primary/foreign-key join neighbours needed by the request. The final schema slice records why each table/column was selected and includes physical identifiers, descriptions, keys, grain, allowed dimensions and source references. The generator may use only this slice; if required identifiers or a valid join path are not found, the Answerability Gate clarifies or refuses before SQL generation. Retrieval scores and chosen thresholds are logged for evaluation.

### 9.3 Ingestion pipeline (add any table set without code changes)

1. Land raw files (Parquet or CSV) and introspect tables, keys and types.
2. Profile: nulls, cardinality, ranges, date coverage, sample values and PII detection.
3. Draft descriptions and synonyms with an LLM; a person approves them.
4. Register the catalog entry, the semantic metrics and dimensions, and the candidate drivers.
5. Embed the schema and documentation into the vector index.
6. Run data tests (keys, freshness, ranges) with dbt or Great Expectations.
7. Compute or refresh the insight tables.
8. Run the evaluation suites and block activation on regression.
9. Bump the data snapshot id and the context version.

Ingestion is done when adding tables is configuration plus approval, never a code change.

### 9.4 Insight store (precomputed intelligence, as the mentor suggested)

```sql
kpi_anomalies(kpi, dimension, dim_value, ts, type, value, expected, delta, score, method, run_id)
kpi_forecasts(kpi, dimension, dim_value, ts, yhat, lower, upper, method, backtest_mape, run_id)
kpi_drivers(kpi, period_a, period_b, driver, contribution, direction, p_value, run_id)
```

Batch jobs fill these inside the **agent's private application store** (never in the customer or user warehouse). The Planner checks the insight store first; a hit costs a single SQL against the agent store and answers fast. A miss falls back to on-the-fly tools, and the UI says a model is running. Store `run_id` and freshness so stale tables are flagged.

Further insight tables, all queried like base tables:

| Table | Contents | Serves |
| --- | --- | --- |
| kpi\_daily | kpi, date, dimension, value | Fast descriptive and trend answers |
| price\_elasticity | category, segment, elasticity, interval, sample size | What-if |
| segment\_profiles | segment, size, revenue share, order value, conversion, lifetime value, churn risk | Now-what |
| churn\_scores *(v4)* | customer, segment, churn probability, calibration bucket, model version, scored\_at, run\_id | Churn and at-risk segments |
| channel\_response\_curves | channel, spend, expected orders, marginal return | Optimization |
| causal\_effects\_ground\_truth | effect id, lever, scope, window, true effect, mechanism | Evaluation only; never visible to the agent |

### 9.5 Ready-to-use warehouse and causal analysis scenarios

The application connects directly to an existing, ready-to-use database (e.g. `ecommerce.sqlite` or any customer warehouse). **No schema expansion or synthetic table generation is performed on the user's database.** The schema and its relationships are discovered dynamically through catalog introspection.

For diagnostic ("Why"), predictive, and scenario analyses, the agent maps candidate drivers declared in `drivers.yaml` against the real operational and business factors already present in the warehouse (e.g., promotions, order delivery delays, freight, categories, payment types, regional variations, review scores, and customer repurchase history).

**Reference causal scenarios (for benchmark evaluation only).** The scenarios below define ground-truth causal benchmarks used in offline evaluation test sets to verify that the Why and Anomaly engines accurately recover drivers when present and correctly report "no significant driver" when absent (as in control periods), without needing to alter or expand the user's database:



| ID | Planted cause | Expected effect | Tests |
| --- | --- | --- | --- |
| S1 | Stockout in one category for one month | Revenue falls about 8% in that category and month | Why recall |
| S2 | Paid-search budget cut by 35% | Sessions fall 12% after a 5-day lag, then orders fall 7% | Multi-hop why |
| S3 | Price up 6% on one category | Units fall 11% (elasticity near -1.85) | What-if |
| S4 | Delivery delay of 4 days in one region | Review score falls 0.7, repeat orders fall 9% after 30 days | Lagged why |
| S5 | Black Friday promotion | Revenue up 40%, margin down 5 points, December cannibalization down 6% | So what and why |
| S6 | Competitor price cut of 10% in one category | Conversion falls 4% in that category | External driver |
| S7 | Control month with no planted cause | None | False-discovery test |
| S8 *(v4)* | Customers with 2 or more late deliveries in their first 3 orders churn at about 2.5 times the base rate in one region | Repeat purchase within 90 days falls for that group | Churn model and segment ranking |
| S9 *(v4)* | Weekly orders in one state fall about 30% for 3 weeks (fulfilment outage plus a paid-search cut) | A sharp regional dip with two lagged drivers | Anomaly detection, then why |
| S10 *(v4)* | A duplicated batch load doubles orders for 2 days in one region | A false spike caused by data quality | Anomaly detection must not report it as business demand (the data-quality check flags it) |

S7 matters most: a system that always finds a driver is worse than one that says there is no significant driver. For each scenario the simulator also writes a no-intervention twin series, so what-if evaluation has a numeric ground truth rather than an opinion.

### 9.6 Messy-warehouse hardening *(v4)*

A real warehouse has many tables, cryptic names, duplicated entities and dirty values. The design handles each one explicitly and tests it on a deliberately messy copy of the warehouse.

**The messy twin (optional test fixture).** `data/generator/messy.py` produces `warehouse_messy` as an isolated evaluation fixture for stress-testing grounding and entity resolution. The primary application connects directly to the user's ready-to-use database and never mutates or corrupts user tables:

| Corruption | Example |
| --- | --- |
| Cryptic names | `orders` becomes `t_ord_hdr`, `customer_id` becomes `c_id`, `order_purchase_timestamp` becomes `ts1` |
| Look-alike tables | `orders_archive`, `orders_v2_tmp`, a deprecated `customers_old` |
| Duplicated entities | The same customer appears 2 to 5 times with spelling, accent, email and address variants |
| Messy values | Mixed case and accents in city names, status codes (`dlvd`, `DELIVERED`), dates in two formats, `'N/A'` and `''` for null, currency stored as text, mixed units |
| Dead columns | Always-null or constant columns that tempt a generator |
| Wide tables | 60 or more columns on a few tables |

**Handling (applied at ingestion, Section 9.3, with a person approving)**

1. **Alias map.** Each cryptic table and column gets a business name, description and synonyms in the context layer. The LLM drafts them from profiling output and sample values; a person approves them; a test checks that every alias round-trips to exactly one physical column.
2. **Canonical clean views.** Ingestion creates `clean_*` views that trim, lowercase and de-accent text, parse dates, cast numerics, map status codes, and turn null-like strings into real nulls. The SQL agent's allow-list contains the clean views only; raw tables are visible to the profiler but not to the generator.
3. **Entity resolution.** Blocking on normalized keys, then pairwise scoring (name, email, address, phone similarity with a Fellegi-Sunter style model, or a rules-plus-threshold fallback) produce an `entity_map(raw_id, entity_id, confidence)`. Metrics that count customers use `COUNT(DISTINCT entity_id)`. Merges below the confidence threshold are listed for review, never applied silently.
4. **Value index.** For each low and medium cardinality text column, a value index (exact, trigram and BM25) lets the Grounder map "sao paulo" to the stored value. Retrieved values are untrusted data (Section 14). For high-cardinality values, perform a bounded, permission-aware lookup after the column is grounded rather than indexing every value into the prompt. When top candidates are too close or confidence is below threshold, ask the Clarification Agent instead of silently choosing.
5. **Value-linking evaluation *(v5)*.** Maintain a labelled set of canonical values and natural-language variants, including misspellings, accents, case changes, status aliases, null-like tokens and ambiguous matches. Measure top-1 accuracy, precision, recall, ambiguous-case clarification rate, and false-match rate separately. Include a regression case for every corrected production miss.
6. **Table disambiguation.** The catalog marks one table per concept as preferred and the others as archive, deprecated or duplicate. The Grounder prefers the marked table and the answer states which table was used.
7. **Data-quality caveats.** Profiling results (null rate, duplicate rate, coverage gaps) travel with the metric. The composer states relevant caveats, and the anomaly engine runs a data-quality screen (duplicate loads, gaps, sudden null spikes) before reporting a spike or dip as a business event (scenario S10).

**Tests:** Section 12 lists the messy-warehouse SQL slice, entity-resolution suite, alias round-trip test, value-linking suite, and the S10 data-quality case.

**External reference:** a 100-question slice of a public text-to-SQL benchmark (for example BIRD mini-dev, run in an isolated container) is reported as an outside check on SQL accuracy. It is reported, not gated, because the production target is the team's own warehouse.

### 9.7 Agent-owned store: where analysis tables, history and traces live *(v4)*

The customer's warehouse is read-only, so everything the agent creates goes into its own writable application/agent store through a separate connection and credentials. For the selected SQLite-to-MySQL profile, use SQLite locally and MySQL in production; PostgreSQL is an alternative deployment profile only if explicitly selected. Keep the store abstraction portable and test dialect-specific behavior with migrations and integration tests.

| Content | Location in the agent store | Notes |
| --- | --- | --- |
| Analysis tables (`kpi_anomalies`, `kpi_forecasts`, `kpi_drivers`, `churn_scores`, `kpi_daily`, `segment_profiles`, `price_elasticity`) | Schema `insights` | Filled by batch jobs that read the source warehouse and write here; each row carries `run_id`, `as_of` and the data snapshot id |
| Entity map, clean-view definitions, value index | Schema `curated` | Built at ingestion (Section 9.6) |
| Catalog, semantic layer and driver definitions (compiled from the git context files) | Schema `semantic` | The git files remain the source of truth |
| Vector index of schema text, column descriptions, synonyms and metric definitions | `VectorMemoryIndex` adapter (compatible database vector capability or dedicated vector service) | This is the RAG layer; it holds descriptions, not data rows; BM25/lexical fallback remains available |
| Sessions, conversation history, resolved slots, user preferences, summaries and artifact references | Schema/tables `memory_*` | Accessed only through `MemoryService`; retention, deletion and tenant isolation as in Sections 8.2 and 8.4 |
| Run traces, evidence records, evaluation results, cost and latency metrics | Schema `ops` | Feeds the run inspector and metrics page |

**How the planner finds an analysis table.** Each insight table is registered in the semantic layer with its description, grain, KPI and dimension coverage, `as_of` and a freshness limit. The planner checks this registry first. RAG only helps the Grounder retrieve the table's description and synonyms; the numbers always come from the table through a validated SQL query. For the SQL agent the `insights` and `curated` schemas are queried like base tables, and a separate read-only source connection or a controlled replicated copy is used when a step needs both. Do not use SQLite ATTACH in the application query path because ATTACH is prohibited by the SQL safety policy.

**Rules:** the agent role can write only to its own schemas; the source warehouse role stays read-only; the same AST guard applies to both; the user history stores no raw PII and is deletable per user.

---

## 10. Engines

### 10.1 SQL Agent

Retrieve and rank the schema slice and metric definitions, generate SQL, then parse with sqlglot (single SELECT only; reject DDL/DML), check every table/column against the retrieved schema and allow-list, run an `EXPLAIN` dry run, and execute with timeout and row cap. On failure, allow one initial generation plus at most 2 repair attempts (3 total SQL attempts); stop after the budget is exhausted and report the reason or a verified partial result. Return the executed SQL, validation/repair history, and DataFrame for transparency. Use the metric registry for known metrics so definitions stay consistent.

### 10.2 Analysis toolkit (deterministic, typed, unit-tested)

| Tool | Signature (core) | Method |
| --- | --- | --- |
| detect_anomalies | kpi, dims, period | Start with robust seasonal residuals / STL-ESD and robust z-scores; use Isolation Forest for suitable multivariate features and PELT for change-point detection when supported by enough ordered observations |
| driver_analysis | kpi, period_a, period_b, dim | Deterministic variance/mix decomposition first; optionally CatBoost for nonlinear predictive driver ranking and SHAP for model attribution; Double Machine Learning (Double ML) only for a well-defined treatment/outcome and defensible causal assumptions |
| significance_test | kpi, group_a, group_b | t-test, chi-square, bootstrap |
| impact_size | kpi, baseline | Delta vs baseline/target/peers in currency and % |
| forecast | kpi, dim, horizon, method=auto | Compare a seasonal-naive/ETS baseline with AutoARIMA and LightGBM when data volume/features justify them; retain Prophet if already suitable; rolling-origin backtest and prediction intervals where supported |
| scenario | kpi, change, elasticity | Log-log elasticity, Monte Carlo, sensitivity on key drivers |
| optimize | objective, constraints | scipy.optimize / LP |
| segment | entity, features | k-means, RFM |
| detect_data_quality *(v4)* | table, window | Duplicate-load, gap and null-spike screens that run before an anomaly is reported as a business event |
| churn_model *(v4)* | customer table, cutoff, horizon, segment dims | Time-based split, calibrated gradient boosting with a BG/NBD baseline, scores per customer |
| prioritize_segments *(v4)* | scores, value, drivers, constraints | Expected revenue at risk per segment with bootstrap intervals, ranked with an actionability weight |

Tool rules: pure functions, explicit units, always return `assumptions` and `confidence`, fail with typed errors, run in a worker with CPU/time limits. The LLM picks the tool and arguments but does not write analysis code in v1.

**Optional advanced-model candidates (evaluation-gated, not mandatory for every question).**

- **Anomaly/change intelligence:** use STL-ESD for seasonal univariate series, Isolation Forest for suitable multivariate feature sets, and PELT for change-point segmentation. Screen for missing periods, duplicate loads and other data-quality issues before interpreting an anomaly as a business event. Compare with a simple robust-z-score baseline.
- **Driver/model attribution:** CatBoost may rank nonlinear predictive drivers; use SHAP to explain the fitted model's predictions. These are predictive associations, not proof of causation. Double Machine Learning (Double ML) is considered only when a treatment, outcome, confounder set, sample size and identification assumptions can be stated and tested; otherwise return association/decomposition analysis and explicitly abstain from causal claims.
- **Forecasting:** compare AutoARIMA against seasonal-naive and ETS baselines; evaluate LightGBM when enough history and useful lag/calendar/exogenous features exist. Keep Prophet as an available existing option where appropriate. Select by rolling-origin backtests, horizon-specific error and interval coverage, not by model name. Do not run all models on every request.
- **Dependencies:** packages such as `ruptures` (PELT), `catboost`, `shap`, `doubleml`, `pmdarima` (AutoARIMA) and `lightgbm` are optional additions, not assumed installed. Inspect the environment, add a dependency only when implementing its feature, pin/document the version, and provide a simpler fallback if installation, compatibility, data sufficiency or runtime budgets prevent use.
- **Acceptance:** each model must have unit tests, a suitable baseline comparison, data-sufficiency checks, reproducible evaluation splits, and recorded latency/resource use. Add it only when it improves a relevant held-out metric without unacceptable cost/latency; otherwise keep the baseline. Never claim improved performance until measured results support the claim.

**Honesty on causality:** on real observational data the Why engine reports *associated drivers with contribution sizes*, not proven causes, and states the limits. In reference benchmark evaluations, ground-truth scenario ledgers let us verify that the ranked drivers match the true causes.

### 10.3 Engine playbook

**Why: funnel identity first, models second.** For e-commerce, revenue = sessions x conversion x average order value. Attribute the change between two periods by sequential (Shapley-style) decomposition, then rank segments by their mix and rate contributions, where w is a segment's share and r its rate:

```latex
\Delta R = \sum_i (w_i^1 - w_i^0)\, r_i^0 \;+\; \sum_i w_i^0\,(r_i^1 - r_i^0) \;+\; \text{interaction}
```

Then test each candidate driver for significance, interval and effect size, join the external drivers declared in drivers.yaml with lags (partial correlation; Granger tests only as a hint), and apply simple hypothesis rules (traffic down with conversion flat points to demand; conversion down with traffic flat points to price, stock or site). Output: ranked drivers, a waterfall chart and the causal tier.

**So what.** Choose the test by data type and sample size (t-test, Mann-Whitney, chi-square, proportion test) and report effect size, interval and power. Anomalies use STL residuals with a robust z-score (median absolute deviation, threshold 3.5) or seasonal-hybrid ESD, and Isolation Forest for multivariate cases. Impact is sized in currency and % against baseline or target.

**What next.** Prophet by default. Beyond the quick start's ds and y workflow, use a Brazilian holiday calendar, multiplicative seasonality for revenue and a tuned changepoint prior per series, and check the Prophet docs for the exact arguments when implementing. Backtest with rolling-origin cross-validation and gate on error and interval coverage. Prophet needs at least two seasonal cycles, and 2016 to 2018 data at monthly grain is only about 24 points, so forecast at daily or weekly grain and aggregate to month, or fall back to ETS. Fit per series for the top segments and allocate the long tail top-down. Never show a point forecast without its interval.

**Forecast to what-if bridge.** Promotions and marketing enter the forecast as extra regressors, so a scenario is a set of future regressor values. Price elasticity comes from log(Q) = a + b log(P) + controls, and a seeded Monte Carlo over the uncertainty of b (1,000 draws) gives P5, P50 and P95 revenue impact.

**Now what.** Fit concave response curves per channel, then maximize total response subject to budget and channel limits with scipy.optimize (SLSQP, or MILP when choices are discrete). Output ranked actions with expected lift, cost and risk, not one "optimal" number.

### 10.4 Churn and at-risk segments *(v4)*

This engine answers "which customer segments are we most likely to lose next quarter, and where should we act first?" It is a predictive module with a holdout check, and its wording stays honest: the model predicts risk; it does not prove why a customer leaves.

**Definition.** In a non-contractual setting, a customer has churned if they place no order in the horizon after the cutoff (default 90 days, defined once in `metrics.yaml` as `churned_90d`). Requirements: a resolved customer entity and repeat purchase history, otherwise the answerability gate refuses (Section 4.3).

**Data and leakage control.** Features are computed only from data at or before the cutoff: recency, frequency, monetary value, tenure, delivery delay, review score, support tickets, promotion exposure and category mix. Splits are by time (train at cutoff T-2, validate at T-1, test at T), never random, and the label window never overlaps feature windows.

**Models.** A probabilistic baseline (BG/NBD with Gamma-Gamma for value) and a calibrated gradient-boosting classifier. The model is chosen on validation, then reported once on test. Isotonic or Platt calibration is applied and checked.

**From customers to segments.** Segments come from the semantic layer (region, acquisition channel, RFM tier, category). For each segment: mean predicted churn probability, expected revenue at risk (probability times predicted value), and a bootstrap interval. The "where to act first" ranking is

```text
priority = expected_revenue_at_risk x actionability_weight
```

where the actionability weight comes from the share of risk attributable to controllable features (for example delivery delay, found with permutation importance or SHAP on the model). The output shows the ranking, the interval, the top contributing features and the sample size.

**Honesty rules.** The answer labels the ranking as predicted risk. Drivers shown are model attributions (causal tier C). Recommended actions are framed as hypotheses to test, for example a pilot with a holdout group; uplift modelling is a SEAM, not a v1 claim.

**Gates (checked on the holdout and on scenario S8):**

| Metric | Gate |
| --- | --- |
| AUC-PR versus a recency-only heuristic | At least 0.05 absolute gain |
| Calibration (expected calibration error) | At most 0.05 |
| Lift in the top decile | At least 2.0 |
| Segment ranking against ground-truth churn (Spearman) | At least 0.70 |
| Ranking stability across 100 bootstrap resamples | Top-3 segments overlap at least 0.8 |
| Planted segment (S8) in the top 3 | Yes |

The batch job writes `churn_scores` to the insight store (fast path). A custom slice runs the model on the fly (flex path).

---

## 11. Visualization *(v6: Nao-inspired reusable experience)*

Chart specs are typed JSON and rendered by a shared React chart renderer. The Visualization Agent receives only verified/finalized step-result artifacts, never unverified intermediate results. **Reuse the patterns documented in `Nao_Visualization_Code_Reuse_Guide_for_Data_Scientist_Agent.md`; do not copy the whole Nao application or make the architecture dependent on its private internals.** Confirm repository license, version compatibility, and attribution before copying any source code. Prefer reimplementing the behavior behind our own schema if reuse rights or dependencies are unclear.

### 11.1 Answer presentation contract

A result may contain: insight headline; concise answer; KPI cards; chart/table; method and "Analysis used"; assumptions and limitations; data-as-of timestamp; evidence/step references; expandable SQL and result data; and follow-up questions. The UI offers **Chart / Data / SQL** inspection when the run has the relevant artifacts. CSV export is allowed only for result data the user is authorized to see. An Executive Story view can assemble narrative, KPIs, charts, evidence tables, filters, method, assumptions, confidence and freshness into a shareable report, subject to access controls.

### 11.2 Typed chart contract and renderer

Use a versioned schema (Pydantic on the backend; matching TypeScript/Zod validation in the frontend) with fields such as `chart_type`, `title`, `subtitle`, `x`, `series`, `data_ref`, `source_step_ids`, `units`, `format`, `annotations`, `filters`, `alt_text`, and optional `editable_config`. The spec references verified artifacts instead of duplicating large result sets. Validate data types, field existence, units, row limits, and series compatibility before rendering. Invalid specs fall back to a table/text answer and produce a traceable chart error; chart failure never invalidates an otherwise verified answer.

Chart selection is rule-first: intent, result shape, data types, units, cardinality and sample size determine allowed chart candidates. The LLM may choose from those candidates and write a short title/annotation, but must not invent fields or produce unconstrained executable visualization code. A user chart-edit action is validated against the same schema and data artifact. Use the chosen library consistently (initial frontend recommendation: Plotly.js for richer analytical interactions; Recharts patterns from Nao may be reimplemented if simpler and dependency/licensing fit is better). Do not maintain two competing renderers without a documented reason.

| Result shape / task | Preferred visual |
| --- | --- |
| Time series | Line; forecast adds prediction interval and separates historical from predicted values |
| Anomaly detection | Actual versus expected with clearly marked outliers and threshold/baseline |
| Category comparison | Sorted bar, top N with remainder aggregation where appropriate |
| Root-cause / variance decomposition | Ranked driver contributions or waterfall, with association/cause tier stated |
| Scenario / what-if | Baseline versus scenario, interval or tornado sensitivity where supported |
| Forecast | Historical + forecast + prediction interval; optional trend/seasonality panels |
| Churn | Risk-ranked segments, calibration/quality summary, sample size and expected value at risk |
| Segment analysis | Scatter or grouped bars only when supported by sample size and variables |

### 11.3 Chart controls and trust

Provide clear labels and units, informative tooltips, date filters, series toggles, chart/data/SQL tabs, and CSV/Excel export when authorized. Filters must trigger a new governed query or a documented safe slice of the verified artifact; never silently filter only the visual while implying the underlying analysis changed. Keep colour-blind-safe palettes, accessible contrast, alt text, a meaningful insight title, source-step references, data freshness, sample sizes, and uncertainty visible. Causal claims must follow the causal tier in Section 7.5. A table is always available as fallback.

### 11.4 Implementation order

1. Versioned chart schema and contract tests.
2. Shared chart renderer plus table fallback.
3. Chart / Data / SQL inspection and safe exports.
4. KPI cards and anomaly/root-cause/forecast/churn/what-if chart templates.
5. Executive Story/report composition and validated chart editing.
6. Visual regression/accessibility tests and chart-specific evaluation.

Source-of-truth implementation details and suggested examples live in the companion Nao guide. Keep the guide in `docs/` and update it when chart contracts or dependencies change.

---

## 12. Evaluation and observability

**Test sets (per track, owned by that track)**

| Suite | Size to start | Metric | Gate |
| --- | --- | --- | --- |
| Intent routing | 200 labelled, including the "spikes across all months" case | Macro-F1, confusion matrix, calibration | F1 ≥ 0.85, no class below 0.7, zero dead ends |
| Context resolution | 50 multi-turn dialogues | Slot accuracy | ≥ 0.90 |
| Clarification | 60 (30 should ask, 30 should not) | Precision, recall, option validity | ≥ 0.85 each; options 100% valid |
| SQL | 80 gold queries | Execution equivalence (result sets match) | ≥ 0.85 |
| Schema retrieval and ranking *(v5)* | At least 200 labelled questions spanning simple, ambiguous, multi-table and distractor-heavy schemas | Required-table Recall@10, column recall, MRR/nDCG, join-path accuracy, retrieval p50/p95 and cost | Initial gates: Recall@10 ≥ 0.90, MRR ≥ 0.80, join-path accuracy ≥ 0.90; calibrate on the labelled set and report by schema size |
| Value linking *(v5)* | At least 200 labelled value mentions, including accents, typos, aliases, null-like values and ambiguous candidates | Top-1 accuracy, precision/recall, false-match rate, clarification accuracy | Initial gates: precision ≥ 0.95 and recall ≥ 0.90; ambiguous cases must clarify instead of silently misbinding |
| Planner Agent *(v5)* | 50 compound questions and failure/fallback cases | Sub-question coverage, DAG validity, dependency correctness, parallelisation, fallback validity, plan-budget compliance | 100% of sub-questions mapped to a step; no cycles; all plans ≤ 8 steps and include a fallback |
| SQL safety | 30 adversarial prompts | Unsafe-statement rejection | 100% |
| Why | 7 planted scenarios | Planted-driver recall at 3; false discovery on the control month | Recall ≥ 0.80; false discovery ≤ 0.15 |
| So what | 30 questions | Test correctness, effect-size error | ≥ 0.85 correct |
| Forecast | 12 series | Error against a seasonal-naive baseline; interval coverage | Beats baseline; coverage 0.85 to 0.98 |
| What-if | 6 scenarios | Elasticity error against ground truth | ≤ 25% |
| Now what | 6 scenarios | Constraint satisfaction, lift against baseline | 100% feasible |
| Chart | 100 result shapes | Valid spec, renders, appropriate | ≥ 98% render; ≥ 85% appropriate |
| End to end | 40 conversations | Groundedness, numeric fidelity, follow-up continuity, latency, cost | Fidelity ≥ 98%; continuity ≥ 0.90 |
| Answerability and refusal *(v4)* | 120 (60 unanswerable, 60 answerable near-misses) | Refusal recall and precision, over-refusal, hallucinated identifiers reaching execution, quality of alternatives offered | Recall at least 0.95, precision at least 0.90, over-refusal at most 0.05, hallucinated identifiers reaching execution 0 |
| Messy-warehouse SQL *(v4)* | 50 on the messy twin | Execution equivalence, wrong-table rate, deduplicated-count accuracy | At least 0.75; dedup counts exact at least 0.90; wrong-table at most 0.05 |
| Enterprise scaling *(v5)* | Frozen workload at 20, 200, and 1,000+ tables; large-row-count and concurrency variants | Recall/grounding quality by schema size, SQL execution accuracy, p50/p95 latency, tokens/cost, memory, timeout/error rate | No material retrieval-quality regression as distractors grow; publish all size/load results and define service limits before release |
| Entity resolution *(v4)* | 200 labelled pairs | Pairwise precision and recall | At least 0.95 and 0.90 |
| Anomaly detection *(v4)* | 40 series with planted dips and spikes plus 10 clean series, plus S9 and S10 | Precision, recall, detection delay, false alarms on clean series, data-quality screen | F1 at least 0.80; false alarms at most 0.1 per clean series; S10 not reported as demand |
| Churn *(v4)* | Holdout window plus S8 | Metrics and gates in Section 10.4 | As listed there |
| Causal wording *(v4)* | Every narrative in the why, anomaly and churn suites | A lint that rejects causal verbs ("caused", "driven by", "due to") unless the tier allows them | 0 violations |
| Public benchmark slice *(v4)* | 100 questions (for example BIRD mini-dev) | Execution accuracy | Reported, not gated |
| Baseline comparison *(v4)* | All suites above | The same metrics for B0 and B1 (Section 12.2) | System beats B0 on every gated accuracy metric; trade-off table committed per tag |

A baseline (single prompt over the schema, no planner, no tools) is run on the same sets so improvement is measurable. A CI job runs the suites on every context or prompt change and reports success %, flaky % (nao-style "always" pass rate), cost and time. Regressions block merge.

**Online:** trace every step (inputs, outputs, SQL, tool args, latency, tokens), keep chat replay, collect thumbs feedback, and produce a periodic context-recommendation report (frequent failures mapped to missing definitions or synonyms).

Judging is hybrid: deterministic checks wherever possible, an LLM judge with a rubric where not, and a human-checked sample for each release. Thresholds live in CI and a regression blocks the release tag.

**Reproducibility.** Every answer stores the context version, data snapshot id, model and prompt versions, seeds, SQL text, step result ids and the plan, so a run can be replayed and compared result for result. Online we also track routing accuracy on a labelled sample, clarification acceptance, SQL repair rate, verifier failure rate, thumbs feedback, service-target burn, data freshness and drift in KPI distributions.

### 12.1 Observability view *(v4; extended in v5)*

The metrics page is served by the application at `/metrics-ui` and is public next to the chat. It reads from the trace store and from the committed evaluation results, so it shows the running system and every prototype side by side.

| Panel | Contents |
| --- | --- |
| Accuracy (eval) | Router F1/calibration, schema Recall@K and MRR/nDCG, column and join-path grounding accuracy, value-link precision/recall, SQL execution accuracy, hallucinated-identifier rate, refusal recall/precision, anomaly F1, planted-driver recall at 3, false discovery on the control month, forecast error/coverage, churn AUC-PR/calibration, planner DAG validity, and numeric fidelity. Shown per tag, with gate lines and schema-size slices. |
| Accuracy (live) | Routing accuracy on the labelled sample, schema/value grounding confidence and misses, SQL repair rate, verifier failure rate, refusal rate, clarification rate, chart fallback rate, thumbs feedback. |
| Latency | p50 and p95 per stage and per path (retrieval, fast, generated SQL, flex, refusal); queue wait; timeouts; schema-size and row-volume slices. |
| Cost | Tokens and currency per answer, by intent, by model tier and by stage; cache hit rate; daily spend against the cap. |
| Baseline versus system | The Section 12.2 table for the selected tag, with the Pareto chart (accuracy against cost and latency). |
| Data health | Insight-table freshness, data-quality screen results, drift in KPI distributions. |
| Run inspector | Search by run id: the context resolved, intent and confidence, grounded identifiers, answerability outcome, plan DAG, each SQL with its validation and repair history, each tool call with parameters, method and seed, evidence records, verifier checks, narrative claims linked to evidence, cost and timings, and prompt and context versions. |

Every metric on the page has a definition, a data source and an owner in `docs/metrics.md`. Spans follow OpenTelemetry conventions, so a Grafana board can be added without changing the code.

### 12.2 Naive baseline and deliberate trade-offs *(v4; clarified in v5)*

**Baselines (same questions, same data, same judge):**

| Id | Description |
| --- | --- |
| B0 naive | A frozen prompt and deterministic schema-inclusion/truncation rule; one LLM call to write SQL, run it with no validation or repair, then ask the LLM to explain the result table. No routing, analysis tools, or refusal path. Freeze model/version, prompt, temperature, schema ordering/truncation, data snapshot, test questions and judge for repeatability. |
| B1 naive plus retry | Frozen B0 plus one execution-error retry, with every other setting held constant. This separates the gain from "just retry" from the gain of grounding, routing and tools. |
| System | The tagged version under test. |

For B0/B1, an unanswerable test case is scored as a non-refusal/incorrect answer if the baseline does not abstain; refusal recall is therefore 0 for those cases, not `N/A`. Also measure hallucinated identifiers and whether unsupported claims are produced. Do not hide a baseline limitation by omitting the refusal slice. The system and baselines use the same frozen question set, data snapshot, timing boundary, cost accounting, and scoring code.

**Comparison table (generated per tag into `evals/results/<tag>.json` and shown on the metrics page; values come from the runs, none are fixed here):**

| Variant | Schema retrieval/grounding | SQL execution accuracy | Hallucinated identifiers | Refusal recall/precision | DS correctness (anomaly F1, driver recall, churn AUC-PR) | Numeric fidelity | Latency p50 / p95 | Cost per answer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | measured where applicable; full-schema/truncation policy recorded | measured | measured | no refusal path: recall scored as 0 on unanswerable cases | measured (LLM explanation baseline) | measured | measured | measured |
| B1 | measured where applicable; same B0 policy | measured | measured | no refusal path: recall scored as 0 on unanswerable cases | measured | measured | measured | measured |
| System | measured | measured | measured | measured | measured | measured | measured | measured |

**Trade-off policy (decided from the table, written down in a decision record per release):**

- A change that adds latency is accepted only if it buys an agreed gain on a gated accuracy metric. The default rule is at least 5 points of gain per added 2 s at p50; the rule is a team decision and may be changed in the record.
- The cost ceiling per answer is a multiple of B0's measured median cost (target: at most 3 times), recovered through model tiering (small models for classification, rewrite, grounding and repair), precomputation, caching and refusing early before any large-model call.
- Where accuracy is not negotiable (identifier validity, refusal, causal wording), no latency or cost saving may lower it.
- Each tag's decision record states which trade-offs were taken and shows the Pareto chart that supports them.

---

## 13. UX and streaming *(v6)*

The event contract is defined in Section 6.2. The UI renders the timeline one to one: resolving context, selecting an intent, grounding tables/metrics, checking answerability, planning, running tools, verifying evidence, preparing a chart, and composing the answer. The user sees concise **decision summaries** and evidence-backed reasons for major choices, plus SQL/assumptions and the run inspector when authorized. This feature may be called “thought streaming” in the UI/product brief, but technically it is **safe progress and rationale-summary streaming**, not disclosure of hidden chain-of-thought.

The UI includes:
- A persistent run timeline with active step, elapsed time, retries, tool status, and errors; show a percentage only when the worker can measure it.
- Brief status messages such as “Checking whether the warehouse contains the requested metric” and “Comparing the last four weeks with the prior period.”
- Short rationale summaries with evidence references, assumptions, and confidence where meaningful; never raw private scratchpad reasoning.
- A visible “model is running; this analysis may take longer” state for on-the-fly ML, with cancellation when safe and supported.
- Clickable clarification options; expandable validated SQL, returned data, method, limitations and assumptions.
- A result layout with headline, KPIs, chart/table, “Analysis used,” observed pattern versus possible causes, “What was not assessed,” data-as-of stamp, and run-inspector link.
- Reconnect/resume after network interruption using persisted event IDs; clear queued/running/completed/failed/cancelled states.

Stream only sanitized, user-authorized data. Never expose system/developer prompts, API keys, internal chain-of-thought, hidden agent scratchpads, cross-tenant information, or unredacted PII. The final answer can stream incrementally after evidence verification; intermediate progress events should not be represented as conclusions. Refusals use the same layout: reason, missing information, and alternatives.

---

## 14. Security and reliability

- **Database:** read-only role, allow-listed schemas, statement timeout and row limits. The AST guard rejects DDL, DML, COPY and ATTACH, EXPLAIN runs before execution, and a cost guard blocks cross joins.
- **Python sandbox:** a container with no network, a read-only filesystem, CPU, memory and time caps, an import allow-list and fixed seeds, with output only as step results. LLM-written code is never executed in the API process, and in v1 the LLM does not write analysis code at all.
- **Prompt injection:** values retrieved from the database are untrusted data, delimited and never treated as instructions. Tool arguments are schema-validated, tools cannot be created dynamically, and the SQL allow-list is the real boundary.
- **PII:** columns are tagged in the catalog and masked in logs, traces and sample values; no PII reaches prompts unless the use case needs it.
- **Tenancy:** the tenant id selects allowed tables and metrics and injects row policies through the semantic layer; quotas and model keys are per tenant. User identity passes through to the warehouse's row-level security where it is supported.
- **Audit:** who asked what, which SQL ran, which step results were read and which model answered.
- **Secrets:** vault or environment only, never in prompts or traces. *(v4)* The repository holds `.env.example` with placeholder keys only; a pre-commit hook and a CI job run a secret scanner (for example gitleaks) and fail on any hit; deployment keys live in the hosting platform's secret store; trace and log redaction masks keys and tokens.

### 14.1 Reliability, performance and cost

| Concern | Mechanism |
| --- | --- |
| Timeouts | Per stage and per tool; hard run cap of 90 s |
| Retries | Exponential backoff with jitter; steps are idempotent |
| Circuit breakers | Per tool and per model provider |
| Durability | Checkpoints; a crashed run resumes where it stopped |
| Consistency | One data snapshot id per run; every step reads the same snapshot |
| Determinism | Temperature 0 for classification, fixed seeds, recorded step results |
| Caching | Key = hash of the standalone question, slots, tool parameters, context version, data snapshot id, and model and prompt versions |
| Cost | Model routing and token budgets per stage; precomputation amortizes repeated analysis |

| Task | Model class | Why |
| --- | --- | --- |
| Context rewrite, intent, entities, chart titles | Small and fast | High volume, structured output |
| Grounding disambiguation, SQL repair | Small | Constrained candidate list or narrow fix |
| Planning, SQL generation, composition | Strong | Reasoning and code |
| Verification narrative | Strong, optional | Only when deterministic checks are inconclusive |

Service targets for the demo: fast path p50 ≤ 2.5 s and p95 ≤ 5 s; flex path p50 ≤ 12 s and p95 ≤ 45 s; error rate under 2%; 100% unsafe-SQL rejection on the adversarial set; numeric fidelity ≥ 98%; clarification rate 10 to 20%; cache hit rate ≥ 25% on repeated questions.

---

## 15. Technology choices

The following is the selected stack for the current local development build. Optional production technologies described elsewhere are not required for this phase.

| Concern | Selected technology / rule |
| --- | --- |
| Language and API | Python + FastAPI |
| Workflow orchestration | LangGraph with checkpointed state; no custom state machine unless an incompatibility is documented and approved |
| Contracts | Pydantic v2; JSON Schema export; versioned typed event envelopes |
| Frontend | Next.js App Router + React + TypeScript; Tailwind CSS + shadcn/ui; TanStack Query; Zod for validating event/chart contracts |
| Charts | Plotly.js with versioned chart specification and validated table/text fallback |
| Streaming | FastAPI + Server-Sent Events (SSE); persist run events and test reconnect/resume behavior |
| Business dataset | Supplied `ecommerce.sqlite`, accessed read-only; never migrate, modify, regenerate, or silently replace it |
| Agent/application store | Separate writable SQLite database for local development; SQLAlchemy repositories; Alembic migrations only for this agent-owned store |
| SQL safety | sqlglot, schema allowlists, parameterized values, read-only execution, bounded query/result sizes, SQLite-compatible query-plan checks |
| Retrieval | BM25 + embeddings behind a replaceable interface; reciprocal-rank fusion (RRF); local vector index/test adapter; BM25 fallback; foreign-key graph expansion and value linking |
| Embeddings/vector index | Provider/model and local index implementation must be selected and documented before implementation; do not pretend an unconfigured provider exists; no hosted vector service required for local development |
| Analysis | pandas, statsmodels, scikit-learn, SciPy, Prophet; ETS or naïve forecast fallback for short/sparse history |
| LLM integration | Provider-agnostic wrapper; explicit model configuration, structured outputs, timeouts, bounded retries, and token/cost budgets |
| Testing and evaluation | pytest + version-controlled YAML evaluation cases; frontend tests and end-to-end question-to-answer tests |
| Observability | Structured application logs, persisted run/step traces, evidence references, latency/cost metadata, and a local run-inspection view |
| Queue | In-process queue only for current development; no Redis, Redis Streams, SQS, or other external queue dependency |
| Application configuration | Typed settings, environment variables, `.env.example` with placeholders only; no secrets in source control |
| Development runtime | Run API and frontend directly in the local development environment; no Docker or deployment setup is required for this phase |

**Explicit exclusions for the current coding task:** Redis, Redis-backed cache/checkpointer/queue, Docker/Compose, Kubernetes, cloud queues, public hosting, managed databases, hosted vector services, and production monitoring infrastructure. Reconsider an excluded technology only after a measured requirement appears and the user approves an architecture change.

### 15.1 Repository layout

```text
data-scientist-agent/
  apps/
    api/            FastAPI, SSE, auth, run/setup-job status
    web/            Next.js App Router, TypeScript, Tailwind/shadcn, chat, timeline, Chart/Data/SQL, stories
  packages/
    contracts/      Pydantic schemas, event envelopes, chart specs, errors, versions
    ui-contracts/   Shared TypeScript/Zod event and chart-spec types
    orchestrator/   Graph, state, checkpoints, budgets
    agents/         context_resolver, intent, grounder, clarifier, planner,
                    sql_agent, verifier, viz, composer, memory
    tools/          Analysis library and sandbox runner
    semantic/       Loader, matcher, join graph, insight index
    insight/        Precompute jobs
    onboarding/     Async setup jobs: schema, semantic layer, docs, indexes, readiness
    eval/           Golden sets, harness, judges, CI gates
  context/          Git-tracked context (Sections 8.1 and 9.2)
  data/
    warehouse/      Read-only user database (e.g., ecommerce.sqlite)
    ground_truth/   Evaluation scenarios, benchmarks, reference ledgers
  infra/            Docker, migrations, tracing, manifests
  docs/             Decision records, runbooks, metrics definitions, Nao visualization reuse guide
  prompts/          Prompt pack: versioned files, one per prompt (Section 21)          (v4)
  evals/
    sets/           Evaluation sets (YAML and JSONL), including refusal and messy slices (v4)
    results/        Committed results per tag: v0.1.json ... v1.0.json                  (v4)
  .agent/           Coding-agent setup: rules, spec, subagents, hooks, commands (Section 22) (v4)
  README.md         Setup and run from scratch (Section 19.3)                           (v4)
  APPROACH.md       Approach (the submission view of this document)                      (v4)
  ARTEFACT.md       What was built, how to use and inspect it, results, links           (v4)
  diagrams/         Source (draw.io or Mermaid) and exported images                      (v4)
  .env.example      Placeholder configuration only; no secrets                           (v4)
```

### 15.2 Decision records to write first

1. LangGraph or Temporal for orchestration.
2. SQLite for the supplied demo dataset; choose a separate production customer-warehouse connector only when required.
3. Custom semantic layer or dbt and MetricFlow.
4. Prophet, ETS or a gradient-boosted model, chosen by series length.
5. Sandbox technology.
6. Context storage format and compiler.
7. Chart library (Vega-Lite or Plotly).
8. Evaluation judge policy.
9. Answerability thresholds and refusal operating point *(v4)*.
10. Entity-resolution method and merge threshold *(v4)*.
11. Churn model choice and cutoff or horizon definition *(v4)*.
12. Baseline definitions and the accuracy, latency and cost trade-off rule *(v4)*.
13. Hosting platform and public-deployment cost caps *(v4)*.

---

## 16. Work breakdown and milestones

Four tracks fit a four-person team; each owns its contracts, tests and demo slice.

| Track | Owns |
| --- | --- |
| A. Frontend/UX | Chat UI, SSE timeline, chart renderer, clarification buttons, follow-ups |
| B. Core backend | Orchestrator, ContextResolver, IntentExtractor, Grounder, Clarifier, Planner, Verifier, Composer |
| C. Data and knowledge | Ingestion & introspection pipeline, context layer, semantic/metric registry, retrieval, SQL agent, schema readiness, insight-store jobs |
| D. Analysis and recommendation | Analysis toolkit, Visualizer rules, eval harness for Why/So what/Forecast/Scenario/Prescriptive |

**Milestones (no dates, exit criteria only)**

| Phase | Work | Exit gate |
| --- | --- | --- |
| P0 Contracts and skeleton | Taxonomy; envelope, error, step-result and answer contracts; repository layout; graph with stub agents; evaluation harness and router test set | Schemas merged; a stub end-to-end run streams events; the router suite runs (failing is expected) |
| P1 Conversation core | Router rewrite with abstain path; context resolver; session memory; clarifier | Multi-turn ≥ 0.90; zero dead ends on 200 questions; clarifier precision and recall ≥ 0.85 |
| P2 Data and semantics | Ready-to-use database introspection; semantic layer; catalog; first insight tables in agent store (daily KPIs, anomalies, forecasts) | Database introspects cleanly without modifying source tables; "spikes across all months" answered from the insight store at p50 ≤ 2.5 s |
| P3 Science and planning | Analysis toolkit; sandbox; planner; verifier; SQL agent hardening | Why recall at 3 ≥ 0.80; false discovery ≤ 0.15; forecast gates; SQL execution accuracy ≥ 0.85 |
| P4 Experience | Visualization agent; step timeline; clarification chips; assumptions and confidence panel; composer with citations and fidelity check | Chart render ≥ 98%; end-to-end flow with charts; every answer shows assumptions and confidence |
| P5 Integration and hardening | What-if and now-what; fast and flex routing; caching; degradation matrix; full evaluation run; demo rehearsal; decision records and README | All CI gates green; service targets met; demo runs twice without intervention |

**Cut line if time is short.** The mentor's guess is about one more week, to be confirmed. Must: contracts, explicit Router/Planner/Clarification/Visualization Agent contracts, router fix, context resolver, clarifier, **answerability gate with the refusal suite**, why and anomaly engines, a basic forecast, **a basic churn module with its holdout check**, suitable charts with table fallback, the step timeline, ready-to-use database with insight tables, reference evaluation scenarios S1 to S3 and S7 to S10, the verifier and CI gates, **schema-retrieval/value-linking suites and scaling benchmarks**, **alias map, clean views, value index and a basic entity map**, **B0 and B1 baselines with the per-tag comparison table**, **the metrics page and run inspector**, **a public deployment with the README, prompt pack and agent setup**, and synchronized architecture diagrams. Should: what-if, now-what optimiser, the learnings loop, caching, model routing, and S4 to S6. Could: chat-platform delivery, dashboards, difference-in-differences (tier B), proactive monitoring, the public benchmark slice. Anything cut stays behind the same interfaces, so it can land later without a redesign.

### 16.1 Prototype tags and per-tag evaluation *(v4)*

Every prototype is a git tag. A tag is created by CI only when its evaluation results are committed and no gate that applies to it has regressed. The phases above (P0 to P5) are the work; the tags are the releases.

| Tag | What it adds | Evaluation committed with the tag |
| --- | --- | --- |
| `v0.1` | First end-to-end slice: question in, naive B0 pipeline, answer out, deployed skeleton, trace store, eval harness | B0 baseline numbers on the first suites; the comparison table starts here |
| `v0.2` | Schema retrieval, SQL guard (sqlglot, allow-list, EXPLAIN), execution validation and repair, answerability gate and refusal | SQL accuracy, hallucinated identifiers, refusal suite |
| `v0.3` | Router with visible analysis choice, semantic layer and metric registry, fast-path lookup | Router F1, calibration, fast-path latency |
| `v0.4` | Anomaly detection, data-quality screen, so-what tests, insight store jobs | Anomaly suite, S9 and S10 |
| `v0.5` | Root-cause engine, drivers, causal tiers, composer wording rules, control-month test | Planted-driver recall, false discovery, causal wording lint |
| `v0.6` | Forecast and churn modules, segment prioritisation | Forecast gates, churn gates, S8 |
| `v0.7` | Context resolver, clarifier, planner and DAG execution, compound questions | Multi-turn, clarification and plan-validity suites |
| `v0.8` | Messy twin, alias map, clean views, entity resolution, value index | Messy SQL slice, entity resolution suite |
| `v0.9` | Visualization, observability page and run inspector, caching, real-time hardening | Chart suite, latency and cost panels, load test |
| `v1.0` | Final: all gates green, deployed at the public URL, README, APPROACH.md, ARTEFACT.md | Full run: every suite, baseline comparison, trade-off decision record |

Every tag's `CHANGELOG` entry lists what changed, which suites ran, the comparison against the previous tag and against B0, and any gate that was waived with the reason. The tags are also the story of how the system grew.

---

## 17. Risks and open decisions

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Deadline shorter than the build | Partial demo | Cut line; stubs behind stable interfaces |
| Causal overclaim on real data | Credibility loss | Tiered wording enforced by the composer; control-month test |
| Data effects unmeasured or ambiguous | Weak insights | Grounding on real warehouse signals, robust driver decomposition, honest refusal |
| On-the-fly model latency | Poor experience | Fast path for common KPIs; streaming with an elapsed timer |
| LLM non-determinism or invented numbers | Wrong answers | Temperature 0, structured output, deterministic checks, fidelity gate |
| Router regressions | Dead ends | 200-question set in CI; abstain to clarify |
| Sandbox escape | Security incident | Container isolation, no network, import allow-list |
| Evaluation effort underestimated | No regression safety | The harness is built in P0, not at the end |
| Context drift | Silent quality loss | Context version in traces; regression run on every context change |
| Prophet on short or sparse series | Poor forecasts | Method auto-select, daily or weekly grain, ETS fallback, state the method used |
| Integration late and painful | Rework | Contracts and stub agents in P0; integrate continuously |
| Over-refusal makes the agent useless | Answerable questions get refused | Near-miss suite, a tuned operating point, alternatives offered, over-refusal gate |
| Entity resolution merges different people | Wrong customer counts | Confidence threshold, review list, pairwise precision gate, no silent merges |
| Churn model leaks future data | Inflated accuracy, wrong segments | Time-based split, feature cutoffs, leakage test in the pipeline |
| Public deployment abuse or runaway cost | Outage or bill | Rate limits, per-session and daily caps, read-only data, admission control |
| Real-time stream drops or stalls | Users see a frozen page | Heartbeats, resumable event ids, per-stage timeouts, degraded-mode messages |
| Baseline built too weakly | Flattering comparison | B0 and B1 defined in Section 12.2 and frozen; the baseline gets the same data and model access |
| Prompt changes silently lower quality | Regression | Prompt version in traces, evaluation on every prompt change, merge blocked on regression |

**Open decisions:** the confirmed submission date; which warehouse and LLM providers are available (this decides the adapters and cost routing); single-tenant demo or multi-tenant requirement; whether chat-platform delivery (Slack or Teams) is in scope; whether dashboards (saved views) are in scope or chat only; how much PII realism the synthetic set may carry.

### 17.1 Anti-patterns we reject

- Agents chatting freely with each other (unbounded cost, untestable).
- The full schema in the prompt.
- LLM-written Python executed in the API process.
- A point forecast shown as certainty.
- Correlation called "the cause" on observational data.
- Charts without units on the axis or an insight in the title.
- Clearing the conversation instead of resolving references.
- Any route that ends in "not enabled".

---

## 18. Demo script

1. "What data do you have?" A catalog answer with sample questions and no SQL.
2. "Why did revenue drop in March 2018?" Funnel decomposition, ranked drivers, a waterfall chart, confidence and the causal tier; the planted stockout is found.
3. "What about São Paulo?" Inherits metric, period and grain, which shows context retention in one step.
4. "Is that dip significant, and what did it cost?" A verdict with the impact in currency.
5. "How does revenue trend today, and what will it be in 3 months?" A compound question split into a SQL step and a forecast step, then merged.
6. "Forecast revenue for the next 3 months." A line with its interval; the method and backtest error are shown.
7. "What if we raise prices 5%?" A scenario range and a tornado chart.
8. "Which segment should we target?" Ranked actions with trade-offs.
9. "Summarize revenue." Clarification options, then an answer with its assumptions stated.
10. Open the run timeline and the evidence behind any number.
11. *(v4)* "Weekly orders in one region dropped sharply last month. Is that unusual, and what is driving it?" Anomaly verdict with the data-quality screen, then ranked drivers with their causal tier, observed pattern kept apart from possible causes (Section 23).
12. *(v4)* "Which customer segments are we most likely to lose next quarter, and where should we act first?" Ranked segments with intervals, calibration and sample size, labelled as predicted risk (Section 23).
13. *(v4)* "Show revenue by sales representative." A plain refusal: no such table or column, what would make it answerable, and nearby questions that can be answered.
14. *(v4)* "Why did orders drop in the control month?" "No significant driver found", with the evidence that was checked.
15. *(v4)* Dirty-data resolution test: cryptic aliases resolved, duplicates collapsed, and the caveats shown.
16. *(v4)* Open the metrics page: the baseline versus system table, accuracy, latency and cost per tag, and the run inspector for the run just made.

---

## 19. Future deployment design — not part of the current coding task *(v4)*

The following is retained as future reference only. Do not implement these deployment steps in the current local development phases unless the user explicitly changes scope. Redis remains excluded from the current stack.

### 19.1 Public deployment

The final system runs at a public URL that anyone can open without installing anything.

| Item | Decision |
| --- | --- |
| Packaging | One Docker image for the API and worker, one for the web app, Docker Compose for local runs |
| Hosting | One public host (Fly.io, Render or Cloud Run), managed relational storage for application state and traces if needed, the supplied demo warehouse packaged as a read-only SQLite file with a data snapshot id |
| Access | Open for read-only questions; no sign-up required for the demo, an optional invite token for heavier use |
| Entry page | Chat, sample questions for each analysis type, a visible "Analysis used" line on every answer, a link to the run inspector and the metrics page |
| Health | `/healthz` (liveness), `/readyz` (database, queue and model gateway), `/version` (git tag, context version, prompt versions, data snapshot id) |
| Release | CI builds on a tag, runs the evaluation gates, deploys, then runs a smoke test against the public URL (one question per analysis type plus one refusal) |
| Rollback | Previous image kept; rolling back is one command and restores the matching context and prompt versions |

### 19.2 Protection for a public system

- Rate limits per IP and per session, queue-depth limits, and a global daily cost cap that switches the system to a cheaper model tier and finally to a polite "daily limit reached" message.
- Read-only database role, AST guard and sandbox as in Section 14. Free-text input is length-limited and treated as untrusted.
- No raw secrets in the image, the repository, prompts or traces (Section 14).
- Questions and answers are stored for inspection only with PII masked; a retention period is stated on the page.

### 19.3 README (setup from scratch)

The README lets someone with only the repository run everything:

1. Prerequisites (Python version, Node version, Docker) and `cp .env.example .env` with the keys to fill in.
2. `make setup` installs dependencies; `make seed` connects the ready-to-use database, builds the catalog and context index, and precomputes initial insight tables in the agent store.
3. `make run` starts the API, worker and web app locally; `make eval` runs every suite and writes `evals/results/<tag>.json`; `make metrics` opens the metrics page.
4. `make test` runs unit and contract tests; `make eval` includes schema retrieval, value linking, large-warehouse scaling, planner/agent contracts, SQL correctness/safety, and analysis suites; `make deploy` documents the deployment path.
5. A short troubleshooting section and the list of every environment variable.

---

## 20. Submission deliverables map *(v4)*

| Deliverable in the brief | Where it lives | Checked by |
| --- | --- | --- |
| README to set up and run from scratch | `README.md` (Section 19.3) | CI job that follows the README commands on a clean runner |
| APPROACH.md with everything it links to | `APPROACH.md` (submission view of this document) and `docs/` | Link checker in CI |
| ARTEFACT.md with everything it links to | `ARTEFACT.md`: public URL, how to use and inspect, results per tag, screenshots, known limits | Link checker in CI |
| Diagrams as images or source | `diagrams/` (draw.io or Mermaid source plus exported images) | CI checks that each linked diagram exists and matches Section 5.3: named agents, refusal/clarification branches, planner DAG, bounded retries, data/insight stores, verification and evidence-backed answer flow |
| Code, plus evaluation benchmarks | `apps/`, `packages/`, `prompts/`, and `evals/` | End-to-end tests run against the ready-to-use database |
| Prompt pack: every prompt the system runs on, as versioned files | `prompts/` (Section 21) | CI check that no prompt string exists in code outside `prompts/` |
| Evaluation framework: set, code, committed results per prototype | `evals/sets/`, `packages/eval/`, `evals/results/` | CI check that each tag has a results file |
| Observability view with problem metrics, accuracy, latency and cost | In-app metrics page and run inspector (Section 12.1) | Smoke test loads the page and finds every required panel |
| Coding-agent setup: rules, specification, subagents, hooks, reusable prompts | `.agent/` (Section 22) | Listed and linked from ARTEFACT.md |
| Tagged prototypes | Git tags `v0.1` to `v1.0` (Section 16.1) | CI creates tags only with results |
| Public URL | Section 19.1 | Post-deploy smoke test |
| No secrets in the repository | `.env.example`, secret scanner in pre-commit and CI | Scanner must pass |

---

## 21. Prompt pack *(v4)*

Every prompt the system runs on is a file in `prompts/`, never a string inside code.
```text
prompts/
  README.md                     How prompts are written, versioned and evaluated
  context_resolver/v1.md
  intent_extractor/v1.md
  grounder_disambiguation/v1.md
  answerability_explain/v1.md   Wording of refusals (the decision itself is deterministic)
  clarifier/v1.md
  planner/v1.md
  sql_generate/v1.md
  sql_repair/v1.md
  composer/v1.md                Includes the causal-tier wording rules
  viz_annotate/v1.md
  judge_rubric/v1.md            LLM judge for narrative quality (hybrid judging, Section 12)
  alias_drafting/v1.md          Drafts descriptions and synonyms at ingestion
  baseline_naive/v1.md          The B0 prompt, frozen
```

Each file has a header and a body:

```yaml
---
id: sql_generate
version: 1.3.0
model_tier: strong
temperature: 0
input_schema: contracts/sql_generate_in.json
output_schema: contracts/sql_generate_out.json
owner: backend
eval_suite: sql
---
(prompt text with named placeholders)
```

Rules: prompts load through one registry by `id` and `version`; the version and a content hash are stamped on every trace and cache key; any change to a prompt file triggers the suites named in its `eval_suite`, and a regression blocks the merge; a prompt is changed through a pull request that shows the before and after evaluation numbers; the baseline prompt is frozen so the comparison stays fair.

---

## 22. Coding-agent setup *(v4)*

The team builds with a coding agent. The setup is committed in `.agent/` so the method is reproducible and reviewable.

```text
.agent/
  rules.md              Project rules the agent must follow (architecture, contracts first, tests first,
                        never hand-write SQL strings in agents, prompts only in prompts/, no secrets)
  spec/
    requirements.md     Requirements in testable form, linked to the matrices in Sections 2 and 2.1
    contracts.md        Typed contracts and error codes (Section 7)
    acceptance.md       Acceptance tests and gates (Section 12)
  subagents/
    contract-guardian.md  Checks that changes keep contracts versioned and consumers updated
    sql-reviewer.md       Reviews generated and hand-written SQL against the allow-list rules
    eval-runner.md        Runs the relevant suites after a change and summarises regressions
    prompt-linter.md      Checks prompt files for header, placeholders, version bump and eval link
    data-gen-reviewer.md  Checks generators for seeding, ground-truth ledger and leakage
  hooks/
    pre-commit            Secret scan, formatting, contract tests, prompt lint
    post-edit             Fast unit tests for the touched package
    pre-tag               Full evaluation run and gate check; refuses the tag on regression
  commands/
    new-prototype.md      Steps to cut a tagged prototype with results and changelog
    add-table.md          Ingestion checklist (Section 9.3)
    add-eval-case.md      Adds a case to a suite with its expected result
    write-decision.md     Creates a decision record from a template
  prompts/
    spec-to-tests.md      Turns an acceptance criterion into failing tests first
    review-checklist.md   Pull-request review prompt
```

Working method (software lifecycle): write the spec and the acceptance test first, implement against stub contracts, run the suites, tag the prototype with its results. Session traces from the coding agent are kept so the way the system was built can be reviewed.

---

## 23. Worked walk-through of the two brief questions *(v4)*

### 23.1 "Weekly orders in one region dropped sharply last month — is that unusual, and what is driving it?"

1. **Context and intent.** Standalone question; intent `so_what/anomaly` with a follow-on `why`; metric `orders`, grain week, dimension region, period last month. If the region is not named, the clarifier offers the regions that exist, in a closed list.
2. **Ground and gate.** Metric `orders`, dimension `region` (state) and the weekly grain exist; enough history exists; the likely drivers in `drivers.yaml` that are measured (sessions, marketing spend, stockouts, delivery delay, promotions, price) are listed, and unmeasured ones (for example competitor actions, if absent) are flagged for the answer.
3. **Plan (DAG).** `s1` weekly orders for the region from the clean view (SQL, validated by execution) and `s2` the same series for the other regions as a peer set (SQL); `s3` `detect_data_quality` on the series; `s4` `detect_anomalies` (STL residual with a robust z-score and the peer comparison); `s5` `impact_size`; then, if the dip is confirmed, `s6` `driver_analysis` (funnel decomposition into sessions, conversion and order value, then candidate drivers with lagged correlation, partial correlation and p-values); `s7` merge.
4. **Verify.** Sample size, window coverage, and the data-quality screen (a duplicate load or a gap is reported as a data issue, not as demand).
5. **Answer.** Sections: *Analysis used* (anomaly detection, then root-cause analysis); *Verdict* (unusual or not, with the score, the size in orders and percent, and the interval); *Observed pattern* (what moved and when, with the waterfall); *Possible causes* (ranked, with contribution size, lag, p-value and the causal tier, worded as "associated with" unless a quasi-experiment supports more); *What was not assessed* (unmeasured drivers); *Evidence* (each SQL, the method, the parameters and every number's step reference); *Suggested checks*.
6. **If no driver is significant** (as in the control month) the answer says so plainly and lists what was tested.

### 23.2 "Which customer segments are we most likely to lose next quarter, and where should we act first?"

1. **Intent.** `what_next/churn_risk`, then `now_what`. Slots: horizon next quarter, objective retention, segment dimensions from the semantic layer (default: region, acquisition channel, RFM tier), constraints optional.
2. **Gate.** A resolved customer entity with repeat history must exist; if not, refuse with the reason and the nearest answerable question (for example order trends by region).
3. **Plan (DAG).** `s1` build features at the cutoff from clean views and the entity map; `s2` `churn_model` (time-split, calibrated) or read `churn_scores` from the insight store; `s3` `prioritize_segments` (expected revenue at risk with bootstrap intervals, actionability weight); `s4` explanation of top features for the leading segments; `s5` merge.
4. **Verify.** Holdout metrics shown, calibration within the gate, segment sample sizes above the minimum, ranking stability across bootstraps.
5. **Answer.** *Analysis used* (churn prediction and prioritisation); *Ranking* (segment, predicted churn probability, revenue at risk, interval, sample size); *Why these segments score high* (model attributions, causal tier C, "associated with", not proof of cause); *Where to act first* (priority order, with the actionable levers and a suggested pilot with a holdout group to test the effect); *Model quality* (holdout AUC-PR against the heuristic baseline, calibration, lift); *Evidence* (queries, features, cutoff, model version, seed).

---

## 24. Onboarding and connectivity flow *(v6: gated, asynchronous setup)*

The chat is **locked until the required setup checks pass**. The onboarding wizard is a separate UI route and creates a durable setup job; it must not keep an HTTP request open while profiling, embedding, or indexing runs. Users can leave and return, see progress, inspect task-level errors, and retry failed stages without rebuilding successful artifacts unnecessarily.

### 24.1 Step-by-step wizard

1. **Choose/configure the LLM provider.** Offer OpenAI, Google Gemini, and Anthropic Claude through the provider-agnostic gateway. The user may select a model per task tier when supported. Accept a key or use a deployment-managed key; validate with a small health-check request. Store credentials only in the backend secret store, encrypted and tenant-scoped; never return them to the browser or write them to logs. Explain whether the key is user-supplied or deployment-managed.
2. **Connect the database.** Support PostgreSQL and MySQL customer connections, plus SQLite for local development and tests. Use SQLAlchemy drivers and a read-only database identity. Keep the agent's own application store separate from the customer warehouse; the selected SQLite/MySQL storage profile and memory adapter are defined in Sections 8.4 and 9.7. Test connectivity, permissions, allowed schemas, statement timeout and representative metadata reads. Display discovered schemas/tables and let the user select the scope. Do not treat a successful TCP connection alone as readiness.
3. **Add optional business context.** Allow multiple PDF documents plus supported text/Markdown/CSV business-logic files where feasible. PDFs may contain metric definitions, KPI rules, business glossary, fiscal calendar, exclusions, domain terminology, or policies. Show filenames, size, ingestion status and document-level errors. Extract text/OCR only when required; preserve source/page metadata and access controls. Treat document contents as untrusted context, not executable instructions. Users can skip this step and add files later.
4. **Start asynchronous preparation.** Create a durable `setup_job_id` and run a checkpointed task graph. Tasks include:
   - discover tables, columns, types, keys, foreign keys, constraints, views and permissions;
   - profile columns with bounded, privacy-aware samples and useful statistics;
   - draft semantic-layer entities, metrics, dimensions, synonyms, grains, join paths, business definitions and caveats;
   - extract/chunk documents, attach source/page metadata, embed chunks and build a document index;
   - build hybrid schema/metadata retrieval indexes (lexical/BM25 + embeddings), join graph and value-linking indexes as appropriate;
   - build canonical clean views/entity maps and the agent-owned insight-store structures where enabled;
   - validate index consistency, permissions, provider health, schema references, and sample read-only queries;
   - run setup smoke tests and emit a readiness report.
5. **Review and approve.** Present the generated semantic layer, key relationships, candidate metric definitions, document citations and warnings. Users can edit/approve business definitions and exclude sensitive tables/columns. Rebuild only dependent artifacts after edits. Store semantic-layer and index versions for reproducibility.
6. **Unlock chat when readiness gates pass.** Required gates: LLM health check; database read-only connection; selected schema catalog complete enough for the configured scope; semantic layer has no blocking errors for enabled capabilities; schema/document indexes report ready or explicitly skipped; sample query and SQL safety checks pass. Document indexing is optional, so its failure should disable document-grounded answers but should not block database-only chat if all required database gates pass. Conversely, if schema catalog or SQL safety validation fails, keep chat locked and explain how to fix it.
7. **Chat and maintain.** Show suggested sample questions from the approved catalog, “Analysis used,” evidence and run-inspector links. Detect schema or document changes and mark affected indexes stale. Offer incremental re-indexing, full rebuild when required, and an admin-visible setup history.

### 24.2 Setup-job status and failure policy

The job uses the same durable event pattern as runtime runs but a distinct `setup_job_id` and event namespace:

```text
setup.started                 {setup_job_id, selected_database, selected_schemas}
setup.stage.started           {stage, label}
setup.stage.progress          {stage, completed_items?, total_items?}
setup.stage.completed         {stage, artifact_version?, summary}
setup.stage.failed            {stage, error_code, safe_message, retryable}
setup.warning                 {code, message, affected_capabilities[]}
setup.review.required         {draft_semantic_layer_version, issues[]}
setup.readiness.updated       {ready, required_checks[], optional_capabilities[]}
setup.completed               {ready, enabled_capabilities[], disabled_capabilities[]}
```

Progress is persisted and resumable. A failed optional PDF/document index may be skipped or retried; a failed schema catalog or security gate cannot be bypassed. Keep partial results and retries idempotent. Show the user which features remain unavailable rather than presenting a false all-green status. Never show fabricated progress percentages.

### 24.3 Semantic layer and document grounding

Database metadata and PDF business context are distinct evidence sources. Semantic definitions should record provenance (`database_catalog`, `approved_user_definition`, or `document`), version, reviewer/approval status and source references. When a PDF defines a KPI, answers should cite the document/page as business-definition evidence while data values still come from validated query/model artifacts. If sources conflict, surface the conflict for review or clarification; do not silently choose one. Indexing a document does not grant database access, change permissions, or authorize execution.

### 24.4 Public demo versus configured installation

The public demo may use preconfigured provider and demo warehouse settings and bypass the wizard for the demo tenant only. The normal deployment must use the full gated flow. No global “skip setup” flag may accidentally unlock an unconfigured tenant.

### 24.5 Acceptance tests

- Provider credentials never appear in browser responses, logs, traces or exported run data.
- PostgreSQL/MySQL read-only access and SQLite development setup each pass connection and permission tests.
- Multiple PDFs can be ingested independently; one malformed PDF does not corrupt other documents or the database index.
- Setup continues after client disconnect and resumes from persisted stage state.
- Chat remains locked when a required gate fails and unlocks only after all required gates pass.
- Optional document-index failure disables document-grounded answers but leaves database-only features available when safe.
- Schema/document changes mark the right artifacts stale and trigger a scoped rebuild.
- Progress events match real task states; all failures expose a safe, actionable message and retryability.
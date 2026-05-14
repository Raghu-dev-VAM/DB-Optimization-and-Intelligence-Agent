# DB Optimization & Intelligence Agent — Technical Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend](#backend)
   - [Entry Point](#entry-point)
   - [API Endpoints](#api-endpoints)
   - [Agent System](#agent-system)
   - [Multi-Agent Orchestration](#multi-agent-orchestration)
   - [Static Analysis Engine](#static-analysis-engine)
   - [Schema Agent](#schema-agent)
   - [Groq AI Client](#groq-ai-client)
4. [Frontend](#frontend)
   - [API Layer](#api-layer)
   - [UI Tabs](#ui-tabs)
5. [Analysis Modes](#analysis-modes)
6. [Data Flow](#data-flow)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Sample Data & Testing](#sample-data--testing)

---

## Overview

The DB Optimization & Intelligence Agent is a full-stack prototype that analyzes SQL code — queries, stored procedures, functions, views, DDL, and DML — and produces performance, security, dependency, and schema insights.

It supports two analysis modes:

- **Quick Analysis** — pure rule-based, no AI, no API key required
- **AI Analysis** — 5-agent orchestration powered by Groq (`llama-3.3-70b-versatile`)

Supported database targets: SQL Server, PostgreSQL, Oracle, and generic SQL.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                    │
│  InputPanel → agentApi.js → Tabs (Fix/Diagnose/...) │
└────────────────────┬────────────────────────────────┘
                     │ HTTP (REST)
┌────────────────────▼────────────────────────────────┐
│              Python HTTP Server (server.py)         │
│         ThreadingHTTPServer on port 8020            │
└──────┬──────────────────────────┬───────────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────────────────┐
│  sql_agent  │          │   SQLOrchestratorAgent       │
│  (static)   │          │  Parser → Security →         │
│             │          │  Dependency → Optimizer →    │
└─────────────┘          │  Reporter                    │
                         └────────────┬────────────────┘
                                      │
                              ┌───────▼──────┐
                              │  GroqClient  │
                              │  (Groq API)  │
                              └──────────────┘
```

---

## Backend

### Entry Point

**`backend/server.py`**

A stdlib `ThreadingHTTPServer` — no framework dependency. Serves both the REST API and the compiled React frontend static files.

- Default port: `8020`
- Custom port: `python backend/server.py 8030`
- On Render: reads `PORT` env var and binds to `0.0.0.0`

Three top-level objects are initialized at startup:

| Object | Class | Purpose |
|---|---|---|
| `agent` | `SqlIntelligenceAgent` | Quick/static analysis |
| `ai_parser` | `SQLParserAgent` | AI parser (used by orchestrator) |
| `orchestrator` | `SQLOrchestratorAgent` | Multi-agent AI analysis |

---

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/ai-status` | Test Groq connectivity, list active agents |
| GET | `/api/history` | Last 25 analysis results |
| GET | `/api/memory` | In-session object memory + dependency map |
| POST | `/api/analyze` | Quick (static) analysis |
| POST | `/api/analyze-multi-agent` | Full AI multi-agent analysis |
| POST | `/api/add-object` | Add a related SQL object to session memory |
| POST | `/api/artifact` | Download a specific artifact as plain text |
| POST | `/api/schema/design` | Static schema design from prompt or DDL |
| POST | `/api/schema/design-ai` | AI-powered schema design |
| POST | `/api/reset` | Clear session memory and history |

All endpoints return JSON. CORS is open (`Access-Control-Allow-Origin: *`).

---

### Agent System

**`backend/agent_config.py`** — `SQLAgentSystem`

Central configuration registry. Defines an `AgentConfig` dataclass for each agent and the Groq model settings.

```python
groq_config = {
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.1,
    "max_tokens": 3000
}
```

Workflow sequences per analysis type:

| Analysis Type | Agent Sequence |
|---|---|
| `full_analysis` | parser → dependency → optimizer → security → reporter |
| `performance_only` | parser → optimizer → reporter |
| `security_only` | parser → security → reporter |
| `dependency_only` | parser → dependency → reporter |

---

### Multi-Agent Orchestration

**`backend/sql_orchestrator_agent.py`** — `SQLOrchestratorAgent`

Coordinates all five specialist agents. Each analysis run produces an `OrchestrationResult` dataclass.

**Orchestration flow:**

1. `_determine_strategy(sql, analysis_type)` — picks a named strategy based on SQL content (e.g., `comprehensive_procedure_analysis`, `security_priority_analysis`)
2. `_select_agents(strategy)` — maps strategy to agent list
3. `_plan_execution_sequence(agents, sql)` — orders agents (security is promoted for risky SQL)
4. Executes agents sequentially, passing results forward
5. `_calculate_overall_confidence(results)` — weighted average (security weight: 1.5, parser: 1.2)
6. `_compile_recommendations(results)` — top 10 cross-agent recommendations sorted by priority
7. `_compile_ai_insights(results)` — cross-agent correlations and overall assessment

**Strategies:**

| Strategy | Triggered By |
|---|---|
| `comprehensive_procedure_analysis` | `CREATE PROCEDURE` / `CREATE FUNCTION` |
| `query_optimization_focused` | SELECT with JOIN or WHERE |
| `security_priority_analysis` | `EXEC(`, `EXECUTE(`, `sp_executesql` |
| `schema_analysis` | `CREATE TABLE` / `ALTER TABLE` |
| `balanced_analysis` | Default |

---

### Specialist Agents

#### SQLParserAgent (`sql_parser_agent.py`)

Parses SQL structure. Returns a `ParsedSQL` dataclass.

- Runs static parse first (reuses `sql_agent.py` functions)
- Enhances with Groq AI: detects aliases, CTEs, temp tables, dynamic SQL, missing references
- Output: tables, joins, filters, references, missing_references, complexity_score (1–10), confidence

#### SQLSecurityAgent (`sql_security_agent.py`)

Identifies security vulnerabilities. Returns `SecurityAnalysisResult`.

Static detectors:
- SQL injection (dynamic SQL with string concatenation)
- Privilege escalation (`xp_cmdshell`, `EXECUTE AS`, `OPENROWSET`)
- Information disclosure (`SELECT *` on sensitive tables)
- Missing error handling (write ops without TRY/CATCH)
- Access control bypass (`WHERE 1=1`, `UNION SELECT`, comment injection)

AI enhancement: advanced injection techniques, business logic flaws, compliance mapping (OWASP, CWE, PCI-DSS, GDPR).

Risk scoring: `security_score = 100 - (critical×40 + high×20 + medium×10)`

#### SQLOptimizerAgent (`sql_optimizer_agent.py`)

Performance analysis and SQL rewriting. Returns `OptimizationResult`.

Static detectors: `SELECT *`, cursors, WHILE loops, missing indexes.

AI enhancement: sargability issues, join order, subquery vs JOIN, parameter sniffing, TempDB pressure.

`generate_optimized_sql()` — calls Groq to produce a complete, runnable optimized SQL string with inline comments.

Index script generation supports SQL Server (`NONCLUSTERED`), PostgreSQL (`CONCURRENTLY`), and Oracle.

#### SQLDependencyAgent (`sql_dependency_agent.py`)

Maps object relationships. Returns `DependencyAnalysisResult`.

- Builds dependency graph (nodes + edges)
- Detects circular dependencies via DFS
- Calculates deployment order via Kahn's topological sort
- Impact scoring: `(direct_deps × 2) + (direct_dependents × 3) + (missing × 5)`
- AI enhancement: hidden/implicit dependencies, cross-database deps, dynamic SQL deps

#### SQLReporterAgent (`sql_reporter_agent.py`)

Generates all reports and downloadable artifacts. Returns `ReportGenerationResult`.

Reports generated:
- Executive Summary (status, key findings, business impact)
- Technical Report (code structure, performance, security, dependency details)
- Recommendations Report (prioritized action list + index recommendations)
- Deployment Guide (pre-deployment checklist, deployment order, rollback plan)
- Risk Assessment Report (security score, impact level, deployment recommendation)

Artifacts:
- `index_creation_script` — ready-to-run index DDL
- `security_remediation_guide` — step-by-step remediation
- `deployment_checklist` — ordered deployment checklist

---

### Static Analysis Engine

**`backend/sql_agent.py`** — `SqlIntelligenceAgent`

Pure Python, zero external dependencies. Powers Quick Analysis mode and serves as the base layer for AI analysis.

Key functions:

| Function | Purpose |
|---|---|
| `normalize_sql(sql)` | Normalize line endings and whitespace |
| `classify_sql(sql, source_type)` | Detect object type (Stored Procedure, Function, View, DDL, DML, Query) |
| `extract_object_name(sql, type)` | Regex-based name extraction |
| `extract_tables(sql)` | FROM, JOIN, UPDATE, INSERT INTO, DELETE FROM |
| `extract_joins(sql)` | Type, table, condition for each join |
| `extract_filters(sql)` | WHERE clause predicates |
| `extract_references(sql)` | EXEC / EXECUTE calls |
| `detect_findings(...)` | 15+ rule-based issue detectors |
| `build_suggestions(...)` | Actionable suggestions per finding |
| `estimate_metrics(...)` | Estimated execution time, logical reads, risk score |
| `optimize_sql(...)` | Static SQL rewrite (SELECT *, NOLOCK removal) |
| `build_index_scripts(...)` | Index DDL per DB type |
| `build_impact(...)` | Affected tables, downstream systems, risk level |
| `build_execution_plan(...)` | Operator-level plan review |

**Rule-based findings detected:**

- SELECT * usage
- Cursor / row-by-row processing
- WHILE loop (RBAR risk)
- Temp table usage (TempDB pressure)
- Dynamic SQL
- Nested stored procedure calls
- Missing referenced objects
- Function in WHERE predicate (sargability)
- Leading wildcard LIKE
- Sort operation without supporting index
- Heavy join graph (3+ joins)
- NOLOCK hint
- Parameter sniffing risk
- Missing TRY/CATCH around write logic
- Transaction without visible ROLLBACK
- Unfiltered table read

**Session memory:**

`SqlIntelligenceAgent` maintains an in-memory `objects` dict (keyed by slugified name) and a `history` list (last 25 results). The `dependency_map()` method builds a live graph from all objects in memory.

**Schema design** (`design_schema`): accepts plain English prompts or DDL. Infers entities, relationships, generates migration DDL, rollback script, ERD (Mermaid format), and migration plan.

---

### Groq AI Client

**`backend/groq_client.py`** — `GroqClient`

Wraps the Groq SDK. Supports primary + fallback API keys.

- Primary key: `GROQ_API_KEY`
- Fallback key: `GROQ_API_KEY_FALLBACK`
- Model: `llama-3.3-70b-versatile`
- All agents call `groq_client.call_ai(system_message, prompt, timeout)`
- Response is parsed as JSON; if JSON extraction fails, raw content is returned under `reasoning`

---

## Frontend

React + Vite SPA. In production, the compiled `dist/` folder is served directly by the Python server.

### API Layer

**`frontend-react/src/api/agentApi.js`**

| Function | Endpoint | Mode |
|---|---|---|
| `analyzeSQL` | POST `/api/analyze` | Quick Analysis |
| `analyzeMultiAgent` | POST `/api/analyze-multi-agent` | AI Analysis |
| `getMultiAgentStatus` | GET `/api/ai-status` | Status check |
| `addRelatedObject` | POST `/api/add-object` | Dependency workflow |
| `designSchema` | POST `/api/schema/design` | Static schema |
| `designSchemaAI` | POST `/api/schema/design-ai` | AI schema |
| `downloadArtifact` | POST `/api/artifact` | Artifact download |
| `resetSession` | POST `/api/reset` | Session reset |

### UI Tabs

| Tab | File | Content |
|---|---|---|
| Fix | `FixTab.jsx` | Optimized SQL, index scripts, suggestions |
| Diagnose | `DiagnoseTab.jsx` | Findings, metrics, execution plan |
| Dependencies | `DependenciesTab.jsx` | Dependency graph, missing objects, add related object |
| Deploy | `DeployTab.jsx` | Impact analysis, deployment guide, downloadable reports |
| Schema | `SchemaTab.jsx` | Schema design, ERD, migration/rollback scripts |

State is managed via **`frontend-react/src/store/agentStore.js`** (Zustand or similar).

---

## Analysis Modes

### Quick Analysis

- Calls `POST /api/analyze`
- Uses `SqlIntelligenceAgent` (pure Python, no AI)
- Returns: summary, findings, suggestions, metrics, optimized SQL draft, index scripts, execution plan, dependency map, impact, artifacts
- Works without any API key

### AI Analysis

- Calls `POST /api/analyze-multi-agent`
- Uses `SQLOrchestratorAgent` → 5 specialist agents → Groq API
- Returns everything from Quick Analysis plus:
  - `ai_enhanced: true`
  - `orchestration_strategy`
  - `agents_used` list
  - `overall_confidence` score
  - `processing_time`
  - `ai_recommendations` (top 10, cross-agent)
  - `ai_insights` (cross-agent correlations, overall assessment)
  - AI-generated `optimized_sql` (complete, runnable)
  - AI security issues tagged `[AI Security]`
  - AI optimizer issues tagged `[AI Optimizer]`
- Falls back to Quick Analysis result if orchestration fails, still attempts AI SQL optimization

---

## Data Flow

### Quick Analysis

```
User pastes SQL
  → POST /api/analyze { sql, db_type, source_type }
  → SqlIntelligenceAgent.analyze()
      → normalize → classify → extract → detect_findings
      → build_suggestions → estimate_metrics → optimize_sql
      → build_index_scripts → build_impact → build_execution_plan
      → build_report → store in session memory
  → JSON response → Frontend tabs
```

### AI Analysis

```
User pastes SQL
  → POST /api/analyze-multi-agent { sql, db_type, analysis_type }
  → SQLOrchestratorAgent.orchestrate_analysis()
      → SQLParserAgent.parse_sql()       [Groq]
      → SQLSecurityAgent.analyze_security()  [Groq]
      → SQLDependencyAgent.analyze_dependencies()  [Groq]
      → SQLOptimizerAgent.optimize_sql()  [Groq]
      → SQLReporterAgent.generate_reports()  [Groq]
  → SqlIntelligenceAgent.analyze()  (base structure)
  → SQLOptimizerAgent.generate_optimized_sql()  [Groq]
  → Merge results → JSON response → Frontend tabs
```

### Dependency Workflow

```
1. Analyze main procedure → missing references detected
2. User pastes related object → POST /api/add-object
3. Object stored in SqlIntelligenceAgent.objects memory
4. Re-run analysis → missing_references now resolved
5. Dependency map updated with new node/edges
```

---

## Configuration

**`.env`** (copy from `.env.example`):

```
GROQ_API_KEY=your_actual_key_here
GROQ_API_KEY_FALLBACK=optional_second_key
GROQ_MODEL=llama-3.3-70b-versatile   # optional override
PORT=8020                              # optional, used on Render
```

**`backend/agent_config.py`** — model, temperature (0.1), max_tokens (3000) per agent.

---

## Deployment

### Local

```powershell
# Terminal 1 — Backend
python backend/server.py

# Terminal 2 — Frontend dev server (optional)
cd frontend-react
npm install
npm run dev
```

Backend serves compiled frontend at `http://127.0.0.1:8020`.  
Frontend dev server runs at `http://localhost:5173` and proxies API calls.

### Render

`render.yaml` is included. Settings:

| Setting | Value |
|---|---|
| Runtime | Python |
| Build Command | `echo "No build required"` |
| Start Command | `python -B backend/server.py` |
| Root Directory | `sql-optimization-db-intelligence-agent` |

The server auto-detects Render via the `RENDER` env var and binds to `0.0.0.0`.

---

## Sample Data & Testing

**`sample-data/`**

| File | Purpose |
|---|---|
| `usp_ProcessCustomerOrders.sql` | Main demo procedure — references a missing object |
| `usp_UpdateOrderRisk.sql` | The missing referenced procedure to paste in Dependencies tab |
| `test_cases.sql` | Additional SQL test cases |

**Test scripts** (root directory):

| Script | Tests |
|---|---|
| `test_server.py` | Basic server endpoints |
| `test_ai_endpoint.py` | AI analysis endpoint |
| `test_ai_optimizer.py` | Optimizer agent |
| `test_ai_validation.py` | AI response validation |
| `test_groq.py` | Groq client connectivity |
| `test_integration.py` | End-to-end integration |

See `TESTING_GUIDE.md` for full test instructions.

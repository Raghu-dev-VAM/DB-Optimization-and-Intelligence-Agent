# DB Optimization & Intelligence Agent

Standalone prototype for analyzing and optimizing database queries, objects, schemas, dependencies, and reports, with room to extend beyond SQL into Oracle, PostgreSQL, SQL Server, and NoSQL platforms.

## Features

- Paste SQL query, stored procedure, function, view, DDL, or DML.
- Upload `.sql` files from the browser.
- Classify DB object type.
- Extract tables, joins, filters, and referenced stored procedures.
- Detect missing referenced objects and ask the user to paste them.
- Remember pasted objects in an in-session object memory.
- Build a dependency map across procedures and tables.
- Detect performance and reliability issues such as cursors, `SELECT *`, functions in `WHERE`, leading wildcard `LIKE`, TempDB pressure, parameter sniffing risk, missing error handling, and risky dynamic SQL.
- Generate optimized SQL draft, index recommendation scripts, execution plan review, impact analysis, and downloadable reports.

## Run

**Terminal 1 — Backend:**

```powershell
python backend/server.py
```

Then open:

```text
http://127.0.0.1:8020
```

You can also choose another port:

```powershell
python backend/server.py 8030
```

**Terminal 2 — Frontend (dev mode):**

```powershell
cd frontend-react
npm install
npm run dev
```

Then open: `http://localhost:5173`

## Analysis Modes

The app supports two fully separate analysis flows:

- **Quick Analysis** — pure rule-based, no AI, no external dependencies. Works without any API key.
- **AI Analysis** — full 5-agent orchestration powered by Groq (Parser, Security, Dependency, Optimizer, Reporter). Requires a valid `GROQ_API_KEY` in `.env`. If AI is unavailable, an error is shown — it does not fall back to static.

## Groq Setup (for AI Analysis)

1. Get a free API key at https://console.groq.com
2. Copy `.env.example` to `.env`
3. Set your key:

```
GROQ_API_KEY=your_actual_key_here
```

4. Restart the backend.

## Deploy On Render

Create a Render Web Service with these settings:

- Root Directory: `sql-optimization-db-intelligence-agent` if deploying from the parent repo
- Runtime: Python
- Build Command: `echo "No build required"`
- Start Command: `python -B backend/server.py`

The included `render.yaml` contains the same settings for Render Blueprints. The server uses Render's `PORT` environment variable and binds to `0.0.0.0` when running on Render.

## Stored Procedure Dependency Workflow

1. Paste or load `sample-data/usp_ProcessCustomerOrders.sql`.
2. Select Quick Analysis or AI Analysis mode.
3. Run analysis.
4. The agent detects `dbo.usp_UpdateOrderRisk` as a missing referenced procedure.
5. Open the Dependencies tab.
6. Paste `sample-data/usp_UpdateOrderRisk.sql` into the related object box.
7. Add it to the dependency workspace.
8. The agent remembers it and re-runs analysis in the same mode (Quick or AI), updating object memory, dependency map, reports, and impact analysis.

## Notes

Quick Analysis runs without database credentials and without external packages. AI Analysis requires a Groq API key. Actual database execution-plan import and live DB connectors can be added later with SQL Server, PostgreSQL, or Oracle drivers.

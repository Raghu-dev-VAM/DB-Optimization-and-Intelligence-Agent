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

```powershell
python run_agent.py
```

Then open:

```text
http://127.0.0.1:8020
```

You can also choose another port:

```powershell
python run_agent.py 8030
```

## Deploy On Render

Create a Render Web Service with these settings:

- Root Directory: `sql-optimization-db-intelligence-agent` if deploying from the parent repo
- Runtime: Python
- Build Command: `echo "No build required"`
- Start Command: `python -B run_agent.py`

The included `render.yaml` contains the same settings for Render Blueprints. The server uses Render's `PORT` environment variable and binds to `0.0.0.0` when running on Render.

## Stored Procedure Dependency Workflow

1. Paste or load `sample-data/usp_ProcessCustomerOrders.sql`.
2. Run analysis.
3. The agent detects `dbo.usp_UpdateOrderRisk` as a missing referenced procedure.
4. Open the Dependencies tab.
5. Paste `sample-data/usp_UpdateOrderRisk.sql` into the related object box.
6. Add it to the dependency workspace.
7. The agent remembers it and updates object memory, dependency map, reports, and impact analysis.

## Notes

This prototype uses static rule-based intelligence, so it runs without database credentials and without external packages. Actual database execution-plan import and live DB connectors can be added later with SQL Server, PostgreSQL, or Oracle drivers.

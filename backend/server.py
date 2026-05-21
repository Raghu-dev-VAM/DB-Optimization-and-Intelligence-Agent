from __future__ import annotations

import os
import sys
from pathlib import Path

# ── path setup so agents import correctly from any working directory ──────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uuid
from fastapi import FastAPI, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from sql_agent import SqlIntelligenceAgent
from groq_client import groq_client
from sql_orchestrator_agent import SQLOrchestratorAgent

_orchestrator = SQLOrchestratorAgent()

# ── deployment tracking (in-memory) ──────────────────────────────────────────
# key: "database:procedure_name" → {deployed_at, procedure_name, database}
_deploy_log: dict[str, dict] = {}

# ── app setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="DB Optimization & Intelligence Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── per-session agent store ───────────────────────────────────────────────────
_sessions: dict[str, SqlIntelligenceAgent] = {}

def get_agent(session_id: Optional[str], response: Response) -> tuple[SqlIntelligenceAgent, str]:
    if not session_id or session_id not in _sessions:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = SqlIntelligenceAgent()
        response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return _sessions[session_id], session_id

# ── request models ────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    sql: str = ""
    db_type: str = "SQL Server"
    source_type: str = "auto"

class ArtifactRequest(BaseModel):
    analysis: dict = {}
    artifact_type: str = "db_review_report"

class SchemaRequest(BaseModel):
    prompt: str = ""
    db_type: str = "SQL Server"

class DBExecuteRequest(BaseModel):
    connection_string: str = ""
    ddl_script: str = ""

class SuggestDbNameRequest(BaseModel):
    prompt: str = ""

class ScanRequest(BaseModel):
    connection_string: str = ""

class FetchProcRequest(BaseModel):
    connection_string: str = ""
    procedure_name: str = ""

class DeployRequest(BaseModel):
    connection_string: str = ""
    optimized_sql: str = ""
    procedure_name: str = ""

# ── health & status ───────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "DB Optimization & Intelligence Agent"}


@app.get("/api/history")
def history(response: Response, session_id: Optional[str] = Cookie(default=None)):
    agent, _ = get_agent(session_id, response)
    return agent.get_history()


@app.get("/api/memory")
def memory(response: Response, session_id: Optional[str] = Cookie(default=None)):
    agent, _ = get_agent(session_id, response)
    return agent.get_memory()


import json, re


def _reformat_single_line_sql(sql: str) -> str:
    """Add newlines to single-line SQL at keyword boundaries."""
    keywords = [
        'SELECT', 'FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN',
        'CROSS JOIN', 'JOIN', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY',
        'HAVING', 'INSERT INTO', 'UPDATE', 'SET', 'DELETE FROM', 'CREATE',
        'ALTER', 'BEGIN', 'END', 'DECLARE', 'EXEC', 'EXECUTE', 'UNION', 'ON',
    ]
    keywords.sort(key=len, reverse=True)
    result = sql
    for kw in keywords:
        result = re.sub(rf'(?<![\w])({re.escape(kw)})(?![\w])', rf'\n\1', result, flags=re.IGNORECASE)
    lines = result.split('\n')
    formatted = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if any(upper.startswith(k) for k in ['AND ', 'OR ', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'JOIN', 'FROM']):
            formatted.append('    ' + stripped)
        else:
            formatted.append(stripped)
    return '\n'.join(formatted)


def fix_sql(sql: str) -> str:
    """Auto-fix common AI-generated SQL mistakes."""
    s = sql.strip()
    s = re.sub(r';(\s*OPTION\s*\()', r'\1', s, flags=re.IGNORECASE)
    return s


def is_valid_sql(sql: str) -> bool:
    """Check SQL has minimum usable structure."""
    s = sql.strip()
    if not s or len(s) < 20:
        return False
    if re.search(r'\bBEGIN\b', s, re.IGNORECASE) and not re.search(r'\bEND\b', s, re.IGNORECASE):
        return False
    if not re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)\b', s, re.IGNORECASE):
        return False
    return True


def enrich_with_groq(sql: str, result: dict, db_type: str) -> dict:
    """Single focused Groq call — adds plain English summary, per-finding explanations, and AI-optimized SQL."""

    findings = result.get("findings", [])
    finding_titles = [f"{f['title']} ({f['severity']})" for f in findings]

    prompt = f"""You are a SQL performance expert. A rule-based engine already analyzed this SQL and found issues.
Your job is to enrich the results with plain English explanations a junior developer can understand.

SQL:
```sql
{sql[:2000]}
```

Database: {db_type}
Findings from rule engine: {finding_titles}

Respond in JSON:
{{
  "summary": "One paragraph in plain English explaining the biggest problem and real-world impact. No jargon.",
  "finding_explanations": {{
    "<finding title>": "One sentence explaining why this matters in real terms for a developer."
  }},
  "optimized_sql": "Complete rewritten SQL that fixes the issues. Must be runnable. IMPORTANT SQL RULES: 1) OPTION (RECOMPILE) must be on the same line as or directly after ORDER BY with NO semicolon before it. 2) Never put a semicolon before OPTION. 3) The last statement inside BEGIN...END must end with a single semicolon after OPTION (RECOMPILE) if used."
}}"""

    response = groq_client.call_ai(
        "You are a SQL expert who explains technical issues in plain English.",
        prompt,
        timeout=25
    )

    # Groq sometimes wraps JSON inside a 'reasoning' field — extract it
    if "summary" not in response and "reasoning" in response:
        reasoning = response["reasoning"]
        try:
            start = reasoning.find('{')
            end = reasoning.rfind('}') + 1
            if start != -1 and end > start:
                raw_json = reasoning[start:end]
                raw_json = ''.join(c if ord(c) >= 32 or c in '\t\n\r' else ' ' for c in raw_json)
                raw_json = re.sub(r'(?<!\\)\n', '\\n', raw_json)
                raw_json = re.sub(r'(?<!\\)\r', '\\r', raw_json)
                raw_json = re.sub(r'(?<!\\)\t', '\\t', raw_json)
                response = json.loads(raw_json)
        except Exception:
            summary_match = re.search(r'"summary"\s*:\s*"(.*?)"(?=\s*,\s*")', reasoning, re.DOTALL)
            sql_match = re.search(r'"optimized_sql"\s*:\s*"(.*?)"(?=\s*[}])', reasoning, re.DOTALL)
            if summary_match:
                response = {"summary": summary_match.group(1).replace('\\n', '\n')}
            if sql_match:
                response["optimized_sql"] = sql_match.group(1).replace('\\n', '\n')
            exp_match = re.search(r'"finding_explanations"\s*:\s*(\{.*?\})(?=\s*,\s*"optimized_sql")', reasoning, re.DOTALL)
            if exp_match:
                try:
                    exp_raw = ''.join(c if ord(c) >= 32 else ' ' for c in exp_match.group(1))
                    response["finding_explanations"] = json.loads(exp_raw)
                except Exception:
                    pass

    result["ai_summary"] = response.get("summary", "")

    explanations = response.get("finding_explanations", {})
    for finding in result.get("findings", []):
        if finding["title"] in explanations:
            finding["ai_explanation"] = explanations[finding["title"]]
        else:
            for key, val in explanations.items():
                if key.lower().strip() in finding["title"].lower() or finding["title"].lower() in key.lower():
                    finding["ai_explanation"] = val
                    break

    ai_sql = response.get("optimized_sql", "")
    if ai_sql and len(ai_sql.strip()) > 20:
        ai_sql = ai_sql.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '')
        if '\n' not in ai_sql:
            ai_sql = _reformat_single_line_sql(ai_sql)
        ai_sql = re.sub(r'SET\s+NOCOUNT\s*\n\s*ON', 'SET NOCOUNT ON', ai_sql, flags=re.IGNORECASE)
        ai_sql = re.sub(r'\s+WITH\s*\(\s*NOLOCK\s*\)', '', ai_sql, flags=re.IGNORECASE)
        ai_sql = fix_sql(ai_sql)
        if is_valid_sql(ai_sql):
            result["optimized_sql"] = ai_sql
            if "artifacts" in result:
                result["artifacts"]["optimized_sql"] = ai_sql

    result["ai_enhanced"] = True
    result["ai_status"] = "Rule-based analysis + AI enrichment"
    return result


# ── unified analyze route ─────────────────────────────────────────────────────
# 1. Rule engine runs first (sql_agent.py)
# 2. AutoGen orchestrator runs all 5 specialist agents
# 3. Groq enrichment merges AI insights back into the result
@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, response: Response, session_id: Optional[str] = Cookie(default=None)):
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="Paste SQL or upload a .sql file before analysis.")
    agent, _ = get_agent(session_id, response)

    # Step 1 — rule-based analysis
    result = agent.analyze(req.sql, req.db_type, req.source_type)

    # Step 2 — AutoGen multi-agent orchestration
    try:
        known = {obj["name"]: obj for obj in agent.get_memory().get("objects", [])}
        orch = _orchestrator.orchestrate_analysis(
            sql=req.sql,
            db_type=req.db_type,
            known_objects=known,
        )
        # Merge orchestration results into the base result
        result["orchestration_strategy"] = orch.orchestration_strategy
        result["agents_used"] = orch.agents_used
        result["overall_confidence"] = orch.overall_confidence
        result["ai_recommendations"] = orch.recommendations
        result["ai_insights"] = orch.ai_insights
        result["processing_time"] = orch.total_processing_time
        # Prefer AI-generated optimized SQL if available
        ai_opt = orch.optimization_results.get("query_rewrite_suggestions", [])
        if ai_opt and ai_opt[0].strip():
            cleaned = ai_opt[0].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '')
            if '\n' not in cleaned:
                cleaned = _reformat_single_line_sql(cleaned)
            cleaned = re.sub(r'SET\s+NOCOUNT\s*\n\s*ON', 'SET NOCOUNT ON', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+WITH\s*\(\s*NOLOCK\s*\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = fix_sql(cleaned)
            result["optimized_sql"] = cleaned
            result["artifacts"]["optimized_sql"] = cleaned
        else:
            # query_rewrite_suggestions empty — call generate_optimized_sql directly
            try:
                ai_sql = _orchestrator.optimizer_agent.generate_optimized_sql(
                    req.sql, orch.parsed_results, req.db_type
                )
                if ai_sql and is_valid_sql(ai_sql):
                    result["optimized_sql"] = ai_sql
                    result["artifacts"]["optimized_sql"] = ai_sql
            except Exception as opt_err:
                print(f"[OPTIMIZER] generate_optimized_sql failed: {opt_err}")
        # Merge security vulnerabilities as additional findings
        for vuln in orch.security_results.get("vulnerabilities", []):
            result["findings"].append({
                "title": vuln.get("vulnerability", "Security Issue"),
                "severity": vuln.get("severity", "High"),
                "category": "Security",
                "detail": vuln.get("description", ""),
                "evidence": vuln.get("evidence", ""),
            })
        result["ai_enhanced"] = True
        result["ai_status"] = "Rule-based + AutoGen 5-agent orchestration"
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed, falling back to Groq enrichment: {e}")
        # Step 3 — fallback: single Groq enrichment call
        try:
            result = enrich_with_groq(req.sql, result, req.db_type)
        except Exception:
            result["ai_enhanced"] = False

    return result


@app.post("/api/add-object")
def add_object(req: AnalyzeRequest, response: Response, session_id: Optional[str] = Cookie(default=None)):
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="Paste the referenced object definition first.")
    agent, _ = get_agent(session_id, response)
    return agent.add_related_object(req.sql, req.db_type, req.source_type)


@app.post("/api/artifact")
def artifact(req: ArtifactRequest):
    text = (req.analysis.get("artifacts") or {}).get(req.artifact_type, "")
    return PlainTextResponse(text or "Artifact is not available.")


@app.post("/api/reset")
def reset(response: Response, session_id: Optional[str] = Cookie(default=None)):
    agent, _ = get_agent(session_id, response)
    agent.reset()
    return {"status": "reset"}


# ── schema routes ─────────────────────────────────────────────────────────────
@app.post("/api/schema/design")
def schema_design(req: SchemaRequest, response: Response, session_id: Optional[str] = Cookie(default=None)):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Describe the schema requirement or paste existing DDL.")
    agent, _ = get_agent(session_id, response)
    result = agent.design_schema(req.prompt, req.db_type)
    try:
        from sql_schema_agent import SQLSchemaAgent
        ai = SQLSchemaAgent().design_schema(req.prompt, req.db_type)
        result["tables"] = ai["tables"]
        result["relationships"] = ai["relationships"]
        result["quality_review"] = ai["quality_review"]
        result["migration_script"] = ai["migration_script"]
        result["rollback_script"] = ai["rollback_script"]
        result["erd_summary"] = ai["erd_summary"]
        result["schema_review_report"] = ai["schema_review_report"]
        result["artifacts"] = ai["artifacts"]
        result["ai_enhanced"] = True
        result["ai_status"] = "Rule-based schema + AI enrichment"
    except Exception:
        result["ai_enhanced"] = False
    return result


@app.post("/api/schema/suggest-db-name")
def suggest_db_name(req: SuggestDbNameRequest):
    try:
        from sql_schema_agent import SQLSchemaAgent
        name = SQLSchemaAgent().suggest_db_name(req.prompt)
        return {"db_name": name}
    except Exception as e:
        return {"db_name": "NewDatabaseDB", "error": str(e)}


# ── live db routes ────────────────────────────────────────────────────────────
@app.post("/api/db/scan")
def db_scan(req: ScanRequest):
    if not req.connection_string.strip():
        raise HTTPException(status_code=400, detail="Paste a connection string first.")
    try:
        from db_scanner_agent import scan_database
        return scan_database(req.connection_string)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/db/fetch-procedure")
def db_fetch_procedure(req: FetchProcRequest):
    if not req.connection_string.strip() or not req.procedure_name.strip():
        raise HTTPException(status_code=400, detail="Connection string and procedure name are required.")
    try:
        from db_scanner_agent import get_procedure_source
        return get_procedure_source(req.connection_string, req.procedure_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/db/deploy-optimized")
def db_deploy_optimized(req: DeployRequest):
    if not req.connection_string.strip():
        raise HTTPException(status_code=400, detail="Paste a connection string first.")
    if not req.optimized_sql.strip():
        raise HTTPException(status_code=400, detail="No optimized SQL to deploy.")
    try:
        from db_scanner_agent import deploy_optimized_procedure, _build_conn_str
        from datetime import datetime
        result = deploy_optimized_procedure(req.connection_string, req.optimized_sql, req.procedure_name)
        # Record successful deployment
        _, database = _build_conn_str(req.connection_string)
        key = f"{database}:{req.procedure_name}".lower()
        _deploy_log[key] = {
            "procedure_name": req.procedure_name,
            "database": database,
            "deployed_at": datetime.now().isoformat(timespec="seconds"),
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/db/deploy-log")
def db_deploy_log(req: ScanRequest):
    """Return deploy log entries for a given database."""
    try:
        from db_scanner_agent import _build_conn_str
        _, database = _build_conn_str(req.connection_string)
        entries = {
            k.split(":", 1)[1]: v
            for k, v in _deploy_log.items()
            if k.startswith(database.lower() + ":")
        }
        return entries
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/db/execute")
def db_execute(req: DBExecuteRequest):
    if not req.connection_string.strip():
        raise HTTPException(status_code=400, detail="Paste a connection string first.")
    if not req.ddl_script.strip():
        raise HTTPException(status_code=400, detail="No DDL script to execute.")
    try:
        from db_connector import execute_ddl
        result = execute_ddl(req.connection_string, req.ddl_script)
        return result
    except Exception as e:
        print(f"[DB EXECUTE ERROR] {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ── static file serving (React build) ────────────────────────────────────────
FRONTEND = ROOT.parent / "frontend-react" / "dist"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", sys.argv[1] if len(sys.argv) > 1 else "8025"))
    host = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"
    print(f"DB Optimization & Intelligence Agent running at http://{host}:{port}")
    print(f"API docs available at http://127.0.0.1:{port}/docs")
    uvicorn.run("server:app", host=host, port=port, reload=False)

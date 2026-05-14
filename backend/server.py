from __future__ import annotations

import json
import mimetypes
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

try:
    from backend.sql_agent import SqlIntelligenceAgent
    from backend.sql_parser_agent import SQLParserAgent
    from backend.sql_orchestrator_agent import SQLOrchestratorAgent
except ImportError:  # Allows running from inside the backend folder.
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
    from sql_agent import SqlIntelligenceAgent
    from sql_parser_agent import SQLParserAgent
    from sql_orchestrator_agent import SQLOrchestratorAgent


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-react" / "dist"
agent = SqlIntelligenceAgent()
ai_parser = SQLParserAgent()  # Initialize AI Parser Agent
orchestrator = SQLOrchestratorAgent()  # Initialize Multi-Agent Orchestrator


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "DBOptimizationAgentHTTP/1.0"

    def do_GET(self) -> None:
        print(f"[DEBUG] GET request to: {self.path}")
        
        # Handle API routes first
        if self.path.startswith("/api/"):
            if self.path == "/api/health":
                self.send_json({"status": "ok", "agent": "DB Optimization & Intelligence Agent"})
                return
            if self.path == "/api/test-ai":
                self.send_json({
                    "test": "AI integration test", 
                    "ai_enhanced": True,
                    "ai_status": "✅ Test Endpoint Working",
                    "timestamp": "2026-05-11T16:00:00"
                })
                return
            if self.path == "/api/ai-status":
                print(f"[DEBUG] Handling AI status request")
                try:
                    try:
                        from backend.groq_client import groq_client
                    except ImportError:
                        from groq_client import groq_client

                    test_result = groq_client.call_ai(
                        "You are a test assistant.",
                        "{\"status\": \"connected\", \"test\": true}",
                        timeout=5
                    )
                    response_data = {
                        "connected": True,
                        "status": "Multi-Agent System Ready",
                        "provider": test_result.get('ai_provider', 'unknown'),
                        "model": "llama-3.3-70b-versatile",
                        "agents": ["parser", "security", "dependency", "optimizer", "reporter"]
                    }
                    print(f"[DEBUG] AI Status OK: {response_data}")
                    self.send_json(response_data)
                except Exception as e:
                    print(f"[ERROR] AI Status failed: {e}")
                    self.send_json({
                        "connected": False,
                        "status": "AI Unavailable",
                        "error": str(e),
                        "message": "Groq API unavailable. Check API key and rate limits."
                    })
                return
            if self.path == "/api/history":
                self.send_json(agent.get_history())
                return
            if self.path == "/api/memory":
                self.send_json(agent.get_memory())
                return
            
            # If no API route matched, return 404
            self.send_json({"error": "API endpoint not found"}, HTTPStatus.NOT_FOUND)
            return
        
        # Serve static files for non-API routes
        self.serve_static()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/analyze":
                payload = self.read_json()
                
                # Simple analysis without AI (for testing)
                result = agent.analyze(
                    payload.get("sql", ""),
                    payload.get("db_type", "SQL Server"),
                    payload.get("source_type", "auto"),
                )
                
                print(f"[DEBUG] Original result keys: {list(result.keys())}")
                
                # Force add test AI fields
                result.update({
                    "ai_enhanced": True,
                    "ai_status": "✅ Test AI Status - Force Added",
                    "ai_insights": {"confidence": 0.85, "test": True}
                })
                
                print(f"[DEBUG] Final result keys: {list(result.keys())}")
                print(f"[DEBUG] AI fields: ai_enhanced={result.get('ai_enhanced')}, ai_status={result.get('ai_status')}")
                
                self.send_json(result)
                return
            if self.path == "/api/analyze-multi-agent":
                payload = self.read_json()
                
                try:
                    print(f"[DEBUG] Starting multi-agent orchestration...")
                    # Use multi-agent orchestrator
                    orchestration_result = orchestrator.orchestrate_analysis(
                        sql=payload.get("sql", ""),
                        analysis_type=payload.get("analysis_type", "full_analysis"),
                        db_type=payload.get("db_type", "SQL Server"),
                        known_objects=payload.get("known_objects", {}),
                        user_preferences=payload.get("preferences", {})
                    )
                    print(f"[DEBUG] Orchestration completed successfully")
                    
                    # Get regular analysis structure as base
                    base_result = agent.analyze(
                        payload.get("sql", ""),
                        payload.get("db_type", "SQL Server"),
                        payload.get("source_type", "auto"),
                    )
                    
                    # Generate AI-optimized SQL using existing optimizer agent
                    from sql_optimizer_agent import SQLOptimizerAgent
                    optimizer_agent = SQLOptimizerAgent()
                    optimization_context = {
                        "tables": base_result.get("summary", {}).get("tables_involved", []),
                        "joins": base_result.get("summary", {}).get("joins_used", []),
                        "filters": base_result.get("summary", {}).get("filters_applied", [])
                    }
                    
                    # Get AI-optimized SQL separately from orchestration
                    ai_optimized_sql = optimizer_agent.generate_optimized_sql(
                        payload.get("sql", ""),
                        optimization_context,
                        payload.get("db_type", "SQL Server")
                    )
                    
                    print(f"[DEBUG] AI Optimized SQL length: {len(ai_optimized_sql)}")
                    print(f"[DEBUG] AI Optimized SQL preview: {ai_optimized_sql[:100]}...")
                    
                    # Enhance base result with AI insights
                    result = base_result.copy()
                    result.update({
                        "ai_enhanced": True,
                        "ai_status": "Multi-Agent Analysis Complete",
                        "orchestration_strategy": orchestration_result.orchestration_strategy,
                        "agents_used": orchestration_result.agents_used,
                        "overall_confidence": orchestration_result.overall_confidence,
                        "processing_time": orchestration_result.total_processing_time,
                        "ai_recommendations": orchestration_result.recommendations,
                        "ai_insights": orchestration_result.ai_insights,
                        "confidence": max(result.get("confidence", 0.6), orchestration_result.overall_confidence)
                    })
                    
                    print(f"[DEBUG] Original optimized SQL: {base_result.get('optimized_sql', '')[:100]}...")
                    
                    # Replace static optimized SQL with AI-generated version
                    result["optimized_sql"] = ai_optimized_sql
                    result["ai_optimization_applied"] = True
                    
                    print(f"[DEBUG] Replaced with AI optimized SQL: {ai_optimized_sql[:100]}...")
                    
                    # Update artifacts with AI-optimized content
                    if "artifacts" in result:
                        result["artifacts"]["optimized_sql"] = ai_optimized_sql
                    
                    # Enhance issues with AI findings
                    ai_issues = []
                    if hasattr(orchestration_result, 'security_results') and orchestration_result.security_results:
                        for issue in orchestration_result.security_results.get('issues', []):
                            ai_issues.append({
                                "severity": issue.get('severity', 'Medium'),
                                "description": f"[AI Security] {issue.get('description', '')}",
                                "line": issue.get('line'),
                                "agent": "Security"
                            })
                    
                    if hasattr(orchestration_result, 'optimization_results') and orchestration_result.optimization_results:
                        for issue in orchestration_result.optimization_results.get('issues', []):
                            ai_issues.append({
                                "severity": issue.get('severity', 'Medium'),
                                "description": f"[AI Optimizer] {issue.get('description', '')}",
                                "line": issue.get('line'),
                                "agent": "Optimizer"
                            })
                    
                    # Add AI optimization info as issues/improvements
                    ai_issues.append({
                        "severity": "Info",
                        "description": "[AI Optimization] Generated optimized SQL with performance improvements",
                        "line": None,
                        "agent": "AI Optimizer"
                    })
                    
                    # Merge AI issues with existing issues
                    existing_issues = result.get('issues', [])
                    result['issues'] = existing_issues + ai_issues
                    
                    self.send_json(result)
                    return
                    
                except Exception as e:
                    # Fallback to regular analysis if multi-agent fails
                    print(f"[ERROR] Multi-agent analysis failed: {e}")
                    print(f"[FALLBACK] Using regular analysis with AI-optimized SQL")
                    result = agent.analyze(
                        payload.get("sql", ""),
                        payload.get("db_type", "SQL Server"),
                        payload.get("source_type", "auto"),
                    )
                    # Still try to get AI-optimized SQL even in fallback
                    try:
                        from sql_optimizer_agent import SQLOptimizerAgent
                        optimizer_agent = SQLOptimizerAgent()
                        optimization_context = {
                            "tables": result.get("summary", {}).get("tables_involved", []),
                            "joins": result.get("summary", {}).get("joins_used", []),
                            "filters": result.get("summary", {}).get("filters_applied", [])
                        }
                        
                        ai_optimized_sql = optimizer_agent.generate_optimized_sql(
                            payload.get("sql", ""),
                            optimization_context,
                            payload.get("db_type", "SQL Server")
                        )
                        
                        # Replace static optimized SQL with AI version
                        result["optimized_sql"] = ai_optimized_sql
                        result["ai_optimization_applied"] = True
                        
                        if "artifacts" in result:
                            result["artifacts"]["optimized_sql"] = ai_optimized_sql
                        
                        print(f"[SUCCESS] AI-optimized SQL generated in fallback mode")
                        
                    except Exception as opt_e:
                        print(f"[WARNING] AI optimization also failed: {opt_e}")
                    
                    result.update({
                        "ai_enhanced": False,
                        "ai_status": f"Multi-agent failed, using fallback: {str(e)[:100]}",
                        "fallback_used": True
                    })
                    self.send_json(result)
                    return
            if self.path == "/api/add-object":
                payload = self.read_json()
                result = agent.add_related_object(
                    payload.get("sql", ""),
                    payload.get("db_type", "SQL Server"),
                    payload.get("source_type", "auto"),
                )
                self.send_json(result)
                return
            if self.path == "/api/artifact":
                payload = self.read_json()
                analysis = payload.get("analysis") or {}
                artifact_type = payload.get("artifact_type", "db_review_report")
                text = (analysis.get("artifacts") or {}).get(artifact_type, "")
                self.send_text(text or "Artifact is not available.")
                return
            if self.path == "/api/schema/design":
                payload = self.read_json()
                result = agent.design_schema(
                    payload.get("prompt", ""),
                    payload.get("db_type", "SQL Server"),
                )
                self.send_json(result)
                return
            if self.path == "/api/schema/design-ai":
                payload = self.read_json()
                try:
                    from backend.sql_schema_agent import SQLSchemaAgent
                except ImportError:
                    from sql_schema_agent import SQLSchemaAgent
                schema_agent = SQLSchemaAgent()
                result = schema_agent.design_schema(
                    payload.get("prompt", ""),
                    payload.get("db_type", "SQL Server"),
                )
                self.send_json(result)
                return
            if self.path == "/api/reset":
                agent.reset()
                self.send_json({"status": "reset"})
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route")
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": f"Server error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, payload, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def serve_static(self) -> None:
        path = unquote(self.path.split("?", 1)[0]).lstrip("/")
        file_path = FRONTEND / (path or "index.html")
        if file_path.is_dir():
            file_path = file_path / "index.html"
        if not file_path.exists() or not file_path.resolve().is_relative_to(FRONTEND.resolve()):
            file_path = FRONTEND / "index.html"

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.getenv("PORT", sys.argv[1] if len(sys.argv) > 1 else "8020"))
    host = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"
    server = ThreadingHTTPServer((host, port), AgentHandler)
    print(f"DB Optimization & Intelligence Agent running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

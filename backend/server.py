from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

try:
    from backend.sql_agent import SqlIntelligenceAgent
except ImportError:  # Allows running from inside the backend folder.
    from sql_agent import SqlIntelligenceAgent


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
agent = SqlIntelligenceAgent()


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "DBOptimizationAgentHTTP/1.0"

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json({"status": "ok", "agent": "DB Optimization & Intelligence Agent"})
            return
        if self.path == "/api/history":
            self.send_json(agent.get_history())
            return
        if self.path == "/api/memory":
            self.send_json(agent.get_memory())
            return
        self.serve_static()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/analyze":
                payload = self.read_json()
                result = agent.analyze(
                    payload.get("sql", ""),
                    payload.get("db_type", "SQL Server"),
                    payload.get("source_type", "auto"),
                )
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

"""
AI-Powered Schema Agent
Generates schema design using Groq AI based on plain English prompt or DDL
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from agent_config import sql_agent_system
from groq_client import groq_client


class SQLSchemaAgent:
    """AI-powered schema design agent using Groq"""

    def __init__(self):
        self.config = sql_agent_system.get_agent_config("sql_parser")

    def design_schema(self, prompt: str, db_type: str = "SQL Server") -> Dict[str, Any]:
        """Generate schema design using AI"""

        ai_result = self._call_ai(prompt, db_type)

        tables = ai_result.get("tables", [])
        relationships = ai_result.get("relationships", [])
        quality_review = ai_result.get("quality_review", [])

        ddl = self._build_ddl(tables, relationships, db_type)
        rollback = self._build_rollback(tables, db_type)
        erd = self._build_erd(tables, relationships)
        report = self._build_report(tables, relationships, quality_review, ddl, rollback)

        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "db_type": db_type,
            "ai_enhanced": True,
            "ai_status": "AI Schema Design Complete",
            "tables": tables,
            "relationships": relationships,
            "quality_review": quality_review,
            "migration_script": ddl,
            "rollback_script": rollback,
            "erd_summary": erd,
            "schema_review_report": report,
            "artifacts": {
                "ddl_script": ddl,
                "rollback_script": rollback,
                "erd_summary": erd,
                "schema_review_report": report,
            },
        }

    def suggest_db_name(self, prompt: str) -> str:
        """Extract a clean database name from the user prompt using AI"""
        system_message = "You are a database naming assistant. Respond with valid JSON only."
        user_prompt = f"""Given this database requirement, suggest a short PascalCase database name (no spaces, end with DB).
Requirement: {prompt}
Respond with exactly: {{"db_name": "SuggestedNameDB"}}"""
        try:
            result = groq_client.call_ai(system_message, user_prompt, timeout=10)
            name = result.get("db_name", "").strip()
            # Sanitize: only alphanumeric and underscores
            name = re.sub(r"[^a-zA-Z0-9_]", "", name)
            return name if name else "NewDatabaseDB"
        except Exception:
            return "NewDatabaseDB"

    def _call_ai(self, prompt: str, db_type: str) -> Dict[str, Any]:

        system_message = """You are an expert database architect. Design optimal database schemas based on requirements.
Always respond with valid JSON only. No markdown, no explanation outside JSON."""

        user_prompt = f"""Design a database schema for the following requirement:

{prompt}

Target database: {db_type}

First, check if the input is a valid database requirement written in plain English.
If the input is random characters, gibberish, or completely unrelated to any database or software system, respond with exactly:
{{"error": "Invalid input. Please describe your database requirement in plain English."}}

Otherwise respond with this exact JSON structure:
{{
    "tables": [
        {{
            "name": "TableName",
            "columns": [
                {{"name": "ColName", "type": "DATATYPE", "nullable": false, "role": "PK|FK|UQ|"}}
            ]
        }}
    ],
    "relationships": [
        {{"from": "ChildTable", "to": "ParentTable", "column": "ForeignKeyCol", "type": "many-to-one"}}
    ],
    "quality_review": [
        {{"severity": "High|Medium|Low", "title": "finding title", "detail": "explanation"}}
    ]
}}

Rules:
- Every table must have a primary key column (role: "PK")
- Include CreatedAt DATETIME2 NOT NULL audit column on every table
- Use proper data types for {db_type}
- Infer all realistic relationships from the requirements
- Quality review should flag any design concerns"""

        try:
            result = groq_client.call_ai(system_message, user_prompt, timeout=30)
            tables = result.get("tables", [])
            relationships = result.get("relationships", [])
            quality_review = result.get("quality_review", [])

            if result.get("error"):
                raise ValueError(result["error"])

            if not tables:
                raise ValueError("Invalid input. Please describe your database requirement in plain English. Example: 'Design a hospital system with patients, doctors and appointments.'")

            return {"tables": tables, "relationships": relationships, "quality_review": quality_review}

        except Exception as e:
            raise Exception(f"AI schema design failed: {str(e)}")

    def _build_ddl(self, tables, relationships, db_type: str) -> str:
        is_pg = db_type == "PostgreSQL"
        is_oracle = db_type == "Oracle"
        is_mssql = not is_pg and not is_oracle

        if is_mssql:
            lines = [
                f"-- AI-Generated DDL Script for {db_type}",
                "-- TODO: Replace YourDatabaseName with your actual database name",
                "USE [YourDatabaseName];",
                "GO",
                "",
            ]
        else:
            lines = [f"-- AI-Generated DDL Script for {db_type}", ""]

        for table in tables:
            tname = f"[{table['name']}]" if is_mssql else f"\"{table['name']}\""
            lines.append(f"CREATE TABLE {tname} (")
            col_lines = []
            for col in table["columns"]:
                null = "NULL" if col.get("nullable") else "NOT NULL"
                ctype = col["type"]
                # Normalize DATETIME2 per platform
                if is_pg:
                    ctype = re.sub(r"(?i)\bDATETIME2\b", "TIMESTAMP", ctype)
                elif is_oracle:
                    ctype = re.sub(r"(?i)\bDATETIME2\b", "TIMESTAMP", ctype)
                    ctype = re.sub(r"(?i)\bVARCHAR\b", "VARCHAR2", ctype)
                    ctype = re.sub(r"(?i)\bBIT\b", "NUMBER(1)", ctype)

                if col.get("role") == "PK":
                    if is_mssql:
                        col_lines.append(f"  {col['name']} INT IDENTITY(1,1) NOT NULL PRIMARY KEY")
                    elif is_pg:
                        col_lines.append(f"  {col['name']} SERIAL NOT NULL PRIMARY KEY")
                    else:  # Oracle
                        col_lines.append(f"  {col['name']} NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL PRIMARY KEY")
                else:
                    col_lines.append(f"  {col['name']} {ctype} {null}")
            lines.append(",\n".join(col_lines))
            lines.append(");")
            if is_mssql:
                lines.append("GO")
            lines.append("")

        for rel in relationships:
            parent_pk = next(
                (col["name"] for t in tables if t["name"] == rel["to"] for col in t["columns"] if col.get("role") == "PK"),
                f"{rel['to']}Id"
            )
            if is_mssql:
                lines.append(f"ALTER TABLE [{rel['from']}] ADD CONSTRAINT FK_{rel['from']}_{rel['to']} FOREIGN KEY ({rel['column']}) REFERENCES [{rel['to']}]({parent_pk});")
                lines.append("GO")
            else:
                lines.append(f"ALTER TABLE \"{rel['from']}\" ADD CONSTRAINT FK_{rel['from']}_{rel['to']} FOREIGN KEY ({rel['column']}) REFERENCES \"{rel['to']}\"({parent_pk});")
        lines.append("")

        for rel in relationships:
            if is_pg:
                lines.append(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS IX_{rel['from']}_{rel['column']} ON \"{rel['from']}\" ({rel['column']});")
            elif is_oracle:
                lines.append(f"CREATE INDEX IX_{rel['from']}_{rel['column']} ON \"{rel['from']}\" ({rel['column']});")
            else:
                lines.append(f"CREATE INDEX IX_{rel['from']}_{rel['column']} ON [{rel['from']}] ({rel['column']});")
                lines.append("GO")
        return "\n".join(lines)

    def _build_rollback(self, tables, db_type: str) -> str:
        is_pg = db_type == "PostgreSQL"
        is_oracle = db_type == "Oracle"
        is_mssql = not is_pg and not is_oracle

        if is_mssql:
            lines = [
                f"-- Rollback Script for {db_type}",
                "-- TODO: Replace YourDatabaseName with your actual database name",
                "USE [YourDatabaseName];",
                "GO",
                "",
            ]
        else:
            lines = [f"-- Rollback Script for {db_type}", ""]

        for table in reversed(tables):
            if is_pg:
                lines.append(f"DROP TABLE IF EXISTS \"{table['name']}\" CASCADE;")
            elif is_oracle:
                lines.append(f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE \"{table['name']}\" CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;")
                lines.append("/")
            else:
                lines.append(f"DROP TABLE IF EXISTS [{table['name']}];")
                lines.append("GO")
        return "\n".join(lines)

    def _build_erd(self, tables, relationships) -> str:
        lines = ["erDiagram"]
        for rel in relationships:
            lines.append(f"    {rel['to']} ||--o{{ {rel['from']} : has")
        for table in tables:
            lines.append(f"    {table['name']} {{")
            for col in table["columns"]:
                safe_type = re.sub(r"[^a-zA-Z0-9_]", "_", col["type"])
                lines.append(f"        {safe_type} {col['name']}")
            lines.append("    }")
        return "\n".join(lines)

    def _build_report(self, tables, relationships, quality_review, ddl, rollback) -> str:
        rel_lines = [f"- {r['from']}.{r['column']} -> {r['to']}" for r in relationships] or ["- None inferred"]
        return "\n".join([
            "# AI DB Schema Agent Review",
            "",
            f"- Tables designed: {len(tables)}",
            f"- Relationships inferred: {len(relationships)}",
            "",
            "## Tables",
            *[f"- {t['name']}: {len(t['columns'])} columns" for t in tables],
            "",
            "## Relationships",
            *rel_lines,
            "",
            "## Quality Review",
            *[f"- [{i['severity']}] {i['title']}: {i['detail']}" for i in quality_review],
            "",
            "## Migration Script",
            "```sql",
            ddl,
            "```",
            "",
            "## Rollback Script",
            "```sql",
            rollback,
            "```",
        ])



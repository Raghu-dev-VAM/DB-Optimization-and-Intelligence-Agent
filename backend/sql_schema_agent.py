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
        migration_plan = self._build_migration_plan(tables, relationships)

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
                "migration_plan": migration_plan,
            },
        }

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
        lines = [
            f"-- AI-Generated Migration Script for {db_type}",
            "-- TODO: Replace YourDatabaseName with your actual database name",
            "USE [YourDatabaseName];",
            "GO",
            "",
        ]
        for table in tables:
            safe_name = f"[{table['name']}]"
            lines.append(f"CREATE TABLE {safe_name} (")
            col_lines = []
            for col in table["columns"]:
                null = "NULL" if col.get("nullable") else "NOT NULL"
                if col.get("role") == "PK":
                    # Inject IDENTITY and PRIMARY KEY for PK columns
                    base_type = re.sub(r"(?i)\bint\b", "INT", col["type"])
                    col_lines.append(f"  {col['name']} {base_type} IDENTITY(1,1) {null} PRIMARY KEY")
                else:
                    col_lines.append(f"  {col['name']} {col['type']} {null}")
            lines.append(",\n".join(col_lines))
            lines.append(");")  
            lines.append("GO")
            lines.append("")
        for rel in relationships:
            # Find the actual PK column name from the parent table
            parent_pk = next(
                (col["name"] for t in tables if t["name"] == rel["to"] for col in t["columns"] if col.get("role") == "PK"),
                f"{rel['to']}Id"  # fallback
            )
            lines.append(
                f"ALTER TABLE [{rel['from']}] ADD CONSTRAINT FK_{rel['from']}_{rel['to']} "
                f"FOREIGN KEY ({rel['column']}) REFERENCES [{rel['to']}]({parent_pk});"
            )
            lines.append("GO")
        lines.append("")
        for rel in relationships:
            lines.append(f"CREATE INDEX IX_{rel['from']}_{rel['column']} ON [{rel['from']}] ({rel['column']});")
            lines.append("GO")
        return "\n".join(lines)

    def _build_rollback(self, tables, db_type: str) -> str:
        lines = [
            f"-- Rollback Script for {db_type}",
            "-- TODO: Replace YourDatabaseName with your actual database name",
            "USE [YourDatabaseName];",
            "GO",
            "",
        ]
        for table in reversed(tables):
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

    def _build_migration_plan(self, tables, relationships) -> str:
        return "\n".join([
            "# AI-Generated Migration Plan",
            "",
            "1. Review generated DDL and naming standards.",
            "2. Deploy tables before foreign keys.",
            "3. Deploy indexes after initial load for large tables.",
            "4. Validate impacted stored procedures, views, reports, APIs, and jobs.",
            "5. Keep rollback script ready for the same deployment window.",
            "",
            f"Tables to deploy: {len(tables)}",
            f"Relationships to enforce: {len(relationships)}",
        ])

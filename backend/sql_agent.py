from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


SQL_KEYWORDS = {
    "select",
    "from",
    "where",
    "join",
    "inner",
    "left",
    "right",
    "full",
    "cross",
    "on",
    "and",
    "or",
    "group",
    "by",
    "order",
    "insert",
    "update",
    "delete",
    "create",
    "alter",
    "procedure",
    "proc",
    "function",
    "view",
    "table",
    "exec",
    "execute",
    "into",
    "values",
    "set",
    "declare",
    "begin",
    "end",
}


@dataclass
class DbObject:
    object_id: str
    name: str
    object_type: str
    db_type: str
    sql: str
    created_at: str
    references: list[str] = field(default_factory=list)
    missing_references: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)


class SqlIntelligenceAgent:
    def __init__(self) -> None:
        self.objects: dict[str, DbObject] = {}
        self.history: list[dict[str, Any]] = []

    def analyze(self, sql: str, db_type: str = "SQL Server", source_type: str = "auto") -> dict[str, Any]:
        cleaned = normalize_sql(sql)
        if not cleaned:
            raise ValueError("Paste SQL or upload a .sql file before analysis.")

        object_type = classify_sql(cleaned, source_type)
        name = extract_object_name(cleaned, object_type)
        tables = extract_tables(cleaned)
        joins = extract_joins(cleaned)
        filters = extract_filters(cleaned)
        references = extract_references(cleaned)
        known_reference_names = {obj.name.lower(): obj.name for obj in self.objects.values()}
        missing_references = [ref for ref in references if ref.lower() not in known_reference_names]

        object_id = slugify(name)
        db_object = DbObject(
            object_id=object_id,
            name=name,
            object_type=object_type,
            db_type=db_type,
            sql=cleaned,
            created_at=datetime.now().isoformat(timespec="seconds"),
            references=references,
            missing_references=missing_references,
            tables=tables,
        )
        self.objects[object_id] = db_object

        findings = detect_findings(cleaned, object_type, tables, joins, filters, references, missing_references)
        suggestions = build_suggestions(cleaned, db_type, object_type, tables, joins, filters, findings)
        metrics = estimate_metrics(cleaned, object_type, findings, joins, tables)
        optimized_sql = optimize_sql(cleaned, db_type, object_type, findings, suggestions)
        index_scripts = build_index_scripts(db_type, tables, filters, joins, findings)
        dependency_map = self.dependency_map()
        impact = build_impact(object_type, name, tables, references, missing_references, findings, dependency_map)
        execution_plan = build_execution_plan(cleaned, findings, joins, tables, metrics)
        report = build_report(name, object_type, db_type, findings, suggestions, impact, execution_plan, optimized_sql, index_scripts)

        result = {
            "analysis_id": f"AN-{len(self.history) + 1:04d}",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "object": asdict(db_object),
            "summary": {
                "object_name": name,
                "object_type": object_type,
                "db_type": db_type,
                "execution_type": "Read/Write" if has_write_operation(cleaned) and "select" in cleaned.lower() else ("Write" if has_write_operation(cleaned) else "Read Only"),
                "tables_involved": tables,
                "joins_used": joins,
                "filters_applied": filters,
                "group_by": bool(re.search(r"\bgroup\s+by\b", cleaned, re.I)),
                "order_by": bool(re.search(r"\border\s+by\b", cleaned, re.I)),
                "references": references,
                "missing_references": missing_references,
                "explanation": explain_sql(cleaned, object_type, name, tables, joins, filters, references),
            },
            "metrics": metrics,
            "findings": findings,
            "suggestions": suggestions,
            "impact": impact,
            "execution_plan": execution_plan,
            "optimized_sql": optimized_sql,
            "index_scripts": index_scripts,
            "dependency_map": dependency_map,
            "artifacts": {
                "optimized_sql": optimized_sql,
                "index_script": "\n\n".join(index_scripts) or "-- No index script generated.",
                "execution_plan_analysis": execution_plan_to_markdown(execution_plan),
                "db_review_report": report,
                "comparison_report": comparison_report(cleaned, optimized_sql, findings, suggestions),
                "test_data_generator": test_data_generator(db_type, tables),
            },
        }
        self.history.insert(0, result)
        self.history = self.history[:25]
        return result

    def add_related_object(self, sql: str, db_type: str = "SQL Server", source_type: str = "auto") -> dict[str, Any]:
        return self.analyze(sql, db_type, source_type)

    def dependency_map(self) -> dict[str, Any]:
        nodes = []
        edges = []
        known = {obj.name.lower(): obj for obj in self.objects.values()}

        for obj in self.objects.values():
            nodes.append({"id": obj.name, "type": obj.object_type, "status": "known"})
            for table in obj.tables:
                nodes.append({"id": table, "type": "Table", "status": "referenced"})
                edges.append({"from": obj.name, "to": table, "kind": "uses"})
            for ref in obj.references:
                status = "known" if ref.lower() in known else "missing"
                nodes.append({"id": ref, "type": "Stored Procedure", "status": status})
                edges.append({"from": obj.name, "to": ref, "kind": "calls"})

        deduped_nodes = {node["id"].lower(): node for node in nodes}
        return {"nodes": list(deduped_nodes.values()), "edges": edges}

    def get_history(self) -> list[dict[str, Any]]:
        return self.history

    def get_memory(self) -> dict[str, Any]:
        return {
            "objects": [asdict(obj) for obj in self.objects.values()],
            "dependency_map": self.dependency_map(),
            "history_count": len(self.history),
        }

    def design_schema(self, prompt: str, db_type: str = "SQL Server") -> dict[str, Any]:
        text = normalize_sql(prompt)
        if not text:
            raise ValueError("Describe the schema requirement or paste existing DDL.")

        if re.search(r"\bcreate\s+table\b", text, re.I):
            tables = parse_ddl_tables(text)
        else:
            tables = infer_schema_from_prompt(text)

        relationships = infer_relationships(tables)
        review = review_schema(tables, relationships)
        ddl = build_schema_ddl(tables, relationships, db_type)
        rollback = build_schema_rollback(tables, db_type)
        impact = self.schema_impact(tables)
        erd = build_erd_summary(tables, relationships)
        report = build_schema_report(tables, relationships, review, impact, ddl, rollback)

        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "db_type": db_type,
            "tables": tables,
            "relationships": relationships,
            "quality_review": review,
            "migration_script": ddl,
            "rollback_script": rollback,
            "impact": impact,
            "erd_summary": erd,
            "schema_review_report": report,
            "artifacts": {
                "ddl_script": ddl,
                "rollback_script": rollback,
                "erd_summary": erd,
                "schema_review_report": report,
                "migration_plan": build_migration_plan(tables, relationships, impact),
            },
        }

    def schema_impact(self, tables: list[dict[str, Any]]) -> dict[str, Any]:
        table_names = {table["name"].lower() for table in tables}
        impacted = []
        for obj in self.objects.values():
            if any(table.lower().split(".")[-1] in table_names or table.lower() in table_names for table in obj.tables):
                impacted.append({"object": obj.name, "type": obj.object_type, "tables": obj.tables})
        return {
            "impacted_objects": impacted,
            "risk_level": "High" if impacted else "Medium",
            "notes": "Schema changes should be checked against stored procedures, views, APIs, reports, and jobs already in object memory.",
        }


def normalize_sql(sql: str) -> str:
    if not isinstance(sql, str):
        sql = json.dumps(sql, indent=2)
    return "\n".join(line.rstrip() for line in sql.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def classify_sql(sql: str, source_type: str) -> str:
    if source_type and source_type != "auto":
        return source_type
    lower = sql.lower()
    if re.search(r"\b(create|alter)\s+(procedure|proc)\b", lower):
        return "Stored Procedure"
    if re.search(r"\b(create|alter)\s+function\b", lower):
        return "Function"
    if re.search(r"\b(create|alter)\s+view\b", lower):
        return "View"
    if re.search(r"\b(create|alter)\s+table\b", lower):
        return "DDL Script"
    if re.search(r"\b(insert|update|delete|merge)\b", lower):
        return "DML Script"
    if re.search(r"\bselect\b", lower):
        return "SQL Query"
    return "SQL Script"


def extract_object_name(sql: str, object_type: str) -> str:
    if object_type == "Stored Procedure":
        match = re.search(r"\b(?:create|alter)\s+(?:procedure|proc)\s+([\[\]\w.]+)", sql, re.I)
    elif object_type == "Function":
        match = re.search(r"\b(?:create|alter)\s+function\s+([\[\]\w.]+)", sql, re.I)
    elif object_type == "View":
        match = re.search(r"\b(?:create|alter)\s+view\s+([\[\]\w.]+)", sql, re.I)
    elif object_type == "DDL Script":
        match = re.search(r"\b(?:create|alter)\s+table\s+([\[\]\w.]+)", sql, re.I)
    else:
        match = None
    return clean_identifier(match.group(1)) if match else f"{object_type} {datetime.now().strftime('%H%M%S')}"


def extract_tables(sql: str) -> list[str]:
    patterns = [
        r"\bfrom\s+([\[\]\w.#]+)",
        r"\bjoin\s+([\[\]\w.#]+)",
        r"\bupdate\s+([\[\]\w.#]+)",
        r"\binsert\s+into\s+([\[\]\w.#]+)",
        r"\bdelete\s+from\s+([\[\]\w.#]+)",
    ]
    tables: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, sql, re.I):
            table = clean_identifier(match.group(1))
            if table and table.lower() not in SQL_KEYWORDS and table not in tables:
                tables.append(table)
    return tables


def extract_joins(sql: str) -> list[dict[str, str]]:
    joins = []
    pattern = r"\b((?:inner|left|right|full|cross)\s+join|join)\s+([\[\]\w.#]+)(?:\s+\w+)?\s+on\s+(.+?)(?=\b(?:inner|left|right|full|cross)?\s*join\b|\bwhere\b|\bgroup\s+by\b|\border\s+by\b|$)"
    for match in re.finditer(pattern, sql, re.I | re.S):
        joins.append({
            "type": " ".join(match.group(1).upper().split()),
            "table": clean_identifier(match.group(2)),
            "condition": " ".join(match.group(3).split()),
        })
    return joins


def extract_filters(sql: str) -> list[str]:
    where = re.search(r"\bwhere\b(.+?)(?=\bgroup\s+by\b|\border\s+by\b|\bhaving\b|$)", sql, re.I | re.S)
    if not where:
        return []
    clause = " ".join(where.group(1).split())
    pieces = re.split(r"\s+\bAND\b\s+|\s+\bOR\b\s+", clause, flags=re.I)
    return [piece.strip(" ;") for piece in pieces if piece.strip(" ;")]


def extract_references(sql: str) -> list[str]:
    refs = []
    for match in re.finditer(r"\b(?:exec|execute)\s+(?!sp_executesql\b)([\[\]\w.]+)", sql, re.I):
        ref = clean_identifier(match.group(1))
        if ref and ref.lower() not in {"exec", "execute"} and ref not in refs:
            refs.append(ref)
    return refs


def clean_identifier(value: str) -> str:
    return value.strip().strip(";").replace("[", "").replace("]", "")


def detect_findings(
    sql: str,
    object_type: str,
    tables: list[str],
    joins: list[dict[str, str]],
    filters: list[str],
    references: list[str],
    missing_references: list[str],
) -> list[dict[str, Any]]:
    lower = sql.lower()
    findings: list[dict[str, Any]] = []

    def add(title: str, severity: str, category: str, detail: str, evidence: str) -> None:
        findings.append({"title": title, "severity": severity, "category": category, "detail": detail, "evidence": evidence})

    if re.search(r"\bselect\s+\*", lower):
        add("SELECT * usage", "Medium", "Column Selection", "Selecting every column increases I/O, memory grants, and network payload.", "SELECT *")
    if " cursor " in f" {lower} " or re.search(r"\bdeclare\s+\w+\s+cursor\b", lower):
        add("Cursor / row-by-row processing", "High", "Stored Procedure", "Cursor logic is often slow for large row counts and should be replaced with set-based operations where possible.", "CURSOR")
    if re.search(r"\bwhile\b", lower):
        add("Loop-based processing", "Medium", "Stored Procedure", "WHILE loops can create RBAR behavior and should be reviewed for set-based rewrites.", "WHILE")
    if re.search(r"\b#\w+", sql):
        add("Temp table usage", "Medium", "TempDB", "Temp tables can be valid, but repeated writes and missing temp-table indexes can pressure TempDB.", "#temp")
    if "sp_executesql" in lower or re.search(r"\bexec\s*\(@", lower):
        add("Dynamic SQL", "Medium", "Security / Plan Cache", "Dynamic SQL needs parameterization and careful plan-cache handling.", "EXEC / sp_executesql")
    if references:
        severity = "High" if missing_references else "Low"
        add("Nested stored procedure calls", severity, "Dependency", "Referenced procedures should be analyzed to complete impact and performance review.", ", ".join(references))
    if missing_references:
        add("Missing referenced object definitions", "High", "Dependency", "Paste referenced procedures/functions so the agent can complete downstream analysis.", ", ".join(missing_references))
    if filters and any(re.search(r"\b\w+\s*\([^)]*\)\s*(=|>|<|like)", item, re.I) for item in filters):
        add("Function in WHERE predicate", "High", "Sargability", "Functions around filtered columns can prevent index seeks.", "; ".join(filters))
    if filters and any(re.search(r"\blike\s+'%", item, re.I) for item in filters):
        add("Leading wildcard LIKE", "Medium", "Sargability", "Leading wildcards usually prevent index seeks.", "; ".join(filters))
    if re.search(r"\border\s+by\b", lower) and not re.search(r"\btop\s+\(?\d+|\boffset\b", lower):
        add("Sort operation risk", "Medium", "Execution Plan", "ORDER BY without a supporting index can introduce expensive sort operators.", "ORDER BY")
    if joins and len(joins) >= 3:
        add("Heavy join graph", "Medium", "Join Strategy", "Multiple joins increase risk of bad cardinality estimates and high logical reads.", f"{len(joins)} joins")
    if " nolock" in lower:
        add("NOLOCK hint", "Medium", "Correctness", "NOLOCK can return dirty, duplicated, or missing rows.", "NOLOCK")
    if object_type == "Stored Procedure" and re.search(r"@\w+", sql) and filters:
        add("Parameter sniffing risk", "Medium", "Plan Stability", "Procedure parameters in selective filters may produce unstable plans across different parameter values.", ", ".join(re.findall(r"@\w+", sql)[:5]))
    if has_write_operation(sql) and not re.search(r"\btry\b.+\bcatch\b", lower, re.S):
        add("Missing TRY/CATCH around write logic", "Medium", "Reliability", "Write procedures should usually protect transactions with error handling.", "No TRY/CATCH found")
    if has_write_operation(sql) and re.search(r"\bbegin\s+tran", lower) and not re.search(r"\brollback\b", lower):
        add("Transaction rollback not visible", "High", "Reliability", "Explicit transactions should include rollback handling.", "BEGIN TRAN")
    if tables and not filters and re.search(r"\bselect\b", lower):
        add("Unfiltered read", "High", "I/O", "Reading tables without predicates can cause full scans on large objects.", ", ".join(tables))
    if not findings:
        add("No major rule-based issue detected", "Low", "Baseline", "The query still needs validation against actual execution plans and production statistics.", "Static review only")

    return findings


def build_suggestions(
    sql: str,
    db_type: str,
    object_type: str,
    tables: list[str],
    joins: list[dict[str, str]],
    filters: list[str],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    titles = {finding["title"] for finding in findings}
    suggestions: list[dict[str, Any]] = []

    def add(title: str, impact: str, effort: str, recommendation: str, script: str = "") -> None:
        suggestions.append({"title": title, "impact": impact, "effort": effort, "recommendation": recommendation, "script": script})

    if "SELECT * usage" in titles:
        add("Project required columns only", "Medium", "Low", "Replace SELECT * with explicit columns used by the caller.")
    if "Cursor / row-by-row processing" in titles:
        add("Replace cursor with set-based logic", "High", "High", "Rewrite cursor operations as a single UPDATE/INSERT/MERGE or staged set operation.")
    if "Function in WHERE predicate" in titles:
        add("Make predicates sargable", "High", "Medium", "Move functions away from indexed columns or add persisted computed columns where appropriate.")
    if "Parameter sniffing risk" in titles:
        hint = "OPTION (RECOMPILE)" if db_type == "SQL Server" else "Use plan-aware statistics and bind-aware review for the selected platform."
        add("Stabilize parameter-sensitive plans", "Medium", "Medium", f"Compare plans for small and large parameter values. Consider {hint} for highly skewed workloads.")
    if tables and (filters or joins):
        add("Create supporting composite indexes", "High", "Medium", "Index filter columns first, then join columns, then INCLUDE frequently selected output columns.")
    if "Temp table usage" in titles:
        add("Review TempDB strategy", "Medium", "Medium", "Index temp tables after load when they are joined or filtered repeatedly; drop large temp tables once no longer needed.")
    if "Missing referenced object definitions" in titles:
        add("Paste missing dependencies", "High", "Low", "Add referenced stored procedure/function definitions into the dependency workspace for complete analysis.")
    if "Missing TRY/CATCH around write logic" in titles:
        add("Add defensive error handling", "Medium", "Medium", "Wrap write operations in TRY/CATCH with rollback and error rethrow/logging.")
    if "Sort operation risk" in titles:
        add("Support ORDER BY with index order", "Medium", "Medium", "Add index key order matching WHERE and ORDER BY columns when this sort is on a hot path.")
    if not suggestions:
        add("Validate against actual execution plan", "Medium", "Low", "Capture actual execution plan, row counts, logical reads, CPU, and duration before deployment.")

    return suggestions


def estimate_metrics(sql: str, object_type: str, findings: list[dict[str, Any]], joins: list[dict[str, str]], tables: list[str]) -> dict[str, Any]:
    risk_points = sum({"High": 18, "Medium": 9, "Low": 3}.get(item["severity"], 4) for item in findings)
    length_factor = min(len(sql) // 250, 20)
    join_factor = len(joins) * 8
    table_factor = len(tables) * 5
    score = min(100, 18 + risk_points + length_factor + join_factor + table_factor)
    improvement = min(72, max(12, score // 2))
    return {
        "execution_time_ms": 150 + score * 19,
        "cpu_usage_pct": min(95, 22 + score // 2),
        "logical_reads": 2800 + score * 470,
        "rows_returned": 1200 + len(tables) * 640,
        "index_usage_pct": max(18, 88 - score // 2),
        "query_cost": round(8.5 + score * 0.62, 1),
        "risk_score": score,
        "improvement_potential_pct": improvement,
        "risk_level": "High" if score >= 70 else "Medium" if score >= 42 else "Low",
        "confidence": "Static analysis estimate. Confirm with actual execution metrics.",
    }


def optimize_sql(sql: str, db_type: str, object_type: str, findings: list[dict[str, Any]], suggestions: list[dict[str, Any]]) -> str:
    optimized = sql
    if any(item["title"] == "SELECT * usage" for item in findings):
        optimized = re.sub(r"\bselect\s+\*", "SELECT /* TODO: list required columns */", optimized, flags=re.I)
    if any(item["title"] == "NOLOCK hint" for item in findings):
        optimized = re.sub(r"\s+with\s*\(\s*nolock\s*\)|\s+nolock\b", "", optimized, flags=re.I)
    footer = [
        "",
        "-- Optimization notes generated by DB Optimization & Intelligence Agent",
        *[f"-- - {item['title']}: {item['recommendation']}" for item in suggestions[:6]],
    ]
    if object_type == "Stored Procedure" and any(item["title"] == "Parameter sniffing risk" for item in findings) and db_type == "SQL Server":
        footer.append("-- Review OPTION (RECOMPILE), OPTIMIZE FOR UNKNOWN, or targeted local-variable strategy after comparing actual plans.")
    return optimized.rstrip() + "\n" + "\n".join(footer)


def build_index_scripts(
    db_type: str,
    tables: list[str],
    filters: list[str],
    joins: list[dict[str, str]],
    findings: list[dict[str, Any]],
) -> list[str]:
    columns = []
    for text in filters + [join["condition"] for join in joins]:
        for match in re.finditer(r"(?:\b\w+\.)?(\w+)\s*(?:=|>|<|>=|<=|like|in\b)", text, re.I):
            col = match.group(1)
            if col.lower() not in SQL_KEYWORDS and col not in columns:
                columns.append(col)

    if not tables or not columns:
        return []

    scripts = []
    for table in tables[:3]:
        cols = columns[:3]
        index_name = f"IX_{table.split('.')[-1].replace('#', 'Temp')}_{'_'.join(cols)}"
        if db_type == "PostgreSQL":
            scripts.append(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({', '.join(cols)});")
        elif db_type == "Oracle":
            scripts.append(f"CREATE INDEX {index_name} ON {table} ({', '.join(cols)});")
        else:
            scripts.append(f"CREATE NONCLUSTERED INDEX {index_name} ON {table} ({', '.join(cols)});")
    return scripts


def build_impact(
    object_type: str,
    name: str,
    tables: list[str],
    references: list[str],
    missing_references: list[str],
    findings: list[dict[str, Any]],
    dependency_map: dict[str, Any],
) -> dict[str, Any]:
    high_count = sum(1 for item in findings if item["severity"] == "High")
    return {
        "affected_tables": tables,
        "dependent_objects": references,
        "missing_objects": missing_references,
        "downstream": ["Reports", "Dashboards", "Batch jobs", "APIs"] if object_type == "Stored Procedure" else ["Calling applications"],
        "risk_level": "High" if high_count or missing_references else "Medium" if len(findings) > 2 else "Low",
        "deployment_complexity": "High" if references or len(tables) > 4 else "Medium" if tables else "Low",
        "rollback": "Keep original object script, deploy indexes separately, and capture before/after execution metrics.",
        "dependency_node_count": len(dependency_map["nodes"]),
    }


def build_execution_plan(sql: str, findings: list[dict[str, Any]], joins: list[dict[str, str]], tables: list[str], metrics: dict[str, Any]) -> dict[str, Any]:
    operators = []
    if any(item["title"] in {"Unfiltered read", "SELECT * usage"} for item in findings):
        operators.append({"operator": "Index/Table Scan", "risk": "High", "note": "Likely scan due to broad projection or weak predicates."})
    else:
        operators.append({"operator": "Index Seek", "risk": "Low", "note": "Seek is possible if recommended indexes and statistics exist."})
    if joins:
        operators.append({"operator": "Hash/Nested Loop Join", "risk": "Medium", "note": f"{len(joins)} join(s) require cardinality validation."})
    if re.search(r"\border\s+by\b", sql, re.I):
        operators.append({"operator": "Sort", "risk": "Medium", "note": "Sort can spill if memory grant is underestimated."})
    if re.search(r"\bgroup\s+by\b", sql, re.I):
        operators.append({"operator": "Hash Aggregate", "risk": "Medium", "note": "Grouping may need supporting indexes or pre-aggregation."})
    if any(item["title"] == "Temp table usage" for item in findings):
        operators.append({"operator": "TempDB Worktable", "risk": "Medium", "note": "TempDB writes should be measured under load."})

    return {
        "operators": operators,
        "costliest_operator": max(operators, key=lambda item: {"High": 3, "Medium": 2, "Low": 1}[item["risk"]]),
        "statistics": "Update statistics on affected tables before comparing plans.",
        "parallelism": "Review CXPACKET/CXCONSUMER waits if CPU is high.",
        "memory_grant": "Watch for sort/hash spills in the actual execution plan.",
        "estimated_cost": metrics["query_cost"],
    }


def explain_sql(sql: str, object_type: str, name: str, tables: list[str], joins: list[dict[str, str]], filters: list[str], references: list[str]) -> str:
    parts = [f"{name} is classified as {object_type}."]
    if tables:
        parts.append(f"It touches {', '.join(tables)}.")
    if joins:
        parts.append(f"It uses {len(joins)} join(s).")
    if filters:
        parts.append(f"It applies {len(filters)} filter predicate(s).")
    if references:
        parts.append(f"It calls {', '.join(references)}.")
    return " ".join(parts)


def build_report(
    name: str,
    object_type: str,
    db_type: str,
    findings: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    impact: dict[str, Any],
    execution_plan: dict[str, Any],
    optimized_sql: str,
    index_scripts: list[str],
) -> str:
    lines = [
        f"# DB Review Report: {name}",
        "",
        f"- Object type: {object_type}",
        f"- Database type: {db_type}",
        f"- Risk level: {impact['risk_level']}",
        f"- Deployment complexity: {impact['deployment_complexity']}",
        "",
        "## Findings",
        *[f"- [{item['severity']}] {item['title']}: {item['detail']}" for item in findings],
        "",
        "## Optimization Suggestions",
        *[f"- [{item['impact']} impact / {item['effort']} effort] {item['title']}: {item['recommendation']}" for item in suggestions],
        "",
        "## Impact",
        f"- Affected tables: {', '.join(impact['affected_tables']) or 'None detected'}",
        f"- Dependent objects: {', '.join(impact['dependent_objects']) or 'None detected'}",
        f"- Missing objects: {', '.join(impact['missing_objects']) or 'None'}",
        f"- Rollback: {impact['rollback']}",
        "",
        "## Execution Plan Review",
        *[f"- {item['operator']} ({item['risk']}): {item['note']}" for item in execution_plan["operators"]],
        "",
        "## Index Scripts",
        "```sql",
        "\n\n".join(index_scripts) or "-- No index scripts generated.",
        "```",
        "",
        "## Optimized SQL Draft",
        "```sql",
        optimized_sql,
        "```",
    ]
    return "\n".join(lines)


def execution_plan_to_markdown(plan: dict[str, Any]) -> str:
    lines = ["# Execution Plan Analysis", ""]
    for item in plan["operators"]:
        lines.append(f"- {item['operator']} ({item['risk']}): {item['note']}")
    lines.extend([
        "",
        f"- Costliest operator: {plan['costliest_operator']['operator']}",
        f"- Estimated cost: {plan['estimated_cost']}",
        f"- Statistics: {plan['statistics']}",
        f"- Parallelism: {plan['parallelism']}",
        f"- Memory grant: {plan['memory_grant']}",
    ])
    return "\n".join(lines)


def comparison_report(original: str, optimized: str, findings: list[dict[str, Any]], suggestions: list[dict[str, Any]]) -> str:
    return "\n".join([
        "# Before vs After Comparison",
        "",
        f"- Original length: {len(original)} characters",
        f"- Optimized draft length: {len(optimized)} characters",
        f"- Findings addressed: {len(findings)}",
        f"- Recommendations generated: {len(suggestions)}",
        "",
        "## Expected Improvement Areas",
        *[f"- {item['title']}" for item in suggestions],
    ])


def test_data_generator(db_type: str, tables: list[str]) -> str:
    target = tables[0] if tables else "dbo.TargetTable"
    if db_type == "PostgreSQL":
        return f"-- Generate representative test rows for {target}\n-- Use generate_series and realistic distribution for filter columns.\n"
    return f"-- Generate representative test rows for {target}\n-- Create small, medium, and high-cardinality parameter cases before comparing execution plans.\n"


def has_write_operation(sql: str) -> bool:
    return bool(re.search(r"\b(insert|update|delete|merge)\b", sql, re.I))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"object-{datetime.now().strftime('%H%M%S')}"


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2)


def infer_schema_from_prompt(prompt: str) -> list[dict[str, Any]]:
    lower = prompt.lower()
    entities = []
    candidates = {
        "Customer": ["customer", "client", "member"],
        "Order": ["order", "purchase"],
        "OrderItem": ["order item", "line item", "item"],
        "Product": ["product", "sku", "catalog"],
        "Payment": ["payment", "invoice", "billing"],
        "UserAccount": ["user", "account", "login"],
        "Ticket": ["ticket", "incident", "case"],
        "Policy": ["policy", "insurance"],
        "Claim": ["claim"],
    }
    for name, words in candidates.items():
        if any(word in lower for word in words):
            entities.append(name)
    if not entities:
        entities = ["Customer", "Order", "OrderItem"]
    if "Order" in entities and "Customer" not in entities:
        entities.insert(0, "Customer")
    if "OrderItem" in entities and "Order" not in entities:
        entities.insert(0, "Order")

    return [default_table(entity) for entity in dict.fromkeys(entities)]


def default_table(entity: str) -> dict[str, Any]:
    table = {
        "Customer": [
            ("CustomerId", "INT", False, "PK"),
            ("CustomerName", "VARCHAR(200)", False, ""),
            ("Email", "VARCHAR(320)", True, "UQ"),
            ("Status", "VARCHAR(30)", False, ""),
            ("CreatedAt", "DATETIME2", False, ""),
            ("UpdatedAt", "DATETIME2", True, ""),
        ],
        "Order": [
            ("OrderId", "INT", False, "PK"),
            ("CustomerId", "INT", False, "FK"),
            ("OrderDate", "DATETIME2", False, ""),
            ("Status", "VARCHAR(30)", False, ""),
            ("TotalAmount", "DECIMAL(18,2)", False, ""),
            ("CreatedAt", "DATETIME2", False, ""),
        ],
        "OrderItem": [
            ("OrderItemId", "INT", False, "PK"),
            ("OrderId", "INT", False, "FK"),
            ("ProductId", "INT", False, "FK"),
            ("Quantity", "INT", False, ""),
            ("UnitPrice", "DECIMAL(18,2)", False, ""),
        ],
        "Product": [
            ("ProductId", "INT", False, "PK"),
            ("Sku", "VARCHAR(80)", False, "UQ"),
            ("ProductName", "VARCHAR(200)", False, ""),
            ("IsActive", "BIT", False, ""),
        ],
        "Payment": [
            ("PaymentId", "INT", False, "PK"),
            ("OrderId", "INT", False, "FK"),
            ("Amount", "DECIMAL(18,2)", False, ""),
            ("PaymentStatus", "VARCHAR(30)", False, ""),
            ("PaidAt", "DATETIME2", True, ""),
        ],
    }.get(entity, [
        (f"{entity}Id", "INT", False, "PK"),
        ("Name", "VARCHAR(200)", False, ""),
        ("Status", "VARCHAR(30)", False, ""),
        ("CreatedAt", "DATETIME2", False, ""),
    ])
    return {
        "name": entity,
        "columns": [{"name": c, "type": t, "nullable": n, "role": r} for c, t, n, r in table],
    }


def parse_ddl_tables(sql: str) -> list[dict[str, Any]]:
    tables = []
    for match in re.finditer(r"\bcreate\s+table\s+([\[\]\w.]+)\s*\((.*?)\)\s*;?", sql, re.I | re.S):
        name = clean_identifier(match.group(1)).split(".")[-1]
        body = match.group(2)
        columns = []
        for raw in body.split(","):
            line = raw.strip()
            if not line or re.match(r"\b(primary|foreign|constraint|unique|check)\b", line, re.I):
                continue
            parts = line.split()
            if len(parts) >= 2:
                role = "PK" if "primary key" in line.lower() else "FK" if parts[0].lower().endswith("id") and parts[0].lower() != f"{name.lower()}id" else ""
                columns.append({"name": clean_identifier(parts[0]), "type": parts[1], "nullable": "not null" not in line.lower(), "role": role})
        tables.append({"name": name, "columns": columns})
    return tables or infer_schema_from_prompt(sql)


def infer_relationships(tables: list[dict[str, Any]]) -> list[dict[str, str]]:
    names = {table["name"]: table for table in tables}
    relationships = []
    for table in tables:
        for col in table["columns"]:
            if col["name"].endswith("Id") and col["role"] != "PK":
                parent = col["name"][:-2]
                if parent in names:
                    relationships.append({"from": table["name"], "to": parent, "column": col["name"], "type": "many-to-one"})
    return relationships


def review_schema(tables: list[dict[str, Any]], relationships: list[dict[str, str]]) -> list[dict[str, str]]:
    findings = []
    related_cols = {rel["column"] for rel in relationships}
    for table in tables:
        cols = table["columns"]
        if not any(col["role"] == "PK" for col in cols):
            findings.append({"severity": "High", "title": f"{table['name']} missing primary key", "detail": "Every operational table should have a stable primary key."})
        if not any(col["name"].lower() == "createdat" for col in cols):
            findings.append({"severity": "Medium", "title": f"{table['name']} missing audit column", "detail": "Add CreatedAt for traceability and data lifecycle review."})
        for col in cols:
            if "MAX" in col["type"].upper():
                findings.append({"severity": "Medium", "title": f"{table['name']}.{col['name']} uses broad type", "detail": "Avoid unbounded text types unless the business case requires it."})
            if col["name"].endswith("Id") and col["role"] != "PK" and col["name"] not in related_cols:
                findings.append({"severity": "Medium", "title": f"{table['name']}.{col['name']} may need FK", "detail": "Column looks relational but no parent table relationship was inferred."})
    if not findings:
        findings.append({"severity": "Low", "title": "Schema baseline looks reasonable", "detail": "Validate naming, cardinality, indexes, and constraints with business owners."})
    return findings


def build_schema_ddl(tables: list[dict[str, Any]], relationships: list[dict[str, str]], db_type: str) -> str:
    lines = [f"-- Migration script for {db_type}", ""]
    for table in tables:
        lines.append(f"CREATE TABLE {table['name']} (")
        col_lines = []
        for col in table["columns"]:
            null = "NULL" if col["nullable"] else "NOT NULL"
            suffix = " PRIMARY KEY" if col["role"] == "PK" else ""
            col_lines.append(f"  {col['name']} {col['type']} {null}{suffix}")
        lines.append(",\n".join(col_lines))
        lines.append(");")
        lines.append("")
    for rel in relationships:
        lines.append(f"ALTER TABLE {rel['from']} ADD CONSTRAINT FK_{rel['from']}_{rel['to']} FOREIGN KEY ({rel['column']}) REFERENCES {rel['to']}({rel['to']}Id);")
    for rel in relationships:
        lines.append(f"CREATE INDEX IX_{rel['from']}_{rel['column']} ON {rel['from']} ({rel['column']});")
    return "\n".join(lines)


def build_schema_rollback(tables: list[dict[str, Any]], db_type: str) -> str:
    lines = [f"-- Rollback script for {db_type}"]
    for table in reversed(tables):
        lines.append(f"DROP TABLE {table['name']};")
    return "\n".join(lines)


def build_erd_summary(tables: list[dict[str, Any]], relationships: list[dict[str, str]]) -> str:
    lines = ["erDiagram"]
    for rel in relationships:
        lines.append(f"  {rel['to']} ||--o{{ {rel['from']} : has")
    for table in tables:
        lines.append(f"  {table['name']} {{")
        for col in table["columns"]:
            lines.append(f"    {col['type'].replace(' ', '_')} {col['name']}")
        lines.append("  }")
    return "\n".join(lines)


def build_schema_report(tables, relationships, review, impact, ddl, rollback) -> str:
    relationship_lines = [f"- {rel['from']}.{rel['column']} -> {rel['to']}" for rel in relationships] or ["- None inferred"]
    return "\n".join([
        "# DB Schema Agent Review",
        "",
        f"- Tables designed/reviewed: {len(tables)}",
        f"- Relationships inferred: {len(relationships)}",
        f"- Impacted known objects: {len(impact['impacted_objects'])}",
        "",
        "## Tables",
        *[f"- {table['name']}: {len(table['columns'])} columns" for table in tables],
        "",
        "## Relationships",
        *relationship_lines,
        "",
        "## Quality Review",
        *[f"- [{item['severity']}] {item['title']}: {item['detail']}" for item in review],
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


def build_migration_plan(tables, relationships, impact) -> str:
    return "\n".join([
        "# Migration Plan",
        "",
        "1. Review generated DDL and naming standards.",
        "2. Deploy tables before foreign keys.",
        "3. Deploy indexes after initial load for large tables.",
        "4. Validate impacted stored procedures, views, reports, APIs, and jobs.",
        "5. Keep rollback script ready for the same deployment window.",
        "",
        f"Impacted known objects: {len(impact['impacted_objects'])}",
    ])

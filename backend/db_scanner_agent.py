"""
DB Scanner Agent
Connects to a live SQL Server and scans stored procedures, tables, indexes,
and slow query stats — feeds results into the existing optimization pipeline.
"""

import re
from typing import Dict, List, Any

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


def _build_conn_str(connection_string: str) -> tuple[str, str]:
    """Parse and normalise connection string. Returns (pyodbc_str, database)."""
    if not PYODBC_AVAILABLE:
        raise Exception("pyodbc is not installed. Run: pip install pyodbc")

    parsed = {}
    for part in re.split(r";", connection_string):
        part = part.strip()
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        parsed[key.strip().lower()] = value.strip()

    # Already a pyodbc string
    if "driver" in parsed:
        database = parsed.get("database", parsed.get("initial catalog", ""))
        return connection_string, database

    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise Exception("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server'.")
    driver = sorted(drivers)[-1]

    server   = parsed.get("server", parsed.get("data source", "localhost"))
    database = parsed.get("database", parsed.get("initial catalog", ""))
    trusted  = parsed.get("trusted_connection", "false").lower() in ("true", "yes")
    uid      = parsed.get("uid", parsed.get("user id", ""))
    pwd      = parsed.get("pwd", parsed.get("password", ""))

    parts = [f"DRIVER={{{driver}}}", f"SERVER={server}"]
    if trusted:
        parts.append("Trusted_Connection=yes")
    else:
        parts += [f"UID={uid}", f"PWD={pwd}"]
    if database:
        parts.append(f"DATABASE={database}")

    return ";".join(parts) + ";", database


def _connect(connection_string: str):
    conn_str, _ = _build_conn_str(connection_string)
    conn = pyodbc.connect(conn_str, timeout=10)
    conn.autocommit = True
    return conn


# ── public API ────────────────────────────────────────────────────────────────

def scan_database(connection_string: str) -> Dict[str, Any]:
    """
    Full database scan.
    Returns stored_procedures, slow_procedures, tables, indexes, summary.
    """
    conn = _connect(connection_string)
    cursor = conn.cursor()

    stored_procedures = _scan_stored_procedures(cursor)
    slow_procedures   = _scan_slow_procedures(cursor)
    tables            = _scan_tables(cursor)
    indexes           = _scan_indexes(cursor)

    conn.close()

    # Mark slow SPs in the full list
    slow_names = {sp["procedure_name"].lower() for sp in slow_procedures}
    for sp in stored_procedures:
        sp["is_slow"] = sp["procedure_name"].lower() in slow_names

    return {
        "stored_procedures": stored_procedures,
        "slow_procedures": slow_procedures,
        "tables": tables,
        "indexes": indexes,
        "summary": {
            "total_procedures": len(stored_procedures),
            "slow_procedures":  len(slow_procedures),
            "total_tables":     len(tables),
            "total_indexes":    len(indexes),
        },
    }


def get_procedure_source(connection_string: str, procedure_name: str) -> Dict[str, Any]:
    """Fetch full source code of a single stored procedure."""
    conn   = _connect(connection_string)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT p.name, m.definition
        FROM sys.procedures p
        JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE p.name = ?
        """,
        procedure_name,
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise Exception(f"Stored procedure '{procedure_name}' not found.")

    return {"procedure_name": row[0], "source_code": row[1]}


def deploy_optimized_procedure(connection_string: str, optimized_sql: str, procedure_name: str = None) -> Dict[str, Any]:
    """
    Deploy an optimized stored procedure.
    Auto-wraps in CREATE OR ALTER PROCEDURE if AI returned only the body.
    """
    conn   = _connect(connection_string)
    cursor = conn.cursor()

    sql = optimized_sql.strip()

    # Strip leading comments before checking for CREATE PROCEDURE
    sql_no_comments = re.sub(r'(^\s*--[^\n]*\n)', '', sql, flags=re.MULTILINE).strip()

    # If AI returned only the body, fetch original signature and wrap it
    if not re.match(r'^\s*(CREATE\s+OR\s+ALTER|CREATE|ALTER)\s+PROC', sql_no_comments, re.IGNORECASE):
        if not procedure_name:
            raise Exception("Optimized SQL must start with CREATE OR ALTER PROCEDURE / CREATE PROCEDURE.")
        # Fetch original procedure signature from DB
        cursor2 = conn.cursor()
        cursor2.execute(
            "SELECT m.definition FROM sys.procedures p "
            "JOIN sys.sql_modules m ON p.object_id = m.object_id WHERE p.name = ?",
            procedure_name,
        )
        row = cursor2.fetchone()
        if not row:
            raise Exception(f"Cannot auto-wrap: original procedure '{procedure_name}' not found.")
        original = row[0]
        # Extract header up to AS\nBEGIN
        header_match = re.search(r'^(.*?\bAS\b\s*)', original, re.IGNORECASE | re.DOTALL)
        if header_match:
            header = header_match.group(1).strip()
            header = re.sub(r'^\s*CREATE\s+PROCEDURE', 'CREATE OR ALTER PROCEDURE', header, count=1, flags=re.IGNORECASE)
            sql = header + '\nBEGIN\n' + sql_no_comments + '\nEND'
        else:
            raise Exception("Could not extract procedure header for auto-wrap.")
    else:
        sql = sql_no_comments
        sql = re.sub(r'^\s*CREATE\s+PROCEDURE', 'CREATE OR ALTER PROCEDURE', sql, count=1, flags=re.IGNORECASE)
        sql = re.sub(r'^\s*ALTER\s+PROCEDURE',  'CREATE OR ALTER PROCEDURE', sql, count=1, flags=re.IGNORECASE)
        # Ensure procedure body is closed with END
        if re.search(r'\bBEGIN\b', sql, re.IGNORECASE) and not re.search(r'\bEND\s*$', sql.strip(), re.IGNORECASE):
            sql = sql.rstrip() + '\nEND'

    try:
        cursor.execute(sql)
        conn.close()
        # Extract procedure name for confirmation message
        name_match = re.search(r"CREATE\s+OR\s+ALTER\s+PROCEDURE\s+([\[\]\w.]+)", sql, re.IGNORECASE)
        proc_name  = name_match.group(1).replace("[", "").replace("]", "") if name_match else "procedure"
        return {
            "success": True,
            "message": f"✅ '{proc_name}' deployed successfully. Open SSMS to verify.",
            "procedure_name": proc_name,
        }
    except Exception as e:
        conn.close()
        raise Exception(f"Deployment failed: {str(e)}")


# ── internal helpers ──────────────────────────────────────────────────────────

def _scan_stored_procedures(cursor) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            p.name                          AS procedure_name,
            SCHEMA_NAME(p.schema_id)        AS schema_name,
            p.create_date,
            p.modify_date,
            LEN(m.definition)               AS source_length
        FROM sys.procedures p
        JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE p.is_ms_shipped = 0
        ORDER BY p.name
        """
    )
    rows = cursor.fetchall()
    return [
        {
            "procedure_name": row[0],
            "schema_name":    row[1],
            "created_at":     str(row[2]),
            "modified_at":    str(row[3]),
            "source_length":  row[4],
            "is_slow":        False,
        }
        for row in rows
    ]


def _scan_slow_procedures(cursor) -> List[Dict[str, Any]]:
    """Top 20 slowest SPs by average CPU time from execution stats."""
    try:
        cursor.execute(
            """
            SELECT TOP 20
                OBJECT_NAME(ps.object_id)                           AS procedure_name,
                ps.execution_count,
                ps.total_worker_time / ps.execution_count           AS avg_cpu_us,
                ps.total_logical_reads / ps.execution_count         AS avg_logical_reads,
                ps.total_elapsed_time / ps.execution_count          AS avg_elapsed_us,
                ps.last_execution_time
            FROM sys.dm_exec_procedure_stats ps
            WHERE ps.database_id = DB_ID()
              AND ps.execution_count > 0
              AND OBJECT_NAME(ps.object_id) IS NOT NULL
            ORDER BY avg_cpu_us DESC
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "procedure_name":    row[0],
                "execution_count":   row[1],
                "avg_cpu_ms":        round(row[2] / 1000, 2),
                "avg_logical_reads": row[3],
                "avg_elapsed_ms":    round(row[4] / 1000, 2),
                "last_execution":    str(row[5]),
            }
            for row in rows
        ]
    except Exception:
        # dm_exec_procedure_stats may not be accessible on all editions
        return []


def _scan_tables(cursor) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            t.name                      AS table_name,
            SCHEMA_NAME(t.schema_id)    AS schema_name,
            p.rows                      AS row_count
        FROM sys.tables t
        JOIN sys.partitions p
          ON t.object_id = p.object_id AND p.index_id IN (0, 1)
        WHERE t.is_ms_shipped = 0
        ORDER BY t.name
        """
    )
    rows = cursor.fetchall()
    return [
        {
            "table_name":  row[0],
            "schema_name": row[1],
            "row_count":   row[2],
        }
        for row in rows
    ]


def _scan_indexes(cursor) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            t.name          AS table_name,
            i.name          AS index_name,
            i.type_desc     AS index_type,
            i.is_unique,
            i.is_primary_key
        FROM sys.indexes i
        JOIN sys.tables t ON i.object_id = t.object_id
        WHERE t.is_ms_shipped = 0
          AND i.name IS NOT NULL
        ORDER BY t.name, i.name
        """
    )
    rows = cursor.fetchall()
    return [
        {
            "table_name":    row[0],
            "index_name":    row[1],
            "index_type":    row[2],
            "is_unique":     bool(row[3]),
            "is_primary_key": bool(row[4]),
        }
        for row in rows
    ]

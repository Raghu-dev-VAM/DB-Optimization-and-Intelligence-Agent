"""
DB Connector - executes DDL scripts against SQL Server using a connection string.
Accepts .NET style or pyodbc style connection strings.
"""

import re
from typing import Dict, Any

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


def _parse_connection_string(conn_str: str) -> dict:
    """Parse key=value pairs from a connection string (case-insensitive keys)."""
    result = {}
    for part in re.split(r';', conn_str):
        part = part.strip()
        if '=' not in part:
            continue
        key, _, value = part.partition('=')
        result[key.strip().lower()] = value.strip()
    return result


def _to_pyodbc_string(conn_str: str) -> tuple[str, str]:
    """
    Convert a .NET or pyodbc connection string to a valid pyodbc connection string.
    Returns (pyodbc_conn_str, database_name).
    """
    parsed = _parse_connection_string(conn_str)

    # Already a pyodbc string if it has 'driver'
    if 'driver' in parsed:
        database = parsed.get('database', parsed.get('initial catalog', ''))
        return conn_str, database

    # .NET style — convert to pyodbc
    drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]
    if not drivers:
        raise Exception("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server'.")
    driver = sorted(drivers)[-1]

    server  = parsed.get('server', parsed.get('data source', 'localhost'))
    database = parsed.get('database', parsed.get('initial catalog', ''))
    trusted = parsed.get('trusted_connection', 'false').lower() in ('true', 'yes')
    uid     = parsed.get('uid', parsed.get('user id', ''))
    pwd     = parsed.get('pwd', parsed.get('password', ''))

    parts = [f"DRIVER={{{driver}}}", f"SERVER={server}"]
    if trusted:
        parts.append("Trusted_Connection=yes")
    else:
        parts += [f"UID={uid}", f"PWD={pwd}"]

    return ';'.join(parts) + ';', database


def execute_ddl(connection_string: str, ddl_script: str) -> Dict[str, Any]:
    """
    Execute a DDL script against SQL Server.
    - Parses the connection string to extract the database name.
    - Creates the database if it does not exist.
    - Executes each GO-separated batch.
    """
    if not PYODBC_AVAILABLE:
        raise Exception("pyodbc is not installed. Run: pip install pyodbc")

    base_conn_str, database = _to_pyodbc_string(connection_string)

    if not database:
        raise Exception("Database name not found in connection string. Add 'Database=YourDbName;'")

    # Step 1 — connect to master and create DB if needed
    master_str = re.sub(r'DATABASE=[^;]+;?', '', base_conn_str, flags=re.IGNORECASE)
    master_str = re.sub(r'INITIAL CATALOG=[^;]+;?', '', master_str, flags=re.IGNORECASE)
    master_str += f"DATABASE=master;"

    conn = pyodbc.connect(master_str, timeout=10)
    conn.autocommit = True
    conn.cursor().execute(
        f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{database}') "
        f"CREATE DATABASE [{database}]"
    )
    conn.close()

    # Step 2 — reconnect to the target database
    target_str = re.sub(r'DATABASE=[^;]+;?', '', base_conn_str, flags=re.IGNORECASE)
    target_str = re.sub(r'INITIAL CATALOG=[^;]+;?', '', target_str, flags=re.IGNORECASE)
    target_str += f"DATABASE={database};"

    conn = pyodbc.connect(target_str, timeout=10)
    conn.autocommit = True
    cursor = conn.cursor()

    # Strip USE statements from script
    ddl_script = re.sub(r'^\s*USE\s+\S+\s*;?\s*$', '', ddl_script, flags=re.MULTILINE | re.IGNORECASE)

    # Split on GO and execute each batch
    batches = [b.strip() for b in re.split(r'^\s*GO\s*$', ddl_script, flags=re.MULTILINE | re.IGNORECASE)]

    executed = 0
    errors = []
    for batch in batches:
        if not batch.strip():
            continue
        # Skip comment-only batches
        non_comment = re.sub(r'^\s*--[^\n]*', '', batch, flags=re.MULTILINE).strip()
        if not non_comment:
            continue
        try:
            cursor.execute(batch)
            executed += 1
        except Exception as e:
            errors.append(f"{str(e)} | SQL: {batch[:120]}")

    conn.close()

    return {
        "success": True,
        "database": database,
        "batches_executed": executed,
        "errors": errors,
        "message": f"✅ Database '{database}' ready. {executed} batch(es) executed."
                   + (f" {len(errors)} warning(s)." if errors else ""),
    }

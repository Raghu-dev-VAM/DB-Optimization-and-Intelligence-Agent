"""
DB Connector - connects to SQL Server via pyodbc and executes DDL scripts
"""

import re
from typing import Dict, Any

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


def _get_connection(server: str, use_windows_auth: bool = True, username: str = "", password: str = ""):
    if not PYODBC_AVAILABLE:
        raise Exception("pyodbc is not installed. Run: pip install pyodbc")

    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise Exception("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server' from Microsoft.")

    driver = sorted(drivers)[-1]  # pick latest

    if use_windows_auth:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};UID={username};PWD={password};"

    return pyodbc.connect(conn_str, timeout=10)


def test_connection(server: str, use_windows_auth: bool = True, username: str = "", password: str = "") -> Dict[str, Any]:
    """Test SQL Server connection and return available databases"""
    try:
        if not PYODBC_AVAILABLE:
            raise Exception("pyodbc not installed. Run: pip install pyodbc")
        
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not drivers:
            raise Exception("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server'")
        
        conn = _get_connection(server, use_windows_auth, username, password)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as Version, @@SERVERNAME as ServerName")
        server_info = cursor.fetchone()
        cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb') ORDER BY name")
        databases = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {
            "connected": True, 
            "server": server, 
            "databases": databases,
            "server_version": server_info[0] if server_info else "Unknown",
            "driver_used": sorted(drivers)[-1]
        }
    except Exception as e:
        error_msg = str(e)
        if "Login failed" in error_msg:
            error_msg = "Authentication failed. Check username/password or try Windows Authentication."
        elif "server was not found" in error_msg.lower():
            error_msg = f"Server '{server}' not found. Try 'localhost', '.\\SQLEXPRESS', or your computer name."
        raise Exception(f"Connection failed: {error_msg}")


def execute_ddl(server: str, database: str, ddl_script: str, use_windows_auth: bool = True, username: str = "", password: str = "") -> Dict[str, Any]:
    """Create database if needed, then execute DDL script"""
    try:
        conn = _get_connection(server, use_windows_auth, username, password)
        conn.autocommit = True
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = ?) CREATE DATABASE [{database}]", database)
        cursor.execute(f"USE [{database}]")

        # Strip USE statements and TODO comments — connector handles database switching itself
        ddl_script = re.sub(r'^\s*USE\s+\S+\s*;?\s*$', '', ddl_script, flags=re.MULTILINE | re.IGNORECASE)
        ddl_script = re.sub(r'^\s*--.*$', '', ddl_script, flags=re.MULTILINE)

        # Split on GO and execute each batch
        batches = [b.strip() for b in re.split(r'^\s*GO\s*$', ddl_script, flags=re.MULTILINE | re.IGNORECASE) if b.strip()]

        executed = 0
        errors = []
        for batch in batches:
            # Skip empty or comment-only batches
            if not batch.strip() or all(line.strip().startswith('--') or not line.strip() for line in batch.splitlines()):
                continue
            try:
                cursor.execute(batch)
                executed += 1
            except Exception as e:
                errors.append(str(e))

        conn.close()

        return {
            "success": True,
            "database": database,
            "server": server,
            "batches_executed": executed,
            "errors": errors,
            "message": f"Database '{database}' ready. {executed} batch(es) executed." + (f" {len(errors)} warning(s)." if errors else "")
        }

    except Exception as e:
        raise Exception(f"Execution failed: {str(e)}")

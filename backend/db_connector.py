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
    print(f"[DB_CONNECTOR] _get_connection called with server='{server}', windows_auth={use_windows_auth}")
    
    if not PYODBC_AVAILABLE:
        raise Exception("pyodbc is not installed. Run: pip install pyodbc")

    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    print(f"[DB_CONNECTOR] Available drivers: {drivers}")
    
    if not drivers:
        raise Exception("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server' from Microsoft.")

    driver = sorted(drivers)[-1]  # pick latest
    print(f"[DB_CONNECTOR] Using driver: {driver}")

    if use_windows_auth:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};UID={username};PWD={password};"
    
    print(f"[DB_CONNECTOR] Connection string: {conn_str.replace(password, '***') if password else conn_str}")
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        print(f"[DB_CONNECTOR] Connection successful")
        return conn
    except Exception as e:
        print(f"[DB_CONNECTOR] Connection failed: {str(e)}")
        raise


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
    print(f"[DB_CONNECTOR] Starting execution:")
    print(f"  Server: '{server}'")
    print(f"  Database: '{database}'")
    print(f"  Windows Auth: {use_windows_auth}")
    
    try:
        print(f"[DB_CONNECTOR] Getting connection...")
        conn = _get_connection(server, use_windows_auth, username, password)
        conn.autocommit = True
        cursor = conn.cursor()
        print(f"[DB_CONNECTOR] Connection successful")

        # Create database if it doesn't exist
        print(f"[DB_CONNECTOR] Creating database if not exists: {database}")
        cursor.execute(f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = ?) CREATE DATABASE [{database}]", database)
        cursor.execute(f"USE [{database}]")
        print(f"[DB_CONNECTOR] Database ready")

        # Strip USE statements and TODO comments — connector handles database switching itself
        original_script = ddl_script
        ddl_script = re.sub(r'^\s*USE\s+\S+\s*;?\s*$', '', ddl_script, flags=re.MULTILINE | re.IGNORECASE)
        ddl_script = re.sub(r'^\s*--.*$', '', ddl_script, flags=re.MULTILINE)
        print(f"[DB_CONNECTOR] Script cleaned. Original: {len(original_script)} chars, Cleaned: {len(ddl_script)} chars")

        # Split on GO and execute each batch
        batches = [b.strip() for b in re.split(r'^\s*GO\s*$', ddl_script, flags=re.MULTILINE | re.IGNORECASE) if b.strip()]
        print(f"[DB_CONNECTOR] Found {len(batches)} batches to execute")

        executed = 0
        errors = []
        for i, batch in enumerate(batches):
            # Skip empty or comment-only batches
            if not batch.strip() or all(line.strip().startswith('--') or not line.strip() for line in batch.splitlines()):
                print(f"[DB_CONNECTOR] Skipping empty batch {i+1}")
                continue
            try:
                print(f"[DB_CONNECTOR] Executing batch {i+1}: {batch[:100]}...")
                cursor.execute(batch)
                executed += 1
                print(f"[DB_CONNECTOR] Batch {i+1} executed successfully")
            except Exception as e:
                error_msg = str(e)
                print(f"[DB_CONNECTOR] Batch {i+1} failed: {error_msg}")
                errors.append(error_msg)

        conn.close()
        print(f"[DB_CONNECTOR] Execution complete. {executed} batches executed, {len(errors)} errors")

        return {
            "success": True,
            "database": database,
            "server": server,
            "batches_executed": executed,
            "errors": errors,
            "message": f"Database '{database}' ready. {executed} batch(es) executed." + (f" {len(errors)} warning(s)." if errors else "")
        }

    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        print(f"[DB_CONNECTOR] {error_msg}")
        raise Exception(error_msg)

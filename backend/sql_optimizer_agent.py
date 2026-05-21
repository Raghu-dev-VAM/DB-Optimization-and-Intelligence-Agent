"""
AI-Powered SQL Optimizer Agent
Provides intelligent performance optimization recommendations using Groq AI
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from datetime import datetime

from agent_config import sql_agent_system
from groq_client import groq_client

@dataclass
class OptimizationResult:
    """SQL optimization analysis results"""
    performance_issues: List[Dict[str, Any]]
    optimization_suggestions: List[Dict[str, Any]]
    index_recommendations: List[Dict[str, Any]]
    query_rewrite_suggestions: List[str]
    estimated_improvement: Dict[str, Any]
    ai_insights: Dict[str, Any]
    confidence_score: float

class SQLOptimizerAgent:
    """AI-powered SQL Optimizer Agent using Groq"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("optimizer")
        
    def optimize_sql(self, sql: str, parsed_data: Dict[str, Any] = None, db_type: str = "SQL Server") -> OptimizationResult:
        """Analyze SQL for performance optimization opportunities"""
        
        # Get basic static analysis first
        static_results = self._static_optimization_analysis(sql, parsed_data or {}, db_type)
        
        # Enhance with AI analysis
        ai_insights = self._ai_optimize(sql, static_results, parsed_data or {}, db_type)
        
        # Combine results
        return OptimizationResult(
            performance_issues=ai_insights.get("enhanced_issues", static_results["performance_issues"]),
            optimization_suggestions=ai_insights.get("enhanced_suggestions", static_results["optimization_suggestions"]),
            index_recommendations=ai_insights.get("enhanced_indexes", static_results["index_recommendations"]),
            query_rewrite_suggestions=ai_insights.get("query_rewrites", []),
            estimated_improvement=ai_insights.get("improvement_estimate", static_results["estimated_improvement"]),
            ai_insights=ai_insights,
            confidence_score=ai_insights.get("confidence", 0.8)
        )
    
    def generate_optimized_sql(self, sql: str, parsed_data: Dict[str, Any] = None, db_type: str = "SQL Server") -> str:
        """Generate actual runnable optimized SQL using AI"""
        
        context = parsed_data or {}
        tables = context.get("tables", [])
        joins = context.get("joins", [])
        filters = context.get("filters", [])
        
        prompt = self._build_sql_optimization_prompt(sql, db_type, tables, joins, filters)
        
        try:
            response = groq_client.call_ai(self.config.system_message, prompt, timeout=25)
            
            # Extract optimized SQL from response - it might be in reasoning field as JSON
            optimized_sql = response.get("optimized_sql")
            
            if not optimized_sql:
                reasoning = response.get("reasoning", "")
                # try extracting from ```sql block first
                sql_block = re.search(r'```sql\s*(.*?)\s*```', reasoning, re.DOTALL)
                if sql_block:
                    optimized_sql = sql_block.group(1).strip()
                else:
                    # try extracting optimized_sql key from embedded JSON
                    key_match = re.search(r'"optimized_sql"\s*:\s*"(.*?)"(?=\s*[,}])', reasoning, re.DOTALL)
                    if key_match:
                        optimized_sql = key_match.group(1).replace('\\n', '\n').replace('\\t', '\t')
                    else:
                        optimized_sql = sql
            
            # Clean up the SQL
            optimized_sql = self._clean_optimized_sql(optimized_sql)
            
            return optimized_sql
            
        except Exception as e:
            print(f"AI SQL optimization failed: {e}")
            # Fallback to basic static optimization
            return self._static_sql_optimization(sql, db_type)
    
    def _build_sql_optimization_prompt(self, sql: str, db_type: str, tables: List[str], joins: List[Dict], filters: List[str]) -> str:
        """Build prompt for AI SQL optimization"""

        return f"""You are a senior SQL Server DBA. Rewrite the stored procedure below so it runs faster while returning identical results.

ORIGINAL SQL:
```sql
{sql}
```

DATABASE TYPE: {db_type}

MANDATORY RULES — every rule must be applied, no exceptions:
1. Output MUST start with CREATE OR ALTER PROCEDURE with the exact same name and parameters as the input.
2. Return the COMPLETE procedure body — never truncate.
3. REMOVE every WITH (NOLOCK) hint — replace with nothing.
4. REMOVE SELECT * — replace with the actual column names used by the procedure (infer from context: OrderId, CustomerId, OrderDate, Status, TotalAmount from Orders; CustomerName, Country from Customers; Quantity, UnitPrice from OrderItems; ProductName, IsActive from Products).
5. Fix non-sargable WHERE predicates: replace YEAR(col) = @param with col >= DATEFROMPARTS(@param,1,1) AND col < DATEFROMPARTS(@param+1,1,1). Replace UPPER(col) = UPPER(@param) with col = @param.
6. Keep SET NOCOUNT ON; on a single line — never split it.
7. Format JOINs cleanly: INNER JOIN table alias ON condition — all on one line.
8. End with OPTION (RECOMPILE) on the same line as ORDER BY, no semicolon before OPTION.
9. Do NOT add extra blank lines inside BEGIN...END.

RESPOND IN JSON:
{{
    "optimized_sql": "complete runnable CREATE OR ALTER PROCEDURE ...",
    "changes_made": ["list of changes applied"],
    "confidence": 0.0-1.0
}}

The optimized_sql value must be properly escaped for JSON (use \\n for newlines inside the string)."""
    
    def _clean_optimized_sql(self, sql: str) -> str:
        """Clean and format optimized SQL"""
        # Decode escaped newlines/tabs from JSON string encoding
        sql = sql.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '')

        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*$', '', sql)

        # Only reformat if genuinely a single line (no real newlines at all)
        if '\n' not in sql and len(sql) > 100:
            sql = self._reformat_single_line_sql(sql)

        # Safety net: remove NOLOCK if AI missed it
        sql = re.sub(r'\s+WITH\s*\(\s*NOLOCK\s*\)', '', sql, flags=re.IGNORECASE)

        # Safety net: flag SELECT * if AI missed it
        sql = re.sub(r'\bSELECT\s+\*', 'SELECT /* TODO: specify columns */ *', sql, flags=re.IGNORECASE)

        # Fix SET NOCOUNT split across lines (SET NOCOUNT\nON -> SET NOCOUNT ON)
        sql = re.sub(r'SET\s+NOCOUNT\s*\n\s*ON', 'SET NOCOUNT ON', sql, flags=re.IGNORECASE)

        # Strip trailing whitespace per line
        lines = [line.rstrip() for line in sql.split('\n')]

        # Remove leading/trailing blank lines only
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        return '\n'.join(lines)

    def _reformat_single_line_sql(self, sql: str) -> str:
        """Add newlines to single-line SQL at keyword boundaries."""
        keywords = [
            'SELECT', 'FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN',
            'CROSS JOIN', 'JOIN', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY',
            'HAVING', 'INSERT INTO', 'UPDATE', 'SET', 'DELETE FROM', 'CREATE',
            'ALTER', 'BEGIN', 'END', 'DECLARE', 'EXEC', 'EXECUTE', 'UNION',
            'WITH', 'AS', 'ON',
        ]
        # Sort longest first to avoid partial matches
        keywords.sort(key=len, reverse=True)
        result = sql
        for kw in keywords:
            result = re.sub(rf'(?<![\w])({re.escape(kw)})(?![\w])', rf'\n\1', result, flags=re.IGNORECASE)
        # Indent lines after SELECT, WHERE, AND, OR, JOIN
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
    
    def _static_sql_optimization(self, sql: str, db_type: str) -> str:
        """Fallback static SQL optimization"""
        
        optimized = sql
        
        # Basic optimizations
        if "select *" in sql.lower():
            optimized = re.sub(r'\bselect\s+\*', 'SELECT /* TODO: Specify required columns */', optimized, flags=re.IGNORECASE)
        
        if "nolock" in sql.lower():
            optimized = re.sub(r'\s+with\s*\(\s*nolock\s*\)|\s+nolock\b', '', optimized, flags=re.IGNORECASE)
        
        # Add optimization note
        optimized += "\n\n-- Static optimization applied (AI unavailable)"
        
        return optimized
    
    def _static_optimization_analysis(self, sql: str, parsed_data: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Basic static optimization analysis (existing logic)"""
        
        lower_sql = sql.lower()
        tables = parsed_data.get("tables", [])
        joins = parsed_data.get("joins", [])
        filters = parsed_data.get("filters", [])
        
        performance_issues = []
        optimization_suggestions = []
        index_recommendations = []
        
        # Static performance issue detection
        if "select *" in lower_sql:
            performance_issues.append({
                "type": "column_selection",
                "severity": "Medium",
                "issue": "SELECT * usage",
                "description": "Selecting all columns increases I/O and memory usage",
                "evidence": "SELECT *"
            })
            optimization_suggestions.append({
                "type": "column_optimization",
                "priority": "Medium",
                "suggestion": "Select only required columns",
                "implementation": "Replace SELECT * with specific column names"
            })
        
        if " cursor " in f" {lower_sql} ":
            performance_issues.append({
                "type": "processing_pattern",
                "severity": "High", 
                "issue": "Cursor usage detected",
                "description": "Row-by-row processing is typically slower than set-based operations",
                "evidence": "CURSOR"
            })
            optimization_suggestions.append({
                "type": "algorithm_optimization",
                "priority": "High",
                "suggestion": "Replace cursor with set-based operations",
                "implementation": "Rewrite using UPDATE/INSERT/MERGE statements"
            })
        
        # Index recommendations based on filters and joins
        if filters or joins:
            for table in tables[:3]:  # Limit to first 3 tables
                filter_columns = self._extract_filter_columns(filters)
                join_columns = self._extract_join_columns(joins, table)
                
                if filter_columns or join_columns:
                    index_recommendations.append({
                        "table": table,
                        "type": "composite_index",
                        "columns": filter_columns + join_columns,
                        "reason": "Support WHERE clause and JOIN operations",
                        "script": self._generate_index_script(table, filter_columns + join_columns, db_type)
                    })
        
        estimated_improvement = {
            "confidence": "Static analysis only — run actual execution plan to measure real improvement."
        }
        
        return {
            "performance_issues": performance_issues,
            "optimization_suggestions": optimization_suggestions,
            "index_recommendations": index_recommendations,
            "estimated_improvement": estimated_improvement
        }
    
    def _ai_optimize(self, sql: str, static_results: Dict[str, Any], parsed_data: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Enhance optimization with AI analysis"""
        
        prompt = self._build_optimization_prompt(sql, static_results, parsed_data, db_type)
        
        try:
            response = self._call_ai(prompt)
            ai_results = self._parse_ai_optimization_response(response)
            
            return {
                **ai_results,
                "ai_reasoning": response.get("reasoning", ""),
                "confidence": response.get("confidence", 0.8),
                "processing_time": response.get("processing_time", 0)
            }
            
        except Exception as e:
            print(f"AI optimization failed, using static results: {e}")
            return {
                "enhanced_issues": static_results["performance_issues"],
                "enhanced_suggestions": static_results["optimization_suggestions"],
                "enhanced_indexes": static_results["index_recommendations"],
                "query_rewrites": [],
                "improvement_estimate": static_results["estimated_improvement"],
                "ai_reasoning": f"AI analysis unavailable: {str(e)}",
                "confidence": 0.6
            }
    
    def _build_optimization_prompt(self, sql: str, static_results: Dict[str, Any], parsed_data: Dict[str, Any], db_type: str) -> str:
        """Build prompt for AI optimization analysis"""

        tables = parsed_data.get("tables", [])
        joins = parsed_data.get("joins", [])
        static_issues = [issue["issue"] for issue in static_results["performance_issues"]]

        return f"""You are a senior SQL Server DBA. Analyze and rewrite this SQL for maximum performance.

SQL CODE:
```sql
{sql}
```

DATABASE TYPE: {db_type}
TABLES INVOLVED: {tables}
STATIC ISSUES FOUND: {static_issues}

MANDATORY REWRITE RULES — all must be applied:
1. Output in query_rewrites MUST start with CREATE OR ALTER PROCEDURE with the exact same name and parameters.
2. REMOVE every WITH (NOLOCK) hint completely.
3. REMOVE SELECT * — replace with explicit columns (OrderId, CustomerId, OrderDate, Status, TotalAmount from Orders; CustomerName, Country from Customers; Quantity, UnitPrice from OrderItems; ProductName, IsActive from Products).
4. Fix non-sargable predicates: YEAR(col)=@p → col>=DATEFROMPARTS(@p,1,1) AND col<DATEFROMPARTS(@p+1,1,1). UPPER(col)=UPPER(@p) → col=@p.
5. Keep SET NOCOUNT ON; on a single line.
6. Format each JOIN on one line: INNER JOIN table alias ON condition.
7. Add OPTION (RECOMPILE) at the end of the SELECT statement, same line as ORDER BY, no semicolon before OPTION.
8. Always close the procedure body with END on its own line after OPTION (RECOMPILE).

Respond in JSON format:
{{
    "enhanced_issues": [
        {{"type": "category", "severity": "High|Medium|Low", "issue": "issue_name", "description": "detailed_explanation", "evidence": "code_snippet"}}
    ],
    "enhanced_suggestions": [
        {{"type": "optimization_type", "priority": "High|Medium|Low", "suggestion": "what_to_do", "implementation": "how_to_implement", "expected_gain": "performance_improvement"}}
    ],
    "enhanced_indexes": [
        {{"table": "table_name", "type": "index_type", "columns": ["col1", "col2"], "reason": "why_needed", "impact": "expected_impact"}}
    ],
    "query_rewrites": ["complete CREATE OR ALTER PROCEDURE with all mandatory rules applied, newlines as \\n"],
    "improvement_estimate": {{
        "performance_gain": "percentage_range",
        "io_reduction": "percentage_range",
        "memory_impact": "impact_description",
        "confidence": "High|Medium|Low"
    }},
    "reasoning": "detailed_analysis_explanation",
    "confidence": 0.0-1.0
}}"""

    def _call_ai(self, prompt: str) -> Dict[str, Any]:
        """Call AI using Groq"""
        
        try:
            return groq_client.call_ai(self.config.system_message, prompt, timeout=20)
        except Exception as e:
            raise Exception(f"Failed to call AI: {str(e)}")
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from AI response"""
        
        # Look for JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Look for plain JSON
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        raise ValueError("No valid JSON found in response")
    
    def _parse_ai_optimization_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI optimization response"""
        
        return {
            "enhanced_issues": response.get("enhanced_issues", []),
            "enhanced_suggestions": response.get("enhanced_suggestions", []),
            "enhanced_indexes": response.get("enhanced_indexes", []),
            "query_rewrites": response.get("query_rewrites", []),
            "improvement_estimate": response.get("improvement_estimate", {}),
            "ai_reasoning": response.get("reasoning", ""),
            "confidence": response.get("confidence", 0.8)
        }
    
    def _extract_filter_columns(self, filters: List[str]) -> List[str]:
        """Extract column names from filter conditions"""
        columns = []
        for filter_condition in filters:
            # Simple regex to find column names before operators
            matches = re.findall(r'(\w+)\s*(?:=|>|<|>=|<=|LIKE|IN)', filter_condition, re.IGNORECASE)
            columns.extend(matches)
        return list(set(columns))[:3]  # Limit to 3 columns
    
    def _extract_join_columns(self, joins: List[Dict[str, str]], table: str) -> List[str]:
        """Extract join columns for a specific table"""
        columns = []
        for join in joins:
            if join.get("table") == table:
                condition = join.get("condition", "")
                # Extract column names from join condition
                matches = re.findall(r'(\w+)\s*=\s*(\w+)', condition)
                for match in matches:
                    columns.extend(match)
        return list(set(columns))[:2]  # Limit to 2 columns
    
    def _generate_index_script(self, table: str, columns: List[str], db_type: str) -> str:
        """Generate index creation script"""
        if not columns:
            return ""
        
        index_name = f"IX_{table}_{'_'.join(columns[:3])}"
        column_list = ', '.join(columns[:3])
        
        if db_type == "PostgreSQL":
            return f"CREATE INDEX CONCURRENTLY {index_name} ON {table} ({column_list});"
        elif db_type == "Oracle":
            return f"CREATE INDEX {index_name} ON {table} ({column_list});"
        else:  # SQL Server
            return f"CREATE NONCLUSTERED INDEX {index_name} ON {table} ({column_list});"

def test_sql_optimizer_agent():
    """Test the SQL Optimizer Agent"""
    
    print("[TEST] Testing SQL Optimizer Agent...")
    
    # Test SQL with performance issues
    test_sql = '''
    SELECT *
    FROM Customers c
    JOIN Orders o ON c.CustomerId = o.CustomerId
    WHERE UPPER(c.CustomerName) LIKE '%SMITH%'
        AND YEAR(o.OrderDate) = 2023
    ORDER BY o.OrderDate
    '''
    
    # Parsed data from Parser Agent
    parsed_data = {
        "tables": ["Customers", "Orders"],
        "joins": [{"type": "JOIN", "table": "Orders", "condition": "c.CustomerId = o.CustomerId"}],
        "filters": ["UPPER(c.CustomerName) LIKE '%SMITH%'", "YEAR(o.OrderDate) = 2023"]
    }
    
    try:
        optimizer = SQLOptimizerAgent()
        result = optimizer.optimize_sql(test_sql, parsed_data)
        
        print("[OK] SQL Optimizer Agent Results:")
        print(f"   Performance Issues: {len(result.performance_issues)} found")
        print(f"   Optimization Suggestions: {len(result.optimization_suggestions)} generated")
        print(f"   Index Recommendations: {len(result.index_recommendations)} created")
        print(f"   Query Rewrites: {len(result.query_rewrite_suggestions)} suggested")
        print(f"   Confidence: {result.confidence_score:.2f}")
        print(f"   Expected Improvement: {result.estimated_improvement.get('performance_gain', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_optimizer_agent()
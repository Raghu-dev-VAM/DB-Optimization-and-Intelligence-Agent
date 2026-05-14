"""
AI-Powered SQL Parser Agent
Enhances static SQL analysis with intelligent reasoning using Groq AI
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
class ParsedSQL:
    """Enhanced SQL parsing results with AI insights"""
    object_name: str
    object_type: str
    tables: List[str]
    joins: List[Dict[str, str]]
    filters: List[str]
    references: List[str]
    missing_references: List[str]
    ai_insights: Dict[str, Any]
    confidence_score: float

class SQLParserAgent:
    """AI-powered SQL Parser Agent using Groq"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("sql_parser")
        
    def parse_sql(self, sql: str, known_objects: Dict[str, Any] = None) -> ParsedSQL:
        """Parse SQL with AI enhancement"""
        
        # First, get basic static analysis (from existing code)
        static_results = self._static_parse(sql)
        
        # Then enhance with AI analysis
        ai_insights = self._ai_analyze(sql, static_results, known_objects or {})
        
        # Combine results
        return ParsedSQL(
            object_name=static_results["object_name"],
            object_type=static_results["object_type"],
            tables=ai_insights.get("enhanced_tables", static_results["tables"]),
            joins=ai_insights.get("enhanced_joins", static_results["joins"]),
            filters=ai_insights.get("enhanced_filters", static_results["filters"]),
            references=ai_insights.get("enhanced_references", static_results["references"]),
            missing_references=ai_insights.get("missing_references", []),
            ai_insights=ai_insights,
            confidence_score=ai_insights.get("confidence", 0.8)
        )
    
    def _static_parse(self, sql: str) -> Dict[str, Any]:
        """Use existing static parsing logic"""
        from sql_agent import (
            normalize_sql, classify_sql, extract_object_name, 
            extract_tables, extract_joins, extract_filters, extract_references
        )
        
        cleaned = normalize_sql(sql)
        object_type = classify_sql(cleaned, "auto")
        object_name = extract_object_name(cleaned, object_type)
        tables = extract_tables(cleaned)
        joins = extract_joins(cleaned)
        filters = extract_filters(cleaned)
        references = extract_references(cleaned)
        
        return {
            "object_name": object_name,
            "object_type": object_type,
            "tables": tables,
            "joins": joins,
            "filters": filters,
            "references": references
        }
    
    def _ai_analyze(self, sql: str, static_results: Dict[str, Any], known_objects: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance parsing with AI analysis"""
        
        prompt = self._build_analysis_prompt(sql, static_results, known_objects)
        
        try:
            response = self._call_ai(prompt)
            ai_results = self._parse_ai_response(response)
            
            return {
                **ai_results,
                "ai_explanation": response.get("explanation", ""),
                "confidence": response.get("confidence", 0.8),
                "processing_time": response.get("processing_time", 0)
            }
            
        except Exception as e:
            print(f"AI analysis failed, using static results: {e}")
            return {
                "enhanced_tables": static_results["tables"],
                "enhanced_joins": static_results["joins"],
                "enhanced_filters": static_results["filters"],
                "enhanced_references": static_results["references"],
                "missing_references": [],
                "ai_explanation": f"AI analysis unavailable: {str(e)}",
                "confidence": 0.6
            }
    
    def _build_analysis_prompt(self, sql: str, static_results: Dict[str, Any], known_objects: Dict[str, Any]) -> str:
        """Build prompt for AI analysis"""
        
        known_list = list(known_objects.keys()) if known_objects else []
        
        return f"""You are a SQL Parser Agent. Analyze this SQL code and enhance the static analysis results.

SQL CODE:
```sql
{sql}
```

STATIC ANALYSIS RESULTS:
- Object Type: {static_results['object_type']}
- Object Name: {static_results['object_name']}
- Tables Found: {static_results['tables']}
- Joins Found: {len(static_results['joins'])} joins
- Filters Found: {len(static_results['filters'])} filters
- References Found: {static_results['references']}

KNOWN OBJECTS IN MEMORY: {known_list}

TASKS:
1. Verify and enhance the table list (look for aliases, CTEs, temp tables)
2. Identify any missing referenced stored procedures/functions
3. Analyze join relationships and complexity
4. Examine filter conditions for performance implications
5. Check for dynamic SQL patterns
6. Identify any missing dependencies

Respond in JSON format:
{{
    "enhanced_tables": ["list of all tables including missed ones"],
    "enhanced_joins": [
        {{"type": "JOIN_TYPE", "table": "table_name", "condition": "join_condition", "complexity": "low|medium|high"}}
    ],
    "enhanced_filters": ["list of filter conditions"],
    "enhanced_references": ["list of stored procedures/functions called"],
    "missing_references": ["procedures not in known objects"],
    "dynamic_sql_detected": true/false,
    "complexity_score": 1-10,
    "explanation": "Brief explanation of findings",
    "confidence": 0.0-1.0
}}"""

    def _call_ai(self, prompt: str) -> Dict[str, Any]:
        """Call AI using Groq"""
        
        try:
            return groq_client.call_ai(self.config.system_message, prompt, timeout=15)
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
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI response"""
        
        return {
            "enhanced_tables": response.get("enhanced_tables", []),
            "enhanced_joins": response.get("enhanced_joins", []),
            "enhanced_filters": response.get("enhanced_filters", []),
            "enhanced_references": response.get("enhanced_references", []),
            "missing_references": response.get("missing_references", []),
            "dynamic_sql_detected": response.get("dynamic_sql_detected", False),
            "complexity_score": response.get("complexity_score", 5),
            "ai_explanation": response.get("explanation", ""),
            "confidence": response.get("confidence", 0.8)
        }

def test_sql_parser_agent():
    """Test the SQL Parser Agent"""
    
    print("[TEST] Testing SQL Parser Agent...")
    
    # Test SQL
    test_sql = '''
    CREATE PROCEDURE usp_GetCustomerOrders
        @CustomerId INT,
        @StartDate DATETIME = NULL
    AS
    BEGIN
        SELECT 
            c.CustomerName,
            o.OrderId,
            o.OrderDate,
            oi.ProductName,
            oi.Quantity * oi.UnitPrice as LineTotal
        FROM Customers c
        INNER JOIN Orders o ON c.CustomerId = o.CustomerId
        LEFT JOIN OrderItems oi ON o.OrderId = oi.OrderId
        WHERE c.CustomerId = @CustomerId
            AND (@StartDate IS NULL OR o.OrderDate >= @StartDate)
        ORDER BY o.OrderDate DESC
        
        EXEC usp_LogCustomerAccess @CustomerId
    END
    '''
    
    # Known objects for testing
    known_objects = {
        "usp_LogCustomerAccess": {"type": "Stored Procedure"},
        "Customers": {"type": "Table"},
        "Orders": {"type": "Table"}
    }
    
    try:
        parser = SQLParserAgent()
        result = parser.parse_sql(test_sql, known_objects)
        
        print("[OK] SQL Parser Agent Results:")
        print(f"   Object: {result.object_name} ({result.object_type})")
        print(f"   Tables: {result.tables}")
        print(f"   Joins: {len(result.joins)} joins detected")
        print(f"   References: {result.references}")
        print(f"   Missing: {result.missing_references}")
        print(f"   Confidence: {result.confidence_score:.2f}")
        print(f"   AI Insights: {result.ai_insights.get('complexity_score', 'N/A')}/10 complexity")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_parser_agent()
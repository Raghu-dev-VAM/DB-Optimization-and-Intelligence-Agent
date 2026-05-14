"""
AI-Powered SQL Security Agent
Identifies security vulnerabilities and provides security recommendations using Groq AI
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
class SecurityAnalysisResult:
    """SQL security analysis results"""
    vulnerabilities: List[Dict[str, Any]]
    security_recommendations: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    compliance_issues: List[Dict[str, Any]]
    remediation_steps: List[Dict[str, Any]]
    ai_insights: Dict[str, Any]
    confidence_score: float

class SQLSecurityAgent:
    """AI-powered SQL Security Agent using Groq"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("security")
        
    def analyze_security(self, sql: str, parsed_data: Dict[str, Any] = None, db_type: str = "SQL Server") -> SecurityAnalysisResult:
        """Analyze SQL for security vulnerabilities and risks"""
        
        # Get basic static security analysis first
        static_results = self._static_security_analysis(sql, parsed_data or {}, db_type)
        
        # Enhance with AI analysis
        ai_insights = self._ai_security_analyze(sql, static_results, parsed_data or {}, db_type)
        
        # Combine results
        return SecurityAnalysisResult(
            vulnerabilities=ai_insights.get("enhanced_vulnerabilities", static_results["vulnerabilities"]),
            security_recommendations=ai_insights.get("enhanced_recommendations", static_results["security_recommendations"]),
            risk_assessment=ai_insights.get("enhanced_risk_assessment", static_results["risk_assessment"]),
            compliance_issues=ai_insights.get("compliance_issues", []),
            remediation_steps=ai_insights.get("remediation_steps", static_results["remediation_steps"]),
            ai_insights=ai_insights,
            confidence_score=ai_insights.get("confidence", 0.8)
        )
    
    def _static_security_analysis(self, sql: str, parsed_data: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Basic static security analysis"""
        
        lower_sql = sql.lower()
        vulnerabilities = []
        security_recommendations = []
        remediation_steps = []
        
        # SQL Injection Detection
        if self._detect_sql_injection_patterns(sql):
            vulnerabilities.append({
                "type": "sql_injection",
                "severity": "Critical",
                "vulnerability": "Potential SQL Injection",
                "description": "Dynamic SQL construction detected without proper parameterization",
                "evidence": self._extract_dynamic_sql_evidence(sql),
                "cwe": "CWE-89"
            })
            security_recommendations.append({
                "type": "parameterization",
                "priority": "Critical",
                "recommendation": "Use parameterized queries",
                "implementation": "Replace string concatenation with parameter placeholders"
            })
            remediation_steps.append({
                "step": 1,
                "action": "Replace dynamic SQL with parameterized queries",
                "code_example": "Use @param instead of concatenating values"
            })
        
        # Privilege Escalation Detection
        if self._detect_privilege_issues(sql):
            vulnerabilities.append({
                "type": "privilege_escalation",
                "severity": "High",
                "vulnerability": "Potential Privilege Escalation",
                "description": "Code may execute with elevated privileges",
                "evidence": self._extract_privilege_evidence(sql),
                "cwe": "CWE-250"
            })
        
        # Information Disclosure
        if "select *" in lower_sql and ("user" in lower_sql or "password" in lower_sql or "credential" in lower_sql):
            vulnerabilities.append({
                "type": "information_disclosure",
                "severity": "Medium",
                "vulnerability": "Potential Information Disclosure",
                "description": "Query may expose sensitive information",
                "evidence": "SELECT * with potential sensitive data",
                "cwe": "CWE-200"
            })
        
        # Missing Error Handling
        if self._detect_missing_error_handling(sql):
            vulnerabilities.append({
                "type": "error_handling",
                "severity": "Medium", 
                "vulnerability": "Missing Error Handling",
                "description": "Inadequate error handling may expose system information",
                "evidence": "No TRY/CATCH blocks found",
                "cwe": "CWE-209"
            })
            remediation_steps.append({
                "step": 2,
                "action": "Add comprehensive error handling",
                "code_example": "Wrap operations in TRY/CATCH blocks"
            })
        
        # Access Control Issues
        if self._detect_access_control_issues(sql):
            vulnerabilities.append({
                "type": "access_control",
                "severity": "High",
                "vulnerability": "Insufficient Access Control",
                "description": "Query may bypass access control mechanisms",
                "evidence": self._extract_access_control_evidence(sql),
                "cwe": "CWE-284"
            })
        
        # Risk Assessment
        critical_count = sum(1 for v in vulnerabilities if v["severity"] == "Critical")
        high_count = sum(1 for v in vulnerabilities if v["severity"] == "High")
        medium_count = sum(1 for v in vulnerabilities if v["severity"] == "Medium")
        
        if critical_count > 0:
            risk_level = "Critical"
        elif high_count > 0:
            risk_level = "High"
        elif medium_count > 0:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        risk_assessment = {
            "overall_risk": risk_level,
            "critical_issues": critical_count,
            "high_issues": high_count,
            "medium_issues": medium_count,
            "security_score": max(0, 100 - (critical_count * 40 + high_count * 20 + medium_count * 10)),
            "deployment_recommendation": "Block" if critical_count > 0 else "Review" if high_count > 0 else "Approve"
        }
        
        return {
            "vulnerabilities": vulnerabilities,
            "security_recommendations": security_recommendations,
            "risk_assessment": risk_assessment,
            "remediation_steps": remediation_steps
        }
    
    def _detect_sql_injection_patterns(self, sql: str) -> bool:
        """Detect potential SQL injection vulnerabilities"""
        patterns = [
            r"exec\s*\(\s*@\w+\s*\+",  # Dynamic SQL with concatenation
            r"execute\s*\(\s*@\w+\s*\+",
            r"'\s*\+\s*@\w+\s*\+\s*'",  # String concatenation with parameters
            r"@\w+\s*\+\s*'",
            r"'\s*\+\s*@\w+",
            r"sp_executesql.*\+",  # sp_executesql with concatenation
        ]
        
        for pattern in patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return True
        return False
    
    def _extract_dynamic_sql_evidence(self, sql: str) -> str:
        """Extract evidence of dynamic SQL construction"""
        patterns = [
            r"exec\s*\([^)]+\)",
            r"execute\s*\([^)]+\)",
            r"sp_executesql[^;]+",
            r"@\w+\s*\+\s*'[^']*'",
            r"'\s*\+\s*@\w+"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                return match.group(0)
        return "Dynamic SQL detected"
    
    def _detect_privilege_issues(self, sql: str) -> bool:
        """Detect potential privilege escalation issues"""
        lower_sql = sql.lower()
        risky_patterns = [
            "with execute as",
            "execute as owner",
            "execute as caller",
            "setuser",
            "openrowset",
            "opendatasource",
            "xp_cmdshell",
            "sp_configure"
        ]
        
        return any(pattern in lower_sql for pattern in risky_patterns)
    
    def _extract_privilege_evidence(self, sql: str) -> str:
        """Extract evidence of privilege escalation"""
        patterns = [
            r"with\s+execute\s+as\s+\w+",
            r"execute\s+as\s+\w+",
            r"xp_cmdshell[^;]*",
            r"openrowset[^)]+\)",
            r"opendatasource[^)]+\)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                return match.group(0)
        return "Privilege escalation pattern detected"
    
    def _detect_missing_error_handling(self, sql: str) -> bool:
        """Detect missing error handling in stored procedures"""
        lower_sql = sql.lower()
        
        # Check if it's a stored procedure or function
        if not ("create procedure" in lower_sql or "create function" in lower_sql):
            return False
        
        # Check for write operations without error handling
        has_write_ops = any(op in lower_sql for op in ["insert", "update", "delete", "merge"])
        has_error_handling = "try" in lower_sql and "catch" in lower_sql
        
        return has_write_ops and not has_error_handling
    
    def _detect_access_control_issues(self, sql: str) -> bool:
        """Detect potential access control bypass"""
        lower_sql = sql.lower()
        
        # Look for queries that might bypass row-level security
        bypass_patterns = [
            "where 1=1",
            "or 1=1", 
            "where '1'='1'",
            "or '1'='1'",
            "union select",
            "-- ",
            "/*"
        ]
        
        return any(pattern in lower_sql for pattern in bypass_patterns)
    
    def _extract_access_control_evidence(self, sql: str) -> str:
        """Extract evidence of access control issues"""
        patterns = [
            r"where\s+1\s*=\s*1",
            r"or\s+1\s*=\s*1",
            r"where\s+'1'\s*=\s*'1'",
            r"union\s+select[^;]+",
            r"--[^\r\n]*",
            r"/\*.*?\*/"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)
        return "Access control bypass pattern detected"
    
    def _ai_security_analyze(self, sql: str, static_results: Dict[str, Any], parsed_data: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Enhance security analysis with AI"""
        
        prompt = self._build_security_prompt(sql, static_results, parsed_data, db_type)
        
        try:
            response = self._call_ai(prompt)
            ai_results = self._parse_ai_security_response(response)
            
            return {
                **ai_results,
                "ai_reasoning": response.get("reasoning", ""),
                "confidence": response.get("confidence", 0.8),
                "processing_time": response.get("processing_time", 0)
            }
            
        except Exception as e:
            print(f"AI security analysis failed, using static results: {e}")
            return {
                "enhanced_vulnerabilities": static_results["vulnerabilities"],
                "enhanced_recommendations": static_results["security_recommendations"],
                "enhanced_risk_assessment": static_results["risk_assessment"],
                "compliance_issues": [],
                "remediation_steps": static_results["remediation_steps"],
                "ai_reasoning": f"AI analysis unavailable: {str(e)}",
                "confidence": 0.6
            }
    
    def _build_security_prompt(self, sql: str, static_results: Dict[str, Any], parsed_data: Dict[str, Any], db_type: str) -> str:
        """Build prompt for AI security analysis"""
        
        static_vulns = [v["vulnerability"] for v in static_results["vulnerabilities"]]
        tables = parsed_data.get("tables", [])
        
        return f"""You are a SQL Security Agent. Analyze this SQL code for security vulnerabilities and risks.

SQL CODE:
```sql
{sql}
```

DATABASE TYPE: {db_type}
TABLES INVOLVED: {tables}
STATIC VULNERABILITIES FOUND: {static_vulns}

SECURITY ANALYSIS TASKS:
1. Identify SQL injection vulnerabilities (beyond basic patterns)
2. Detect privilege escalation risks
3. Find information disclosure issues
4. Check for authentication/authorization bypasses
5. Analyze input validation weaknesses
6. Assess compliance with security standards (OWASP, CWE)
7. Evaluate error handling security implications

Focus on:
- Advanced SQL injection techniques (blind, time-based, union-based)
- Business logic security flaws
- Data exposure risks
- Audit trail completeness
- Principle of least privilege violations
- Secure coding practices

Respond in JSON format:
{{
    "enhanced_vulnerabilities": [
        {{"type": "vuln_category", "severity": "Critical|High|Medium|Low", "vulnerability": "vuln_name", "description": "detailed_explanation", "evidence": "code_snippet", "cwe": "CWE-XXX"}}
    ],
    "enhanced_recommendations": [
        {{"type": "security_control", "priority": "Critical|High|Medium|Low", "recommendation": "what_to_implement", "implementation": "how_to_implement"}}
    ],
    "enhanced_risk_assessment": {{
        "overall_risk": "Critical|High|Medium|Low",
        "security_score": 0-100,
        "deployment_recommendation": "Block|Review|Approve",
        "business_impact": "impact_description"
    }},
    "compliance_issues": [
        {{"standard": "OWASP|PCI-DSS|SOX|GDPR", "requirement": "requirement_name", "violation": "what_is_violated", "remediation": "how_to_fix"}}
    ],
    "remediation_steps": [
        {{"step": 1, "action": "what_to_do", "code_example": "example_implementation", "priority": "Critical|High|Medium|Low"}}
    ],
    "reasoning": "detailed_security_analysis",
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
    
    def _parse_ai_security_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI security response"""
        
        return {
            "enhanced_vulnerabilities": response.get("enhanced_vulnerabilities", []),
            "enhanced_recommendations": response.get("enhanced_recommendations", []),
            "enhanced_risk_assessment": response.get("enhanced_risk_assessment", {}),
            "compliance_issues": response.get("compliance_issues", []),
            "remediation_steps": response.get("remediation_steps", []),
            "ai_reasoning": response.get("reasoning", ""),
            "confidence": response.get("confidence", 0.8)
        }

def test_sql_security_agent():
    """Test the SQL Security Agent"""
    
    print("[TEST] Testing SQL Security Agent...")
    
    # Test SQL with security issues
    test_sql = '''
    CREATE PROCEDURE usp_GetUserData
        @UserId NVARCHAR(50),
        @Filter NVARCHAR(MAX)
    AS
    BEGIN
        DECLARE @SQL NVARCHAR(MAX)
        SET @SQL = 'SELECT * FROM Users WHERE UserId = ' + QUOTENAME(@UserId) + ' AND ' + @Filter
        
        EXEC(@SQL)
    END
    '''
    
    # Parsed data from Parser Agent
    parsed_data = {
        "tables": ["Users"],
        "joins": [],
        "filters": ["UserId = @UserId", "@Filter"],
        "references": []
    }
    
    try:
        security_agent = SQLSecurityAgent()
        result = security_agent.analyze_security(test_sql, parsed_data)
        
        print("[OK] SQL Security Agent Results:")
        print(f"   Vulnerabilities: {len(result.vulnerabilities)} found")
        for vuln in result.vulnerabilities:
            print(f"     - {vuln['severity']}: {vuln['vulnerability']}")
        print(f"   Security Recommendations: {len(result.security_recommendations)} generated")
        print(f"   Risk Assessment: {result.risk_assessment.get('overall_risk', 'Unknown')} risk")
        print(f"   Security Score: {result.risk_assessment.get('security_score', 'N/A')}/100")
        print(f"   Confidence: {result.confidence_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_security_agent()
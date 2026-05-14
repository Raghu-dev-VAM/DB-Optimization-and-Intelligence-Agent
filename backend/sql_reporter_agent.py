"""
AI-Powered SQL Reporter Agent
Generates comprehensive analysis reports combining insights from all other agents using Groq AI
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
class ReportGenerationResult:
    """SQL report generation results"""
    executive_summary: str
    technical_report: str
    recommendations_report: str
    deployment_guide: str
    risk_assessment_report: str
    artifacts: Dict[str, str]
    ai_insights: Dict[str, Any]
    confidence_score: float

class SQLReporterAgent:
    """AI-powered SQL Reporter Agent using Groq"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("reporter")
        
    def generate_reports(self, 
                        parsed_results: Dict[str, Any] = None,
                        optimization_results: Dict[str, Any] = None,
                        security_results: Dict[str, Any] = None,
                        dependency_results: Dict[str, Any] = None,
                        object_info: Dict[str, Any] = None) -> ReportGenerationResult:
        """Generate comprehensive reports from all agent analyses"""
        
        # Compile all analysis results
        all_results = {
            "parsed": parsed_results or {},
            "optimization": optimization_results or {},
            "security": security_results or {},
            "dependency": dependency_results or {},
            "object_info": object_info or {}
        }
        
        # Generate static reports first
        static_reports = self._generate_static_reports(all_results)
        
        # Enhance with AI-generated reports
        ai_insights = self._ai_generate_reports(all_results, static_reports)
        
        # Combine results
        return ReportGenerationResult(
            executive_summary=ai_insights.get("enhanced_executive_summary", static_reports["executive_summary"]),
            technical_report=ai_insights.get("enhanced_technical_report", static_reports["technical_report"]),
            recommendations_report=ai_insights.get("enhanced_recommendations", static_reports["recommendations_report"]),
            deployment_guide=ai_insights.get("enhanced_deployment_guide", static_reports["deployment_guide"]),
            risk_assessment_report=ai_insights.get("enhanced_risk_assessment", static_reports["risk_assessment_report"]),
            artifacts=ai_insights.get("enhanced_artifacts", static_reports["artifacts"]),
            ai_insights=ai_insights,
            confidence_score=ai_insights.get("confidence", 0.8)
        )
    
    def _generate_static_reports(self, all_results: Dict[str, Any]) -> Dict[str, str]:
        """Generate basic static reports"""
        
        object_info = all_results.get("object_info", {})
        parsed = all_results.get("parsed", {})
        optimization = all_results.get("optimization", {})
        security = all_results.get("security", {})
        dependency = all_results.get("dependency", {})
        
        # Executive Summary
        executive_summary = self._generate_executive_summary(object_info, optimization, security, dependency)
        
        # Technical Report
        technical_report = self._generate_technical_report(parsed, optimization, security, dependency)
        
        # Recommendations Report
        recommendations_report = self._generate_recommendations_report(optimization, security, dependency)
        
        # Deployment Guide
        deployment_guide = self._generate_deployment_guide(dependency, security, optimization)
        
        # Risk Assessment Report
        risk_assessment_report = self._generate_risk_assessment_report(security, optimization, dependency)
        
        # Artifacts
        artifacts = self._generate_artifacts(all_results)
        
        return {
            "executive_summary": executive_summary,
            "technical_report": technical_report,
            "recommendations_report": recommendations_report,
            "deployment_guide": deployment_guide,
            "risk_assessment_report": risk_assessment_report,
            "artifacts": artifacts
        }
    
    def _generate_executive_summary(self, object_info: Dict[str, Any], 
                                  optimization: Dict[str, Any], 
                                  security: Dict[str, Any], 
                                  dependency: Dict[str, Any]) -> str:
        """Generate executive summary"""
        
        object_name = object_info.get("object_name", "SQL Object")
        object_type = object_info.get("object_type", "Unknown")
        
        # Count issues by severity
        perf_issues = len(optimization.get("performance_issues", []))
        security_vulns = len(security.get("vulnerabilities", []))
        missing_deps = len(dependency.get("missing_objects", []))
        
        # Determine overall status
        critical_security = any(v.get("severity") == "Critical" for v in security.get("vulnerabilities", []))
        high_perf_issues = any(i.get("severity") == "High" for i in optimization.get("performance_issues", []))
        
        if critical_security:
            overall_status = "[CRITICAL] Security vulnerabilities require immediate attention"
        elif high_perf_issues or missing_deps > 0:
            overall_status = "[REVIEW REQUIRED] Performance and dependency issues found"
        else:
            overall_status = "[ACCEPTABLE] Minor issues identified"
        
        summary = f"""# Executive Summary: {object_name}
        
## Overall Assessment
**Status**: {overall_status}
**Object Type**: {object_type}
**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Key Findings
- **Performance Issues**: {perf_issues} identified
- **Security Vulnerabilities**: {security_vulns} found
- **Missing Dependencies**: {missing_deps} detected
- **Impact Level**: {dependency.get("impact_analysis", {}).get("impact_level", "Unknown")}

## Immediate Actions Required
"""
        
        if critical_security:
            summary += "1. **URGENT**: Address critical security vulnerabilities before deployment\n"
        if missing_deps > 0:
            summary += f"2. **HIGH**: Resolve {missing_deps} missing dependencies\n"
        if high_perf_issues:
            summary += "3. **MEDIUM**: Optimize performance bottlenecks\n"
        
        summary += f"""
## Business Impact
- **Deployment Risk**: {dependency.get("impact_analysis", {}).get("change_risk", "Unknown")}
- **Performance Impact**: {optimization.get("estimated_improvement", {}).get("performance_gain", "Unknown")}
- **Security Risk**: {security.get("risk_assessment", {}).get("overall_risk", "Unknown")}
"""
        
        return summary
    
    def _generate_technical_report(self, parsed: Dict[str, Any], 
                                 optimization: Dict[str, Any], 
                                 security: Dict[str, Any], 
                                 dependency: Dict[str, Any]) -> str:
        """Generate detailed technical report"""
        
        report = f"""# Technical Analysis Report
        
## Code Structure Analysis
"""
        
        if parsed:
            tables = parsed.get("tables", [])
            joins = parsed.get("joins", [])
            report += f"""
### Database Objects
- **Tables Referenced**: {len(tables)} ({', '.join(tables[:5])})
- **Joins Used**: {len(joins)} joins
- **Complexity Score**: {parsed.get("ai_insights", {}).get("complexity_score", "N/A")}/10
"""
        
        # Performance Analysis
        if optimization:
            perf_issues = optimization.get("performance_issues", [])
            report += f"""
## Performance Analysis
### Issues Identified ({len(perf_issues)})
"""
            for i, issue in enumerate(perf_issues[:5], 1):
                report += f"{i}. **{issue.get('issue', 'Unknown')}** ({issue.get('severity', 'Unknown')})\n"
                report += f"   - {issue.get('description', 'No description')}\n"
        
        # Security Analysis
        if security:
            vulnerabilities = security.get("vulnerabilities", [])
            report += f"""
## Security Analysis
### Vulnerabilities Found ({len(vulnerabilities)})
"""
            for i, vuln in enumerate(vulnerabilities[:5], 1):
                report += f"{i}. **{vuln.get('vulnerability', 'Unknown')}** ({vuln.get('severity', 'Unknown')})\n"
                report += f"   - CWE: {vuln.get('cwe', 'N/A')}\n"
                report += f"   - {vuln.get('description', 'No description')}\n"
        
        # Dependency Analysis
        if dependency:
            deps = dependency.get("dependencies", {})
            missing = dependency.get("missing_objects", [])
            report += f"""
## Dependency Analysis
### Dependencies ({sum(len(d) for d in deps.values())})
"""
            for obj, obj_deps in deps.items():
                if obj_deps:
                    report += f"- **{obj}**: {', '.join(obj_deps[:3])}\n"
            
            if missing:
                report += f"""
### Missing Objects ({len(missing)})
"""
                for obj in missing[:5]:
                    report += f"- {obj}\n"
        
        return report
    
    def _generate_recommendations_report(self, optimization: Dict[str, Any], 
                                       security: Dict[str, Any], 
                                       dependency: Dict[str, Any]) -> str:
        """Generate recommendations report"""
        
        report = """# Recommendations Report

## Priority Actions
"""
        
        priority_actions = []
        
        # Security recommendations (highest priority)
        if security:
            security_recs = security.get("security_recommendations", [])
            for rec in security_recs:
                if rec.get("priority") in ["Critical", "High"]:
                    priority_actions.append({
                        "priority": 1 if rec.get("priority") == "Critical" else 2,
                        "category": "Security",
                        "action": rec.get("recommendation", ""),
                        "implementation": rec.get("implementation", "")
                    })
        
        # Performance recommendations
        if optimization:
            opt_suggestions = optimization.get("optimization_suggestions", [])
            for sug in opt_suggestions:
                if sug.get("priority") in ["High", "Medium"]:
                    priority_actions.append({
                        "priority": 2 if sug.get("priority") == "High" else 3,
                        "category": "Performance",
                        "action": sug.get("suggestion", ""),
                        "implementation": sug.get("implementation", "")
                    })
        
        # Dependency recommendations
        if dependency:
            missing_objects = dependency.get("missing_objects", [])
            if missing_objects:
                priority_actions.append({
                    "priority": 2,
                    "category": "Dependencies",
                    "action": f"Resolve {len(missing_objects)} missing dependencies",
                    "implementation": f"Add definitions for: {', '.join(missing_objects[:3])}"
                })
        
        # Sort by priority and generate report
        priority_actions.sort(key=lambda x: x["priority"])
        
        for i, action in enumerate(priority_actions[:10], 1):
            report += f"""
### {i}. {action['category']}: {action['action']}
**Implementation**: {action['implementation']}
"""
        
        # Index recommendations
        if optimization:
            index_recs = optimization.get("index_recommendations", [])
            if index_recs:
                report += """
## Index Recommendations
"""
                for rec in index_recs[:5]:
                    report += f"- **{rec.get('table', 'Unknown')}**: {rec.get('reason', 'Performance optimization')}\n"
        
        return report
    
    def _generate_deployment_guide(self, dependency: Dict[str, Any], 
                                 security: Dict[str, Any], 
                                 optimization: Dict[str, Any]) -> str:
        """Generate deployment guide"""
        
        guide = """# Deployment Guide

## Pre-Deployment Checklist
"""
        
        # Security checks
        if security:
            critical_vulns = [v for v in security.get("vulnerabilities", []) if v.get("severity") == "Critical"]
            if critical_vulns:
                guide += "- [ ] **CRITICAL**: Resolve all critical security vulnerabilities\n"
            
            guide += "- [ ] Security review completed and approved\n"
        
        # Dependency checks
        if dependency:
            missing_objects = dependency.get("missing_objects", [])
            if missing_objects:
                guide += f"- [ ] **REQUIRED**: Deploy missing dependencies: {', '.join(missing_objects[:3])}\n"
            
            deployment_order = dependency.get("deployment_order", [])
            if deployment_order:
                guide += """
## Deployment Order
"""
                for i, obj in enumerate(deployment_order[:10], 1):
                    guide += f"{i}. {obj}\n"
        
        # Performance considerations
        if optimization:
            index_recs = optimization.get("index_recommendations", [])
            if index_recs:
                guide += """
## Post-Deployment Steps
1. Create recommended indexes
2. Update statistics
3. Monitor performance metrics
"""
        
        guide += """
## Rollback Plan
1. Keep backup of original objects
2. Document all changes made
3. Test rollback procedure in non-production environment
"""
        
        return guide
    
    def _generate_risk_assessment_report(self, security: Dict[str, Any], 
                                       optimization: Dict[str, Any], 
                                       dependency: Dict[str, Any]) -> str:
        """Generate risk assessment report"""
        
        report = """# Risk Assessment Report

## Risk Summary
"""
        
        # Calculate overall risk
        security_risk = security.get("risk_assessment", {}).get("overall_risk", "Low")
        perf_risk = "High" if any(i.get("severity") == "High" for i in optimization.get("performance_issues", [])) else "Medium"
        dependency_risk = dependency.get("impact_analysis", {}).get("change_risk", "Low")
        
        report += f"""
- **Security Risk**: {security_risk}
- **Performance Risk**: {perf_risk}
- **Dependency Risk**: {dependency_risk}
"""
        
        # Risk details
        if security:
            security_score = security.get("risk_assessment", {}).get("security_score", 100)
            report += f"""
## Security Risk Details
- **Security Score**: {security_score}/100
- **Deployment Recommendation**: {security.get("risk_assessment", {}).get("deployment_recommendation", "Review")}
"""
        
        if dependency:
            impact_level = dependency.get("impact_analysis", {}).get("impact_level", "Unknown")
            report += f"""
## Change Impact Assessment
- **Impact Level**: {impact_level}
- **Deployment Complexity**: {dependency.get("impact_analysis", {}).get("deployment_complexity", "Unknown")}
"""
        
        return report
    
    def _generate_artifacts(self, all_results: Dict[str, Any]) -> Dict[str, str]:
        """Generate downloadable artifacts"""
        
        artifacts = {}
        
        # Optimization scripts
        optimization = all_results.get("optimization", {})
        if optimization:
            index_recs = optimization.get("index_recommendations", [])
            if index_recs:
                index_script = "\n".join([rec.get("script", "") for rec in index_recs if rec.get("script")])
                artifacts["index_creation_script"] = index_script or "-- No index scripts generated"
        
        # Security remediation
        security = all_results.get("security", {})
        if security:
            remediation_steps = security.get("remediation_steps", [])
            if remediation_steps:
                remediation_script = "\n".join([f"-- Step {step.get('step', 1)}: {step.get('action', '')}" 
                                              for step in remediation_steps])
                artifacts["security_remediation_guide"] = remediation_script or "-- No remediation steps"
        
        # Deployment checklist
        dependency = all_results.get("dependency", {})
        if dependency:
            deployment_order = dependency.get("deployment_order", [])
            checklist = "\n".join([f"- [ ] Deploy {obj}" for obj in deployment_order])
            artifacts["deployment_checklist"] = checklist or "-- No deployment order specified"
        
        return artifacts
    
    def _ai_generate_reports(self, all_results: Dict[str, Any], static_reports: Dict[str, str]) -> Dict[str, Any]:
        """Enhance reports with AI generation"""
        
        prompt = self._build_reporting_prompt(all_results, static_reports)
        
        try:
            response = self._call_ai(prompt)
            ai_results = self._parse_ai_reporting_response(response)
            
            return {
                **ai_results,
                "ai_reasoning": response.get("reasoning", ""),
                "confidence": response.get("confidence", 0.8),
                "processing_time": response.get("processing_time", 0)
            }
            
        except Exception as e:
            print(f"AI report generation failed, using static reports: {e}")
            return {
                "enhanced_executive_summary": static_reports["executive_summary"],
                "enhanced_technical_report": static_reports["technical_report"],
                "enhanced_recommendations": static_reports["recommendations_report"],
                "enhanced_deployment_guide": static_reports["deployment_guide"],
                "enhanced_risk_assessment": static_reports["risk_assessment_report"],
                "enhanced_artifacts": static_reports["artifacts"],
                "ai_reasoning": f"AI analysis unavailable: {str(e)}",
                "confidence": 0.6
            }
    
    def _build_reporting_prompt(self, all_results: Dict[str, Any], static_reports: Dict[str, str]) -> str:
        """Build prompt for AI report generation"""
        
        # Summarize key findings
        security_issues = len(all_results.get("security", {}).get("vulnerabilities", []))
        perf_issues = len(all_results.get("optimization", {}).get("performance_issues", []))
        missing_deps = len(all_results.get("dependency", {}).get("missing_objects", []))
        
        return f"""You are a SQL Reporter Agent. Generate comprehensive, professional reports based on multi-agent analysis results.

ANALYSIS SUMMARY:
- Security Issues: {security_issues} found
- Performance Issues: {perf_issues} identified  
- Missing Dependencies: {missing_deps} detected

STATIC REPORTS GENERATED:
{static_reports.get("executive_summary", "")[:500]}...

REPORTING TASKS:
1. Enhance executive summary with business impact analysis
2. Improve technical report with actionable insights
3. Prioritize recommendations by business value
4. Create comprehensive deployment strategy
5. Provide risk mitigation strategies

Focus on:
- Business impact and ROI of fixes
- Clear prioritization of actions
- Practical implementation guidance
- Risk mitigation strategies
- Stakeholder communication

Respond in JSON format:
{{
    "enhanced_executive_summary": "improved_executive_summary_with_business_context",
    "enhanced_recommendations": "prioritized_actionable_recommendations",
    "key_insights": [
        {{"insight": "business_insight", "impact": "High|Medium|Low", "action": "recommended_action"}}
    ],
    "stakeholder_summary": "summary_for_non_technical_stakeholders",
    "reasoning": "report_generation_analysis",
    "confidence": 0.0-1.0
}}"""

    def _call_ai(self, prompt: str) -> Dict[str, Any]:
        """Call AI using Groq"""
        
        try:
            return groq_client.call_ai(self.config.system_message, prompt, timeout=25)
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
    
    def _parse_ai_reporting_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI reporting response"""
        
        return {
            "enhanced_executive_summary": response.get("enhanced_executive_summary", ""),
            "enhanced_recommendations": response.get("enhanced_recommendations", ""),
            "key_insights": response.get("key_insights", []),
            "stakeholder_summary": response.get("stakeholder_summary", ""),
            "ai_reasoning": response.get("reasoning", ""),
            "confidence": response.get("confidence", 0.8)
        }

def test_sql_reporter_agent():
    """Test the SQL Reporter Agent"""
    
    print("[TEST] Testing SQL Reporter Agent...")
    
    # Mock results from other agents
    mock_results = {
        "object_info": {
            "object_name": "usp_ProcessOrder",
            "object_type": "Stored Procedure"
        },
        "optimization": {
            "performance_issues": [
                {"issue": "SELECT * usage", "severity": "Medium", "description": "Inefficient column selection"}
            ],
            "optimization_suggestions": [
                {"suggestion": "Use specific columns", "priority": "Medium", "implementation": "Replace SELECT * with column list"}
            ],
            "estimated_improvement": {"performance_gain": "20-30%"}
        },
        "security": {
            "vulnerabilities": [
                {"vulnerability": "SQL Injection", "severity": "Critical", "cwe": "CWE-89", "description": "Dynamic SQL without parameterization"}
            ],
            "risk_assessment": {"overall_risk": "Critical", "security_score": 40}
        },
        "dependency": {
            "missing_objects": ["usp_LogActivity", "usp_SendEmail"],
            "impact_analysis": {"impact_level": "High", "change_risk": "High", "deployment_complexity": "High"}
        }
    }
    
    try:
        reporter = SQLReporterAgent()
        result = reporter.generate_reports(
            parsed_results=mock_results.get("parsed"),
            optimization_results=mock_results.get("optimization"),
            security_results=mock_results.get("security"),
            dependency_results=mock_results.get("dependency"),
            object_info=mock_results.get("object_info")
        )
        
        print("[OK] SQL Reporter Agent Results:")
        print(f"   Executive Summary: {len(result.executive_summary)} characters")
        print(f"   Technical Report: {len(result.technical_report)} characters")
        print(f"   Recommendations: {len(result.recommendations_report)} characters")
        print(f"   Deployment Guide: {len(result.deployment_guide)} characters")
        print(f"   Risk Assessment: {len(result.risk_assessment_report)} characters")
        print(f"   Artifacts Generated: {len(result.artifacts)} files")
        print(f"   Confidence: {result.confidence_score:.2f}")
        
        # Show a sample of the executive summary
        print(f"\n[REPORT] Executive Summary Preview:")
        print(result.executive_summary[:300] + "...")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_reporter_agent()
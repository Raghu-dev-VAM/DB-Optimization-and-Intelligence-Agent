"""
SQL Orchestrator Agent
Coordinates all SQL analysis agents and manages the multi-agent workflow
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from agent_config import sql_agent_system
from sql_parser_agent import SQLParserAgent
from sql_optimizer_agent import SQLOptimizerAgent
from sql_security_agent import SQLSecurityAgent
from sql_dependency_agent import SQLDependencyAgent
from sql_reporter_agent import SQLReporterAgent

@dataclass
class OrchestrationResult:
    """Complete multi-agent analysis results"""
    analysis_id: str
    orchestration_strategy: str
    agents_used: List[str]
    execution_sequence: List[str]
    parsed_results: Dict[str, Any]
    optimization_results: Dict[str, Any]
    security_results: Dict[str, Any]
    dependency_results: Dict[str, Any]
    report_results: Dict[str, Any]
    overall_confidence: float
    total_processing_time: float
    recommendations: List[Dict[str, Any]]
    ai_insights: Dict[str, Any]

class SQLOrchestratorAgent:
    """SQL Orchestrator Agent - coordinates all other agents"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("orchestrator")
        
        # Initialize all agents
        self.parser_agent = SQLParserAgent()
        self.optimizer_agent = SQLOptimizerAgent()
        self.security_agent = SQLSecurityAgent()
        self.dependency_agent = SQLDependencyAgent()
        self.reporter_agent = SQLReporterAgent()
        
        # Agent execution history
        self.execution_history = []
    
    def orchestrate_analysis(self, 
                           sql: str, 
                           analysis_type: str = "full_analysis",
                           db_type: str = "SQL Server",
                           known_objects: Dict[str, Any] = None,
                           user_preferences: Dict[str, Any] = None) -> OrchestrationResult:
        """Orchestrate multi-agent SQL analysis"""
        
        start_time = datetime.now()
        analysis_id = f"ORCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"[ORCHESTRATOR] Starting orchestrated analysis: {analysis_id}")
        print(f"[ANALYSIS] Analysis type: {analysis_type}")
        
        # Determine orchestration strategy
        strategy = self._determine_strategy(sql, analysis_type, user_preferences or {})
        agents_to_use = self._select_agents(strategy, sql)
        execution_sequence = self._plan_execution_sequence(agents_to_use, sql)
        
        print(f"[AGENTS] Agents selected: {agents_to_use}")
        print(f"[SEQUENCE] Execution sequence: {execution_sequence}")
        
        # Execute agents in sequence
        results = {}
        
        try:
            # Step 1: Always start with Parser Agent
            if "parser" in agents_to_use:
                print("[PARSER] Executing Parser Agent...")
                parsed_result = self.parser_agent.parse_sql(sql, known_objects or {})
                results["parsed"] = {
                    "object_name": parsed_result.object_name,
                    "object_type": parsed_result.object_type,
                    "tables": parsed_result.tables,
                    "joins": parsed_result.joins,
                    "filters": parsed_result.filters,
                    "references": parsed_result.references,
                    "missing_references": parsed_result.missing_references,
                    "ai_insights": parsed_result.ai_insights,
                    "confidence_score": parsed_result.confidence_score
                }
                print(f"   [OK] Parser completed (confidence: {parsed_result.confidence_score:.2f})")
            
            # Step 2: Security Agent (high priority)
            if "security" in agents_to_use:
                print("[SECURITY] Executing Security Agent...")
                security_result = self.security_agent.analyze_security(sql, results.get("parsed", {}), db_type)
                results["security"] = {
                    "vulnerabilities": security_result.vulnerabilities,
                    "security_recommendations": security_result.security_recommendations,
                    "risk_assessment": security_result.risk_assessment,
                    "compliance_issues": security_result.compliance_issues,
                    "remediation_steps": security_result.remediation_steps,
                    "ai_insights": security_result.ai_insights,
                    "confidence_score": security_result.confidence_score
                }
                print(f"   [OK] Security completed (confidence: {security_result.confidence_score:.2f})")
                
                # Check for critical security issues
                critical_security = any(v.get("severity") == "Critical" for v in security_result.vulnerabilities)
                if critical_security:
                    print("   [WARNING] CRITICAL security issues found - prioritizing remediation")
            
            # Step 3: Dependency Agent
            if "dependency" in agents_to_use:
                print("[DEPENDENCY] Executing Dependency Agent...")
                object_name = results.get("parsed", {}).get("object_name", "Unknown")
                dependency_result = self.dependency_agent.analyze_dependencies(
                    sql, object_name, results.get("parsed", {}), known_objects or {}
                )
                results["dependency"] = {
                    "dependencies": dependency_result.dependencies,
                    "reverse_dependencies": dependency_result.reverse_dependencies,
                    "dependency_graph": dependency_result.dependency_graph,
                    "impact_analysis": dependency_result.impact_analysis,
                    "circular_dependencies": dependency_result.circular_dependencies,
                    "missing_objects": dependency_result.missing_objects,
                    "deployment_order": dependency_result.deployment_order,
                    "ai_insights": dependency_result.ai_insights,
                    "confidence_score": dependency_result.confidence_score
                }
                print(f"   [OK] Dependency completed (confidence: {dependency_result.confidence_score:.2f})")
            
            # Step 4: Optimizer Agent
            if "optimizer" in agents_to_use:
                print("[OPTIMIZER] Executing Optimizer Agent...")
                optimization_result = self.optimizer_agent.optimize_sql(sql, results.get("parsed", {}), db_type)
                results["optimization"] = {
                    "performance_issues": optimization_result.performance_issues,
                    "optimization_suggestions": optimization_result.optimization_suggestions,
                    "index_recommendations": optimization_result.index_recommendations,
                    "query_rewrite_suggestions": optimization_result.query_rewrite_suggestions,
                    "estimated_improvement": optimization_result.estimated_improvement,
                    "ai_insights": optimization_result.ai_insights,
                    "confidence_score": optimization_result.confidence_score
                }
                print(f"   [OK] Optimizer completed (confidence: {optimization_result.confidence_score:.2f})")
            
            # Step 5: Reporter Agent (always last)
            if "reporter" in agents_to_use:
                print("[REPORTER] Executing Reporter Agent...")
                report_result = self.reporter_agent.generate_reports(
                    parsed_results=results.get("parsed"),
                    optimization_results=results.get("optimization"),
                    security_results=results.get("security"),
                    dependency_results=results.get("dependency"),
                    object_info=results.get("parsed", {})
                )
                results["reports"] = {
                    "executive_summary": report_result.executive_summary,
                    "technical_report": report_result.technical_report,
                    "recommendations_report": report_result.recommendations_report,
                    "deployment_guide": report_result.deployment_guide,
                    "risk_assessment_report": report_result.risk_assessment_report,
                    "artifacts": report_result.artifacts,
                    "ai_insights": report_result.ai_insights,
                    "confidence_score": report_result.confidence_score
                }
                print(f"   [OK] Reporter completed (confidence: {report_result.confidence_score:.2f})")
            
            # Calculate overall metrics
            total_time = (datetime.now() - start_time).total_seconds()
            overall_confidence = self._calculate_overall_confidence(results)
            recommendations = self._compile_recommendations(results)
            
            # Create orchestration result
            orchestration_result = OrchestrationResult(
                analysis_id=analysis_id,
                orchestration_strategy=strategy,
                agents_used=agents_to_use,
                execution_sequence=execution_sequence,
                parsed_results=results.get("parsed", {}),
                optimization_results=results.get("optimization", {}),
                security_results=results.get("security", {}),
                dependency_results=results.get("dependency", {}),
                report_results=results.get("reports", {}),
                overall_confidence=overall_confidence,
                total_processing_time=total_time,
                recommendations=recommendations,
                ai_insights=self._compile_ai_insights(results)
            )
            
            # Store execution history
            self.execution_history.append({
                "analysis_id": analysis_id,
                "timestamp": start_time.isoformat(),
                "strategy": strategy,
                "agents_used": agents_to_use,
                "success": True,
                "processing_time": total_time
            })
            
            print(f"[SUCCESS] Orchestration completed successfully!")
            print(f"[TIME] Total processing time: {total_time:.2f}s")
            print(f"[CONFIDENCE] Overall confidence: {overall_confidence:.2f}")
            
            return orchestration_result
            
        except Exception as e:
            print(f"[ERROR] Orchestration failed: {str(e)}")
            
            # Store failed execution
            self.execution_history.append({
                "analysis_id": analysis_id,
                "timestamp": start_time.isoformat(),
                "strategy": strategy,
                "agents_used": agents_to_use,
                "success": False,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            })
            
            raise Exception(f"Orchestration failed: {str(e)}")
    
    def _determine_strategy(self, sql: str, analysis_type: str, user_preferences: Dict[str, Any]) -> str:
        """Determine orchestration strategy based on SQL and requirements"""
        
        sql_lower = sql.lower()
        
        # Strategy based on analysis type
        if analysis_type == "security_only":
            return "security_focused"
        elif analysis_type == "performance_only":
            return "performance_focused"
        elif analysis_type == "dependency_only":
            return "dependency_focused"
        
        # Strategy based on SQL characteristics
        if "create procedure" in sql_lower or "create function" in sql_lower:
            return "comprehensive_procedure_analysis"
        elif "select" in sql_lower and ("join" in sql_lower or "where" in sql_lower):
            return "query_optimization_focused"
        elif any(risky in sql_lower for risky in ["exec(", "execute(", "sp_executesql"]):
            return "security_priority_analysis"
        elif "create table" in sql_lower or "alter table" in sql_lower:
            return "schema_analysis"
        else:
            return "balanced_analysis"
    
    def _select_agents(self, strategy: str, sql: str) -> List[str]:
        """Select which agents to use based on strategy"""
        
        agent_selection = {
            "comprehensive_procedure_analysis": ["parser", "security", "dependency", "optimizer", "reporter"],
            "query_optimization_focused": ["parser", "optimizer", "security", "reporter"],
            "security_priority_analysis": ["parser", "security", "dependency", "reporter"],
            "security_focused": ["parser", "security", "reporter"],
            "performance_focused": ["parser", "optimizer", "reporter"],
            "dependency_focused": ["parser", "dependency", "reporter"],
            "schema_analysis": ["parser", "dependency", "reporter"],
            "balanced_analysis": ["parser", "optimizer", "security", "dependency", "reporter"]
        }
        
        return agent_selection.get(strategy, ["parser", "optimizer", "security", "dependency", "reporter"])
    
    def _plan_execution_sequence(self, agents: List[str], sql: str) -> List[str]:
        """Plan optimal execution sequence for selected agents"""
        
        # Base sequence (parser always first, reporter always last)
        sequence = []
        
        if "parser" in agents:
            sequence.append("parser")
        
        # Security has high priority for risky SQL
        if "security" in agents and any(risky in sql.lower() for risky in ["exec(", "execute(", "+"]):
            sequence.append("security")
        
        # Dependency analysis before optimization
        if "dependency" in agents:
            sequence.append("dependency")
        
        # Security (if not already added)
        if "security" in agents and "security" not in sequence:
            sequence.append("security")
        
        # Optimization
        if "optimizer" in agents:
            sequence.append("optimizer")
        
        # Reporter always last
        if "reporter" in agents:
            sequence.append("reporter")
        
        return sequence
    
    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score from all agents"""
        
        confidences = []
        
        for agent_result in results.values():
            if isinstance(agent_result, dict) and "confidence_score" in agent_result:
                confidences.append(agent_result["confidence_score"])
        
        if not confidences:
            return 0.5
        
        # Weighted average (give more weight to security and parser)
        weights = {
            "parsed": 1.2,
            "security": 1.5,
            "optimization": 1.0,
            "dependency": 1.0,
            "reports": 0.8
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for i, (agent_name, agent_result) in enumerate(results.items()):
            if isinstance(agent_result, dict) and "confidence_score" in agent_result:
                weight = weights.get(agent_name, 1.0)
                weighted_sum += agent_result["confidence_score"] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else sum(confidences) / len(confidences)
    
    def _compile_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compile prioritized recommendations from all agents"""
        
        recommendations = []
        
        # Security recommendations (highest priority)
        security_results = results.get("security", {})
        for rec in security_results.get("security_recommendations", []):
            recommendations.append({
                "source": "Security Agent",
                "priority": 1 if rec.get("priority") == "Critical" else 2,
                "category": "Security",
                "recommendation": rec.get("recommendation", ""),
                "implementation": rec.get("implementation", "")
            })
        
        # Performance recommendations
        optimization_results = results.get("optimization", {})
        for rec in optimization_results.get("optimization_suggestions", []):
            priority = 2 if rec.get("priority") == "High" else 3
            recommendations.append({
                "source": "Optimizer Agent",
                "priority": priority,
                "category": "Performance",
                "recommendation": rec.get("suggestion", ""),
                "implementation": rec.get("implementation", "")
            })
        
        # Dependency recommendations
        dependency_results = results.get("dependency", {})
        missing_objects = dependency_results.get("missing_objects", [])
        if missing_objects:
            recommendations.append({
                "source": "Dependency Agent",
                "priority": 2,
                "category": "Dependencies",
                "recommendation": f"Resolve {len(missing_objects)} missing dependencies",
                "implementation": f"Add definitions for: {', '.join(missing_objects[:3])}"
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"])
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _compile_ai_insights(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile AI insights from all agents"""
        
        insights = {
            "orchestration_summary": f"Multi-agent analysis completed with {len(results)} agents",
            "agent_insights": {},
            "cross_agent_correlations": [],
            "overall_assessment": ""
        }
        
        # Collect insights from each agent
        for agent_name, agent_result in results.items():
            if isinstance(agent_result, dict) and "ai_insights" in agent_result:
                insights["agent_insights"][agent_name] = agent_result["ai_insights"]
        
        # Identify cross-agent correlations
        security_critical = any(v.get("severity") == "Critical" 
                              for v in results.get("security", {}).get("vulnerabilities", []))
        high_perf_issues = any(i.get("severity") == "High" 
                             for i in results.get("optimization", {}).get("performance_issues", []))
        missing_deps = len(results.get("dependency", {}).get("missing_objects", []))
        
        if security_critical and missing_deps > 0:
            insights["cross_agent_correlations"].append(
                "Critical security issues combined with missing dependencies create high deployment risk"
            )
        
        if high_perf_issues and security_critical:
            insights["cross_agent_correlations"].append(
                "Performance and security issues both present - prioritize security fixes first"
            )
        
        # Overall assessment
        if security_critical:
            insights["overall_assessment"] = "CRITICAL: Security vulnerabilities require immediate attention"
        elif high_perf_issues or missing_deps > 2:
            insights["overall_assessment"] = "REVIEW REQUIRED: Significant issues found across multiple areas"
        else:
            insights["overall_assessment"] = "ACCEPTABLE: Minor issues identified with clear remediation path"
        
        return insights

def test_sql_orchestrator_agent():
    """Test the SQL Orchestrator Agent"""
    
    print("[ORCHESTRATOR] Testing SQL Orchestrator Agent...")
    
    # Test SQL with multiple types of issues
    test_sql = """
    CREATE PROCEDURE usp_GetUserOrders
        @UserId NVARCHAR(50),
        @StartDate DATETIME = NULL
    AS
    BEGIN
        DECLARE @SQL NVARCHAR(MAX)
        SET @SQL = 'SELECT * FROM Orders o 
                    JOIN Customers c ON o.CustomerId = c.CustomerId 
                    WHERE c.UserId = "' + @UserId + '"'
        
        IF @StartDate IS NOT NULL
            SET @SQL = @SQL + ' AND o.OrderDate >= "' + CAST(@StartDate AS NVARCHAR) + '"'
        
        EXEC(@SQL)
        
        -- Update user activity
        EXEC usp_UpdateUserActivity @UserId
        
        -- Log access
        EXEC usp_LogAccess @UserId, 'ORDER_VIEW'
    END
    """
    
    # Known objects for dependency analysis
    known_objects = {
        "Orders": {"object_type": "Table"},
        "Customers": {"object_type": "Table"},
        "usp_UpdateUserActivity": {"object_type": "Stored Procedure", "references": [], "tables": ["UserActivity"]}
    }
    
    try:
        orchestrator = SQLOrchestratorAgent()
        
        # Test comprehensive analysis
        result = orchestrator.orchestrate_analysis(
            sql=test_sql,
            analysis_type="full_analysis",
            db_type="SQL Server",
            known_objects=known_objects
        )
        
        print("[OK] SQL Orchestrator Agent Results:")
        print(f"   Analysis ID: {result.analysis_id}")
        print(f"   Strategy: {result.orchestration_strategy}")
        print(f"   Agents Used: {len(result.agents_used)} ({', '.join(result.agents_used)})")
        print(f"   Execution Sequence: {' -> '.join(result.execution_sequence)}")
        print(f"   Overall Confidence: {result.overall_confidence:.2f}")
        print(f"   Total Processing Time: {result.total_processing_time:.2f}s")
        print(f"   Recommendations Generated: {len(result.recommendations)}")
        
        # Show top recommendations
        print(f"\n[RECOMMENDATIONS] Top Recommendations:")
        for i, rec in enumerate(result.recommendations[:3], 1):
            print(f"   {i}. [{rec['category']}] {rec['recommendation']}")
        
        # Show overall assessment
        print(f"\n[ASSESSMENT] Overall Assessment:")
        print(f"   {result.ai_insights.get('overall_assessment', 'Analysis completed')}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_orchestrator_agent()
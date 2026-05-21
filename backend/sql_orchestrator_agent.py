"""
SQL Orchestrator Agent — AutoGen-powered multi-agent coordination
Each specialist agent runs as an AutoGen AssistantAgent.
The orchestrator drives the sequence and collects results.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agent_config import sql_agent_system
from sql_parser_agent import SQLParserAgent
from sql_security_agent import SQLSecurityAgent
from sql_dependency_agent import SQLDependencyAgent
from sql_optimizer_agent import SQLOptimizerAgent
from sql_reporter_agent import SQLReporterAgent


@dataclass
class OrchestrationResult:
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


# ── AutoGen model client (Groq via OpenAI-compatible endpoint) ───────────────
def _make_model_client():
    import os
    return OpenAIChatCompletionClient(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY", ""),
        base_url="https://api.groq.com/openai/v1",
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
        },
    )


class SQLOrchestratorAgent:
    """AutoGen-powered orchestrator — drives specialist agents in sequence."""

    def __init__(self):
        self.config = sql_agent_system.get_agent_config("orchestrator")
        self.parser_agent = SQLParserAgent()
        self.security_agent = SQLSecurityAgent()
        self.dependency_agent = SQLDependencyAgent()
        self.optimizer_agent = SQLOptimizerAgent()
        self.reporter_agent = SQLReporterAgent()
        self.execution_history: List[Dict[str, Any]] = []

        self._model_client = _make_model_client()

        # ── AutoGen synthesis agent ───────────────────────────────────────────
        self.orchestrator_ag = AssistantAgent(
            name="Orchestrator",
            system_message=(
                "You coordinate SQL analysis. Given a task summary from each specialist, "
                "synthesize a final overall_assessment and list cross_agent_correlations. "
                "Reply with valid JSON only: "
                "{\"overall_assessment\": \"...\", \"cross_agent_correlations\": [\"...\"]}"
            ),
            model_client=self._model_client,
        )

    # ── public entry point ────────────────────────────────────────────────────
    def orchestrate_analysis(
        self,
        sql: str,
        analysis_type: str = "full_analysis",
        db_type: str = "SQL Server",
        known_objects: Dict[str, Any] = None,
        user_preferences: Dict[str, Any] = None,
    ) -> OrchestrationResult:

        start_time = datetime.now()
        analysis_id = f"ORCH-{start_time.strftime('%Y%m%d-%H%M%S')}"
        known_objects = known_objects or {}

        strategy = self._determine_strategy(sql, analysis_type)
        agents_to_use = self._select_agents(strategy)
        execution_sequence = self._plan_execution_sequence(agents_to_use, sql)

        print(f"[ORCHESTRATOR] {analysis_id} | strategy={strategy}")
        print(f"[SEQUENCE] {' -> '.join(execution_sequence)}")

        results: Dict[str, Any] = {}

        # ── Step 1: Parser ────────────────────────────────────────────────────
        if "parser" in agents_to_use:
            print("[PARSER] Running...")
            r = self.parser_agent.parse_sql(sql, known_objects)
            results["parsed"] = {
                "object_name": r.object_name,
                "object_type": r.object_type,
                "tables": r.tables,
                "joins": r.joins,
                "filters": r.filters,
                "references": r.references,
                "missing_references": r.missing_references,
                "ai_insights": r.ai_insights,
                "confidence_score": r.confidence_score,
            }
            print(f"   [OK] confidence={r.confidence_score:.2f}")

        # ── Step 2: Security ──────────────────────────────────────────────────
        if "security" in agents_to_use:
            print("[SECURITY] Running...")
            r = self.security_agent.analyze_security(sql, results.get("parsed", {}), db_type)
            results["security"] = {
                "vulnerabilities": r.vulnerabilities,
                "security_recommendations": r.security_recommendations,
                "risk_assessment": r.risk_assessment,
                "compliance_issues": r.compliance_issues,
                "remediation_steps": r.remediation_steps,
                "ai_insights": r.ai_insights,
                "confidence_score": r.confidence_score,
            }
            print(f"   [OK] confidence={r.confidence_score:.2f}")

        # ── Step 3: Dependency ────────────────────────────────────────────────
        if "dependency" in agents_to_use:
            print("[DEPENDENCY] Running...")
            obj_name = results.get("parsed", {}).get("object_name", "Unknown")
            r = self.dependency_agent.analyze_dependencies(sql, obj_name, results.get("parsed", {}), known_objects)
            results["dependency"] = {
                "dependencies": r.dependencies,
                "reverse_dependencies": r.reverse_dependencies,
                "dependency_graph": r.dependency_graph,
                "impact_analysis": r.impact_analysis,
                "circular_dependencies": r.circular_dependencies,
                "missing_objects": r.missing_objects,
                "deployment_order": r.deployment_order,
                "ai_insights": r.ai_insights,
                "confidence_score": r.confidence_score,
            }
            print(f"   [OK] confidence={r.confidence_score:.2f}")

        # ── Step 4: Optimizer ─────────────────────────────────────────────────
        if "optimizer" in agents_to_use:
            print("[OPTIMIZER] Running...")
            r = self.optimizer_agent.optimize_sql(sql, results.get("parsed", {}), db_type)
            results["optimization"] = {
                "performance_issues": r.performance_issues,
                "optimization_suggestions": r.optimization_suggestions,
                "index_recommendations": r.index_recommendations,
                "query_rewrite_suggestions": r.query_rewrite_suggestions,
                "estimated_improvement": r.estimated_improvement,
                "ai_insights": r.ai_insights,
                "confidence_score": r.confidence_score,
            }
            print(f"   [OK] confidence={r.confidence_score:.2f}")

        # ── Step 5: Reporter ──────────────────────────────────────────────────
        if "reporter" in agents_to_use:
            print("[REPORTER] Running...")
            r = self.reporter_agent.generate_reports(
                parsed_results=results.get("parsed"),
                optimization_results=results.get("optimization"),
                security_results=results.get("security"),
                dependency_results=results.get("dependency"),
                object_info=results.get("parsed", {}),
            )
            results["reports"] = {
                "executive_summary": r.executive_summary,
                "technical_report": r.technical_report,
                "recommendations_report": r.recommendations_report,
                "deployment_guide": r.deployment_guide,
                "risk_assessment_report": r.risk_assessment_report,
                "artifacts": r.artifacts,
                "ai_insights": r.ai_insights,
                "confidence_score": r.confidence_score,
            }
            print(f"   [OK] confidence={r.confidence_score:.2f}")

        # ── AutoGen synthesis step ────────────────────────────────────────────
        ai_insights = self._autogen_synthesize(results)

        total_time = (datetime.now() - start_time).total_seconds()
        overall_confidence = self._calculate_overall_confidence(results)
        recommendations = self._compile_recommendations(results)

        self.execution_history.append({
            "analysis_id": analysis_id,
            "timestamp": start_time.isoformat(),
            "strategy": strategy,
            "agents_used": agents_to_use,
            "success": True,
            "processing_time": total_time,
        })

        print(f"[DONE] {total_time:.2f}s | confidence={overall_confidence:.2f}")

        return OrchestrationResult(
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
            ai_insights=ai_insights,
        )

    # ── AutoGen synthesis ─────────────────────────────────────────────────────
    def _autogen_synthesize(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Ask AutoGen orchestrator agent to synthesize cross-agent insights."""
        import asyncio

        summary_lines = []
        if "security" in results:
            vulns = results["security"].get("vulnerabilities", [])
            critical = sum(1 for v in vulns if v.get("severity") == "Critical")
            summary_lines.append(f"Security: {len(vulns)} vulnerabilities, {critical} critical.")
        if "optimization" in results:
            issues = results["optimization"].get("performance_issues", [])
            summary_lines.append(f"Performance: {len(issues)} issues.")
        if "dependency" in results:
            missing = results["dependency"].get("missing_objects", [])
            summary_lines.append(f"Dependencies: {len(missing)} missing objects.")
        if "parsed" in results:
            summary_lines.append(f"Complexity score: {results['parsed'].get('ai_insights', {}).get('complexity_score', 'N/A')}/10.")

        task = "Agent findings:\n" + "\n".join(summary_lines) + "\nProvide your JSON synthesis."

        insights = {
            "orchestration_summary": f"AutoGen multi-agent analysis with {len(results)} agents",
            "agent_insights": {k: v.get("ai_insights", {}) for k, v in results.items()},
            "cross_agent_correlations": [],
            "overall_assessment": "",
        }

        try:
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken

            async def _run():
                response = await self.orchestrator_ag.on_messages(
                    [TextMessage(content=task, source="user")],
                    cancellation_token=CancellationToken(),
                )
                return response.chat_message.content if response.chat_message else ""

            content = asyncio.run(_run())
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(content[start:end])
                insights["overall_assessment"] = parsed.get("overall_assessment", "")
                insights["cross_agent_correlations"] = parsed.get("cross_agent_correlations", [])
        except Exception as e:
            print(f"[AUTOGEN SYNTHESIS] Fallback to static: {e}")
            insights["overall_assessment"] = self._static_assessment(results)
            insights["cross_agent_correlations"] = self._static_correlations(results)

        return insights

    # ── static fallbacks ──────────────────────────────────────────────────────
    def _static_assessment(self, results: Dict[str, Any]) -> str:
        security_critical = any(
            v.get("severity") == "Critical"
            for v in results.get("security", {}).get("vulnerabilities", [])
        )
        high_perf = any(
            i.get("severity") == "High"
            for i in results.get("optimization", {}).get("performance_issues", [])
        )
        missing = len(results.get("dependency", {}).get("missing_objects", []))
        if security_critical:
            return "CRITICAL: Security vulnerabilities require immediate attention"
        if high_perf or missing > 2:
            return "REVIEW REQUIRED: Significant issues found across multiple areas"
        return "ACCEPTABLE: Minor issues identified with clear remediation path"

    def _static_correlations(self, results: Dict[str, Any]) -> List[str]:
        correlations = []
        security_critical = any(
            v.get("severity") == "Critical"
            for v in results.get("security", {}).get("vulnerabilities", [])
        )
        missing = len(results.get("dependency", {}).get("missing_objects", []))
        high_perf = any(
            i.get("severity") == "High"
            for i in results.get("optimization", {}).get("performance_issues", [])
        )
        if security_critical and missing > 0:
            correlations.append("Critical security issues combined with missing dependencies create high deployment risk")
        if high_perf and security_critical:
            correlations.append("Performance and security issues both present - prioritize security fixes first")
        return correlations

    # ── strategy helpers ──────────────────────────────────────────────────────
    def _determine_strategy(self, sql: str, analysis_type: str) -> str:
        lower = sql.lower()
        if analysis_type == "security_only":
            return "security_focused"
        if analysis_type == "performance_only":
            return "performance_focused"
        if analysis_type == "dependency_only":
            return "dependency_focused"
        if "create procedure" in lower or "create function" in lower:
            return "comprehensive_procedure_analysis"
        if "select" in lower and ("join" in lower or "where" in lower):
            return "query_optimization_focused"
        if any(r in lower for r in ["exec(", "execute(", "sp_executesql"]):
            return "security_priority_analysis"
        if "create table" in lower or "alter table" in lower:
            return "schema_analysis"
        return "balanced_analysis"

    def _select_agents(self, strategy: str) -> List[str]:
        mapping = {
            "comprehensive_procedure_analysis": ["parser", "security", "dependency", "optimizer", "reporter"],
            "query_optimization_focused": ["parser", "optimizer", "security", "reporter"],
            "security_priority_analysis": ["parser", "security", "dependency", "reporter"],
            "security_focused": ["parser", "security", "reporter"],
            "performance_focused": ["parser", "optimizer", "reporter"],
            "dependency_focused": ["parser", "dependency", "reporter"],
            "schema_analysis": ["parser", "dependency", "reporter"],
            "balanced_analysis": ["parser", "optimizer", "security", "dependency", "reporter"],
        }
        return mapping.get(strategy, ["parser", "optimizer", "security", "dependency", "reporter"])

    def _plan_execution_sequence(self, agents: List[str], sql: str) -> List[str]:
        seq = []
        order = ["parser", "security", "dependency", "optimizer", "reporter"]
        risky = any(r in sql.lower() for r in ["exec(", "execute(", "+"])
        if risky and "security" in agents:
            order = ["parser", "security", "dependency", "optimizer", "reporter"]
        for a in order:
            if a in agents:
                seq.append(a)
        return seq

    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        weights = {"parsed": 1.2, "security": 1.5, "optimization": 1.0, "dependency": 1.0, "reports": 0.8}
        weighted_sum = total_weight = 0.0
        for key, val in results.items():
            if isinstance(val, dict) and "confidence_score" in val:
                w = weights.get(key, 1.0)
                weighted_sum += val["confidence_score"] * w
                total_weight += w
        return weighted_sum / total_weight if total_weight else 0.5

    def _compile_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs = []
        for r in results.get("security", {}).get("security_recommendations", []):
            recs.append({
                "source": "Security Agent",
                "priority": 1 if r.get("priority") == "Critical" else 2,
                "category": "Security",
                "recommendation": r.get("recommendation", ""),
                "implementation": r.get("implementation", ""),
            })
        for r in results.get("optimization", {}).get("optimization_suggestions", []):
            recs.append({
                "source": "Optimizer Agent",
                "priority": 2 if r.get("priority") == "High" else 3,
                "category": "Performance",
                "recommendation": r.get("suggestion", ""),
                "implementation": r.get("implementation", ""),
            })
        missing = results.get("dependency", {}).get("missing_objects", [])
        if missing:
            recs.append({
                "source": "Dependency Agent",
                "priority": 2,
                "category": "Dependencies",
                "recommendation": f"Resolve {len(missing)} missing dependencies",
                "implementation": f"Add definitions for: {', '.join(missing[:3])}",
            })
        recs.sort(key=lambda x: x["priority"])
        return recs[:10]

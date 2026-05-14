"""
AI-Powered SQL Dependency Agent
Maps dependencies, relationships, and provides impact analysis using Groq AI
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
import requests
from datetime import datetime

from agent_config import sql_agent_system
from groq_client import groq_client

@dataclass
class DependencyAnalysisResult:
    """SQL dependency analysis results"""
    dependencies: Dict[str, List[str]]
    reverse_dependencies: Dict[str, List[str]]
    dependency_graph: Dict[str, Any]
    impact_analysis: Dict[str, Any]
    circular_dependencies: List[List[str]]
    missing_objects: List[str]
    deployment_order: List[str]
    ai_insights: Dict[str, Any]
    confidence_score: float

class SQLDependencyAgent:
    """AI-powered SQL Dependency Agent using Groq"""
    
    def __init__(self):
        self.config = sql_agent_system.get_agent_config("dependency")
        
    def analyze_dependencies(self, sql: str, object_name: str, parsed_data: Dict[str, Any] = None, 
                           known_objects: Dict[str, Any] = None) -> DependencyAnalysisResult:
        """Analyze SQL dependencies and relationships"""
        
        # Get basic static dependency analysis first
        static_results = self._static_dependency_analysis(sql, object_name, parsed_data or {}, known_objects or {})
        
        # Enhance with AI analysis
        ai_insights = self._ai_dependency_analyze(sql, object_name, static_results, parsed_data or {}, known_objects or {})
        
        # Combine results
        return DependencyAnalysisResult(
            dependencies=ai_insights.get("enhanced_dependencies", static_results["dependencies"]),
            reverse_dependencies=ai_insights.get("reverse_dependencies", static_results["reverse_dependencies"]),
            dependency_graph=ai_insights.get("enhanced_graph", static_results["dependency_graph"]),
            impact_analysis=ai_insights.get("enhanced_impact", static_results["impact_analysis"]),
            circular_dependencies=ai_insights.get("circular_dependencies", static_results["circular_dependencies"]),
            missing_objects=ai_insights.get("enhanced_missing", static_results["missing_objects"]),
            deployment_order=ai_insights.get("deployment_order", static_results["deployment_order"]),
            ai_insights=ai_insights,
            confidence_score=ai_insights.get("confidence", 0.8)
        )
    
    def _static_dependency_analysis(self, sql: str, object_name: str, parsed_data: Dict[str, Any], 
                                  known_objects: Dict[str, Any]) -> Dict[str, Any]:
        """Basic static dependency analysis"""
        
        # Extract dependencies from parsed data
        tables = parsed_data.get("tables", [])
        references = parsed_data.get("references", [])
        
        # Build dependency mapping
        dependencies = {object_name: tables + references}
        
        # Find reverse dependencies (what depends on this object)
        reverse_dependencies = self._find_reverse_dependencies(object_name, known_objects)
        
        # Identify missing objects
        missing_objects = []
        for ref in references:
            if ref.lower() not in {obj.lower() for obj in known_objects.keys()}:
                missing_objects.append(ref)
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(dependencies, reverse_dependencies, known_objects)
        
        # Detect circular dependencies
        circular_dependencies = self._detect_circular_dependencies(dependency_graph)
        
        # Calculate impact analysis
        impact_analysis = self._calculate_impact_analysis(object_name, dependencies, reverse_dependencies, missing_objects)
        
        # Determine deployment order
        deployment_order = self._calculate_deployment_order(dependency_graph, circular_dependencies)
        
        return {
            "dependencies": dependencies,
            "reverse_dependencies": reverse_dependencies,
            "dependency_graph": dependency_graph,
            "impact_analysis": impact_analysis,
            "circular_dependencies": circular_dependencies,
            "missing_objects": missing_objects,
            "deployment_order": deployment_order
        }
    
    def _find_reverse_dependencies(self, object_name: str, known_objects: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find objects that depend on the given object"""
        reverse_deps = {object_name: []}
        
        for obj_name, obj_data in known_objects.items():
            if isinstance(obj_data, dict):
                obj_references = obj_data.get("references", [])
                obj_tables = obj_data.get("tables", [])
                
                # Check if this object references our target object
                if (object_name.lower() in {ref.lower() for ref in obj_references} or
                    object_name.lower() in {table.lower() for table in obj_tables}):
                    reverse_deps[object_name].append(obj_name)
        
        return reverse_deps
    
    def _build_dependency_graph(self, dependencies: Dict[str, List[str]], 
                              reverse_dependencies: Dict[str, List[str]], 
                              known_objects: Dict[str, Any]) -> Dict[str, Any]:
        """Build a comprehensive dependency graph"""
        
        nodes = []
        edges = []
        
        # Add nodes for all objects
        all_objects = set()
        for obj, deps in dependencies.items():
            all_objects.add(obj)
            all_objects.update(deps)
        
        for obj in all_objects:
            node_type = "Unknown"
            status = "missing"
            
            if obj in known_objects:
                status = "known"
                obj_data = known_objects[obj]
                if isinstance(obj_data, dict):
                    node_type = obj_data.get("object_type", "Unknown")
            elif obj.lower().endswith(("table", "view")):
                node_type = "Table"
                status = "referenced"
            elif obj.lower().startswith(("usp_", "sp_")):
                node_type = "Stored Procedure"
            elif obj.lower().startswith(("fn_", "udf_")):
                node_type = "Function"
            
            nodes.append({
                "id": obj,
                "type": node_type,
                "status": status
            })
        
        # Add edges for dependencies
        for obj, deps in dependencies.items():
            for dep in deps:
                edges.append({
                    "from": obj,
                    "to": dep,
                    "type": "depends_on"
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, Any]) -> List[List[str]]:
        """Detect circular dependencies in the graph"""
        
        edges = dependency_graph.get("edges", [])
        
        # Build adjacency list
        graph = {}
        for edge in edges:
            from_node = edge["from"]
            to_node = edge["to"]
            
            if from_node not in graph:
                graph[from_node] = []
            graph[from_node].append(to_node)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _calculate_impact_analysis(self, object_name: str, dependencies: Dict[str, List[str]], 
                                 reverse_dependencies: Dict[str, List[str]], 
                                 missing_objects: List[str]) -> Dict[str, Any]:
        """Calculate impact analysis for the object"""
        
        direct_dependencies = len(dependencies.get(object_name, []))
        direct_dependents = len(reverse_dependencies.get(object_name, []))
        
        # Calculate impact score
        impact_score = (direct_dependencies * 2) + (direct_dependents * 3) + (len(missing_objects) * 5)
        
        if impact_score >= 20:
            impact_level = "High"
        elif impact_score >= 10:
            impact_level = "Medium"
        else:
            impact_level = "Low"
        
        return {
            "impact_level": impact_level,
            "impact_score": impact_score,
            "direct_dependencies": direct_dependencies,
            "direct_dependents": direct_dependents,
            "missing_dependencies": len(missing_objects),
            "change_risk": "High" if missing_objects else "Medium" if direct_dependents > 0 else "Low",
            "deployment_complexity": "High" if direct_dependencies > 3 else "Medium" if direct_dependencies > 0 else "Low"
        }
    
    def _calculate_deployment_order(self, dependency_graph: Dict[str, Any], 
                                  circular_dependencies: List[List[str]]) -> List[str]:
        """Calculate optimal deployment order"""
        
        edges = dependency_graph.get("edges", [])
        nodes = {node["id"] for node in dependency_graph.get("nodes", [])}
        
        # Build adjacency list (reverse for topological sort)
        graph = {node: [] for node in nodes}
        in_degree = {node: 0 for node in nodes}
        
        for edge in edges:
            from_node = edge["from"]
            to_node = edge["to"]
            
            # Reverse the edge for deployment order (dependencies first)
            graph[to_node].append(from_node)
            in_degree[from_node] += 1
        
        # Topological sort (Kahn's algorithm)
        queue = [node for node in nodes if in_degree[node] == 0]
        deployment_order = []
        
        while queue:
            node = queue.pop(0)
            deployment_order.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If there are circular dependencies, add remaining nodes
        remaining = nodes - set(deployment_order)
        deployment_order.extend(list(remaining))
        
        return deployment_order
    
    def _ai_dependency_analyze(self, sql: str, object_name: str, static_results: Dict[str, Any], 
                             parsed_data: Dict[str, Any], known_objects: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance dependency analysis with AI"""
        
        prompt = self._build_dependency_prompt(sql, object_name, static_results, parsed_data, known_objects)
        
        try:
            response = self._call_ai(prompt)
            ai_results = self._parse_ai_dependency_response(response)
            
            return {
                **ai_results,
                "ai_reasoning": response.get("reasoning", ""),
                "confidence": response.get("confidence", 0.8),
                "processing_time": response.get("processing_time", 0)
            }
            
        except Exception as e:
            print(f"AI dependency analysis failed, using static results: {e}")
            return {
                "enhanced_dependencies": static_results["dependencies"],
                "reverse_dependencies": static_results["reverse_dependencies"],
                "enhanced_graph": static_results["dependency_graph"],
                "enhanced_impact": static_results["impact_analysis"],
                "circular_dependencies": static_results["circular_dependencies"],
                "enhanced_missing": static_results["missing_objects"],
                "deployment_order": static_results["deployment_order"],
                "ai_reasoning": f"AI analysis unavailable: {str(e)}",
                "confidence": 0.6
            }
    
    def _build_dependency_prompt(self, sql: str, object_name: str, static_results: Dict[str, Any], 
                               parsed_data: Dict[str, Any], known_objects: Dict[str, Any]) -> str:
        """Build prompt for AI dependency analysis"""
        
        static_deps = static_results["dependencies"].get(object_name, [])
        missing_objects = static_results["missing_objects"]
        known_object_names = list(known_objects.keys())
        
        return f"""You are a SQL Dependency Agent. Analyze dependencies and relationships for this SQL object.

SQL CODE:
```sql
{sql}
```

OBJECT NAME: {object_name}
STATIC DEPENDENCIES FOUND: {static_deps}
MISSING OBJECTS: {missing_objects}
KNOWN OBJECTS IN SYSTEM: {known_object_names[:10]}  # First 10 for context

DEPENDENCY ANALYSIS TASKS:
1. Validate and enhance dependency detection
2. Identify hidden or implicit dependencies
3. Analyze cross-database dependencies
4. Detect dynamic dependencies (runtime-resolved)
5. Assess impact of changes to this object
6. Recommend deployment strategies
7. Identify potential breaking changes

Focus on:
- Stored procedures calling other procedures
- Views depending on tables/views
- Functions used in computed columns
- Triggers on tables
- Dynamic SQL dependencies
- Schema dependencies
- Permission dependencies

Respond in JSON format:
{{
    "enhanced_dependencies": {{
        "{object_name}": ["list_of_all_dependencies"]
    }},
    "enhanced_missing": ["objects_not_found_in_known_objects"],
    "enhanced_impact": {{
        "impact_level": "High|Medium|Low",
        "change_risk": "High|Medium|Low",
        "affected_systems": ["list_of_affected_systems"],
        "breaking_change_risk": "High|Medium|Low"
    }},
    "deployment_recommendations": [
        {{"step": 1, "action": "what_to_deploy_first", "reason": "why_this_order"}}
    ],
    "hidden_dependencies": [
        {{"type": "dependency_type", "object": "object_name", "reason": "why_dependency_exists"}}
    ],
    "reasoning": "detailed_dependency_analysis",
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
    
    def _parse_ai_dependency_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI dependency response"""
        
        return {
            "enhanced_dependencies": response.get("enhanced_dependencies", {}),
            "enhanced_missing": response.get("enhanced_missing", []),
            "enhanced_impact": response.get("enhanced_impact", {}),
            "deployment_recommendations": response.get("deployment_recommendations", []),
            "hidden_dependencies": response.get("hidden_dependencies", []),
            "ai_reasoning": response.get("reasoning", ""),
            "confidence": response.get("confidence", 0.8)
        }

def test_sql_dependency_agent():
    """Test the SQL Dependency Agent"""
    
    print("[TEST] Testing SQL Dependency Agent...")
    
    # Test SQL with dependencies
    test_sql = '''
    CREATE PROCEDURE usp_ProcessOrder
        @OrderId INT,
        @CustomerId INT
    AS
    BEGIN
        -- Insert order details
        INSERT INTO OrderHistory (OrderId, CustomerId, ProcessedDate)
        SELECT @OrderId, @CustomerId, GETDATE()
        
        -- Update customer stats
        EXEC usp_UpdateCustomerStats @CustomerId
        
        -- Log the activity
        EXEC usp_LogActivity 'ORDER_PROCESSED', @OrderId
        
        -- Send notification
        EXEC usp_SendNotification @CustomerId, 'Order processed successfully'
    END
    '''
    
    # Parsed data from Parser Agent
    parsed_data = {
        "tables": ["OrderHistory"],
        "joins": [],
        "filters": [],
        "references": ["usp_UpdateCustomerStats", "usp_LogActivity", "usp_SendNotification"]
    }
    
    # Known objects in the system
    known_objects = {
        "usp_UpdateCustomerStats": {"object_type": "Stored Procedure", "references": [], "tables": ["Customers"]},
        "OrderHistory": {"object_type": "Table"},
        "Customers": {"object_type": "Table"}
    }
    
    try:
        dependency_agent = SQLDependencyAgent()
        result = dependency_agent.analyze_dependencies(test_sql, "usp_ProcessOrder", parsed_data, known_objects)
        
        print("[OK] SQL Dependency Agent Results:")
        print(f"   Dependencies: {len(result.dependencies.get('usp_ProcessOrder', []))} found")
        print(f"   Missing Objects: {len(result.missing_objects)} detected")
        for missing in result.missing_objects:
            print(f"     - {missing}")
        print(f"   Impact Level: {result.impact_analysis.get('impact_level', 'Unknown')}")
        print(f"   Change Risk: {result.impact_analysis.get('change_risk', 'Unknown')}")
        print(f"   Deployment Complexity: {result.impact_analysis.get('deployment_complexity', 'Unknown')}")
        print(f"   Circular Dependencies: {len(result.circular_dependencies)} found")
        print(f"   Confidence: {result.confidence_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_dependency_agent()
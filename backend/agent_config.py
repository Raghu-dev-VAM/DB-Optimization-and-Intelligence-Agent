"""
SQL Optimization Multi-Agent System Configuration
Defines the structure and roles of each agent in the system
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AgentConfig:
    """Configuration for individual agents"""
    name: str
    role: str
    system_message: str
    model: str = "llama3.2:1b"
    temperature: float = 0.1
    max_tokens: int = 1500

class SQLAgentSystem:
    """Defines the multi-agent system for SQL optimization"""
    
    def __init__(self):
        # Groq Configuration (Primary AI Provider)
        self.groq_config = {
            "api_key": os.getenv("GROQ_API_KEY"),
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "temperature": 0.1,
            "max_tokens": 3000
        }
        
        # Determine if Groq is available
        self.use_groq = bool(self.groq_config["api_key"])
        
        self.agents = self._define_agents()
    
    def _define_agents(self) -> Dict[str, AgentConfig]:
        """Define all agents in the SQL optimization system"""
        
        return {
            "sql_parser": AgentConfig(
                name="SQL_Parser_Agent",
                role="SQL Analysis & Parsing",
                system_message="""You are a SQL Parser Agent specialized in analyzing SQL code structure.
                
Your responsibilities:
- Parse SQL queries, stored procedures, functions, and views
- Extract table names, column references, joins, and relationships
- Identify SQL object types (SELECT, INSERT, UPDATE, DELETE, CREATE, etc.)
- Extract referenced stored procedures and functions
- Detect missing dependencies and objects
- Provide structured analysis of SQL components

Always respond with clear, structured information about the SQL code structure."""
            ),
            
            "optimizer": AgentConfig(
                name="SQL_Optimizer_Agent", 
                role="Performance Optimization",
                system_message="""You are a SQL Optimization Agent focused on performance improvements.
                
Your responsibilities:
- Analyze query performance issues (SELECT *, cursors, functions in WHERE)
- Identify missing indexes and suggest index recommendations
- Detect parameter sniffing risks and TempDB pressure
- Find inefficient joins and subqueries
- Suggest query rewriting for better performance
- Generate optimized SQL alternatives
- Provide execution plan analysis recommendations

Focus on actionable performance improvements with clear explanations."""
            ),
            
            "security": AgentConfig(
                name="SQL_Security_Agent",
                role="Security Analysis", 
                system_message="""You are a SQL Security Agent specialized in identifying security vulnerabilities.
                
Your responsibilities:
- Detect SQL injection vulnerabilities in dynamic SQL
- Identify risky dynamic SQL construction patterns
- Check for proper input validation and parameterization
- Find missing error handling that could expose information
- Analyze stored procedure security and permissions
- Detect potential data exposure risks
- Suggest security best practices and fixes

Always prioritize security issues and provide clear remediation steps."""
            ),
            
            "dependency": AgentConfig(
                name="SQL_Dependency_Agent",
                role="Dependency Mapping",
                system_message="""You are a SQL Dependency Agent specialized in mapping object relationships.
                
Your responsibilities:
- Map dependencies between stored procedures, functions, and tables
- Track cross-references and call hierarchies
- Identify circular dependencies and potential issues
- Build dependency graphs and impact analysis
- Detect missing referenced objects
- Analyze deployment order requirements
- Provide impact assessment for changes

Focus on comprehensive dependency mapping and change impact analysis."""
            ),
            
            "reporter": AgentConfig(
                name="SQL_Reporter_Agent",
                role="Report Generation",
                system_message="""You are a SQL Reporter Agent specialized in generating comprehensive analysis reports.
                
Your responsibilities:
- Compile findings from all other agents into structured reports
- Generate executive summaries and technical details
- Create actionable recommendations and priority lists
- Format reports for different audiences (developers, DBAs, managers)
- Generate migration scripts and deployment guides
- Create documentation and best practice guides
- Provide clear, professional reporting

Always create well-structured, actionable reports with clear priorities."""
            ),
            
            "orchestrator": AgentConfig(
                name="SQL_Orchestrator_Agent",
                role="Workflow Coordination",
                system_message="""You are the SQL Orchestrator Agent responsible for coordinating the entire analysis workflow.
                
Your responsibilities:
- Coordinate analysis workflow between all agents
- Determine which agents need to be involved for each task
- Manage information flow and dependencies between agents
- Prioritize tasks and optimize analysis sequence
- Handle error recovery and fallback strategies
- Ensure comprehensive analysis coverage
- Coordinate final report compilation

You are the conductor of the SQL analysis orchestra - ensure all agents work together effectively."""
            )
        }
    
    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent"""
        return self.agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all available agents"""
        return list(self.agents.keys())
    
    def get_workflow_sequence(self, analysis_type: str) -> List[str]:
        """Define agent execution sequence based on analysis type"""
        
        workflows = {
            "full_analysis": [
                "sql_parser",      # Parse SQL structure first
                "dependency",      # Map dependencies 
                "optimizer",       # Analyze performance
                "security",        # Check security
                "reporter"         # Generate final report
            ],
            
            "performance_only": [
                "sql_parser",      # Parse structure
                "optimizer",       # Focus on performance
                "reporter"         # Generate performance report
            ],
            
            "security_only": [
                "sql_parser",      # Parse structure  
                "security",        # Focus on security
                "reporter"         # Generate security report
            ],
            
            "dependency_only": [
                "sql_parser",      # Parse structure
                "dependency",      # Map dependencies
                "reporter"         # Generate dependency report
            ]
        }
        
        return workflows.get(analysis_type, workflows["full_analysis"])

# Global instance
sql_agent_system = SQLAgentSystem()

if __name__ == "__main__":
    print("🤖 SQL Multi-Agent System Configuration")
    print(f"📋 Available Agents: {sql_agent_system.list_agents()}")
    print(f"🔄 Full Analysis Workflow: {sql_agent_system.get_workflow_sequence('full_analysis')}")
    
    # Display agent details
    for agent_name in sql_agent_system.list_agents():
        config = sql_agent_system.get_agent_config(agent_name)
        print(f"\n🎯 {config.name}")
        print(f"   Role: {config.role}")
        print(f"   Model: {config.model}")
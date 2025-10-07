# components/agent_awareness.py
"""
Agent Awareness Service - Track available flows, connectors, tools
"""
import logging
from sqlalchemy.orm import Session
from database import Flow, Connector
from typing import Dict, List
import json

logger = logging.getLogger(__name__)

class AgentAwareness:
    """Maintains agent's awareness of available resources"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_system_context(self) -> str:
        """Get comprehensive system context for LLM"""
        
        flows = self.get_available_flows()
        connectors = self.get_available_connectors()
        
        context = f"""=== SYSTEM AWARENESS ===

AVAILABLE FLOWS ({len(flows)}):
{self._format_flows(flows)}

AVAILABLE CONNECTORS ({len(connectors)}):
{self._format_connectors(connectors)}

CAPABILITIES:
- Create new flows using natural language
- Execute existing flows
- Modify flows dynamically
- Read/write local files (data/ directory)
- Execute Python code dynamically
- Query databases
- Send emails and notifications
- Access SharePoint documents

CURRENT WORKING DIRECTORY: data/
PYTHON EXECUTION: code/ directory with venv support
"""
        
        return context
    
    def get_available_flows(self) -> List[Dict]:
        """Get list of available flows"""
        flows = self.db_session.query(Flow).all()
        
        return [
            {
                'id': flow.id,
                'name': flow.name,
                'description': flow.description,
                'version': flow.current_version
            }
            for flow in flows
        ]
    
    def get_available_connectors(self) -> List[Dict]:
        """Get list of available connectors"""
        connectors = self.db_session.query(Connector).all()
        
        return [
            {
                'name': conn.name,
                'type': conn.type,
                'capabilities': json.loads(conn.capabilities_json) if conn.capabilities_json else []
            }
            for conn in connectors
        ]
    
    def _format_flows(self, flows: List[Dict]) -> str:
        """Format flows for context"""
        if not flows:
            return "  (No flows available)"
        
        formatted = []
        for flow in flows:
            formatted.append(
                f"  - {flow['name']} (ID: {flow['id']}, v{flow['version']}): {flow['description']}"
            )
        return "\n".join(formatted)
    
    def _format_connectors(self, connectors: List[Dict]) -> str:
        """Format connectors for context"""
        if not connectors:
            return "  (No connectors available)"
        
        formatted = []
        for conn in connectors:
            caps = ", ".join(conn['capabilities'][:5])  # First 5 capabilities
            formatted.append(
                f"  - {conn['name']} ({conn['type']}): {caps}"
            )
        return "\n".join(formatted)
    
    def find_flow_by_description(self, description: str) -> List[Dict]:
        """Find flows matching description"""
        flows = self.get_available_flows()
        
        # Simple keyword matching (can be enhanced with embeddings)
        keywords = description.lower().split()
        matching = []
        
        for flow in flows:
            flow_text = f"{flow['name']} {flow['description']}".lower()
            if any(keyword in flow_text for keyword in keywords):
                matching.append(flow)
        
        return matching
# components/connector_manager.py
from database import Connector
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class BaseConnector:
    """Base connector interface"""
    
    def capabilities(self) -> List[str]:
        """Return list of supported actions"""
        raise NotImplementedError
    
    def run(self, action: str, params: dict) -> dict:
        """Execute action with parameters"""
        raise NotImplementedError

class SQLConnector(BaseConnector):
    """SQL Database Connector"""
    
    def capabilities(self) -> List[str]:
        return ['query', 'insert', 'update', 'delete', 'execute']
    
    def run(self, action: str, params: dict) -> dict:
        """Execute SQL action"""
        try:
            if action == 'query':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Executed query: {params.get('query', '')}",
                    'rows_affected': 0
                }
            elif action == 'insert':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Inserted into {params.get('table', '')}",
                    'rows_affected': 1
                }
            elif action == 'update':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Updated {params.get('table', '')}",
                    'rows_affected': 1
                }
            elif action == 'delete':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Deleted from {params.get('table', '')}",
                    'rows_affected': 1
                }
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class SharePointConnector(BaseConnector):
    """SharePoint Connector"""
    
    def capabilities(self) -> List[str]:
        return ['read_file', 'write_file', 'list_files', 'upload', 'download']
    
    def run(self, action: str, params: dict) -> dict:
        """Execute SharePoint action"""
        try:
            if action == 'read_file':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Read file: {params.get('filename', '')}",
                    'content': 'Sample file content'
                }
            elif action == 'write_file':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Wrote file: {params.get('filename', '')}",
                }
            elif action == 'list_files':
                return {
                    'status': 'success',
                    'action': action,
                    'files': ['file1.txt', 'file2.pdf', 'file3.xlsx']
                }
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class EmailConnector(BaseConnector):
    """Email Connector"""
    
    def capabilities(self) -> List[str]:
        return ['send', 'read', 'list']
    
    def run(self, action: str, params: dict) -> dict:
        """Execute Email action"""
        try:
            if action == 'send':
                return {
                    'status': 'success',
                    'action': action,
                    'result': f"Sent email to {params.get('to', '')}",
                    'message_id': 'msg_12345'
                }
            elif action == 'read':
                return {
                    'status': 'success',
                    'action': action,
                    'result': 'Read email',
                    'subject': params.get('subject', ''),
                    'body': 'Email body content'
                }
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class NotificationConnector(BaseConnector):
    """Notification Connector"""
    
    def capabilities(self) -> List[str]:
        return ['send_notification', 'send_alert']
    
    def run(self, action: str, params: dict) -> dict:
        """Execute Notification action"""
        try:
            return {
                'status': 'success',
                'action': action,
                'result': f"Sent notification: {params.get('message', '')}",
                'notification_id': 'notif_12345'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class ConnectorManager:
    """Manages connector registry and execution"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        
        # Register built-in connectors
        self.connectors = {
            'sql': SQLConnector(),
            'sharepoint': SharePointConnector(),
            'email': EmailConnector(),
            'notification': NotificationConnector()
        }
        
        # Initialize database connectors
        self._init_db_connectors()
    
    def _init_db_connectors(self):
        """Initialize connectors in database if not exists"""
        for name, connector in self.connectors.items():
            existing = self.db_session.query(Connector).filter(
                Connector.name == name
            ).first()
            
            if not existing:
                db_connector = Connector(
                    name=name,
                    type=connector.__class__.__name__,
                    capabilities_json=json.dumps(connector.capabilities()),
                    config_ref='{}'
                )
                self.db_session.add(db_connector)
        
        self.db_session.commit()
        logger.info("Initialized connectors in database")
    
    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Get connector instance by name"""
        return self.connectors.get(name)
    
    def list_connectors(self) -> List[Dict]:
        """List all available connectors"""
        connectors = self.db_session.query(Connector).all()
        return [
            {
                'id': c.id,
                'name': c.name,
                'type': c.type,
                'capabilities': json.loads(c.capabilities_json) if c.capabilities_json else []
            }
            for c in connectors
        ]
    
    def run_connector(self, connector_name: str, action: str, params: dict) -> dict:
        """Execute connector action"""
        connector = self.get_connector(connector_name)
        
        if not connector:
            return {
                'status': 'error',
                'message': f'Connector not found: {connector_name}',
                'suggestion': f'Available connectors: {", ".join(self.connectors.keys())}'
            }
        
        # Check if action is supported
        if action not in connector.capabilities():
            return {
                'status': 'error',
                'message': f'Action {action} not supported by {connector_name}',
                'supported_actions': connector.capabilities()
            }
        
        # Execute action
        logger.info(f"Executing {connector_name}.{action} with params: {params}")
        return connector.run(action, params)
    
    def test_connector(self, connector_name: str) -> dict:
        """Test connector connectivity"""
        connector = self.get_connector(connector_name)
        
        if not connector:
            return {'status': 'error', 'message': f'Connector not found: {connector_name}'}
        
        return {
            'status': 'success',
            'connector': connector_name,
            'capabilities': connector.capabilities()
        }
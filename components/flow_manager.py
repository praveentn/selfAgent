# components/flow_manager.py
from database import Flow, FlowVersion
from sqlalchemy.orm import Session
from pathlib import Path
import yaml
import json
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class FlowManager:
    """Manages process flow CRUD operations and versioning"""
    
    def __init__(self, db_session: Session, flows_dir: str = 'flows'):
        self.db_session = db_session
        self.flows_dir = Path(flows_dir)
        self.flows_dir.mkdir(exist_ok=True)
    
    def create_flow(self, name: str, description: str, steps: List[Dict], author: str = 'system') -> Flow:
        """Create new flow with initial version"""
        # Create flow record
        flow = Flow(
            name=name,
            description=description,
            current_version=1
        )
        self.db_session.add(flow)
        self.db_session.commit()
        self.db_session.refresh(flow)
        
        # Create flow directory
        flow_dir = self.flows_dir / str(flow.id)
        flow_dir.mkdir(exist_ok=True)
        
        # Create flow content
        flow_content = {
            'id': flow.id,
            'name': name,
            'description': description,
            'version': 1,
            'steps': steps
        }
        
        # Save flow file
        filename = f'v1.yaml'
        filepath = flow_dir / filename
        
        with open(filepath, 'w') as f:
            yaml.dump(flow_content, f, default_flow_style=False)
        
        # Create version record
        version = FlowVersion(
            flow_id=flow.id,
            version_no=1,
            filename=str(filepath),
            author=author
        )
        self.db_session.add(version)
        self.db_session.commit()
        
        logger.info(f"Created flow: {name} (ID: {flow.id})")
        return flow
    
    def get_flow(self, flow_id: int) -> Optional[Flow]:
        """Get flow by ID"""
        return self.db_session.query(Flow).filter(Flow.id == flow_id).first()
    
    def get_flow_by_name(self, name: str) -> Optional[Flow]:
        """Get flow by name"""
        return self.db_session.query(Flow).filter(Flow.name == name).first()
    
    def list_flows(self) -> List[Flow]:
        """List all flows"""
        return self.db_session.query(Flow).all()
    
    def load_flow_content(self, flow_id: int, version_no: Optional[int] = None) -> Optional[Dict]:
        """Load flow content from file"""
        flow = self.get_flow(flow_id)
        if not flow:
            return None
        
        # Use current version if not specified
        if version_no is None:
            version_no = flow.current_version
        
        # Get version record
        version = self.db_session.query(FlowVersion).filter(
            FlowVersion.flow_id == flow_id,
            FlowVersion.version_no == version_no
        ).first()
        
        if not version:
            return None
        
        # Load file
        try:
            with open(version.filename, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading flow content: {e}")
            return None
    
    def update_flow(
        self, 
        flow_id: int, 
        steps: List[Dict], 
        description: Optional[str] = None,
        author: str = 'system'
    ) -> FlowVersion:
        """Create new version of flow"""
        flow = self.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")
        
        # Increment version
        new_version_no = flow.current_version + 1
        
        # Update description if provided
        if description:
            flow.description = description
        
        # Create new flow content
        flow_content = {
            'id': flow.id,
            'name': flow.name,
            'description': flow.description,
            'version': new_version_no,
            'steps': steps
        }
        
        # Save new version file
        flow_dir = self.flows_dir / str(flow.id)
        filename = f'v{new_version_no}.yaml'
        filepath = flow_dir / filename
        
        with open(filepath, 'w') as f:
            yaml.dump(flow_content, f, default_flow_style=False)
        
        # Create version record
        version = FlowVersion(
            flow_id=flow.id,
            version_no=new_version_no,
            filename=str(filepath),
            author=author
        )
        self.db_session.add(version)
        
        # Update current version
        flow.current_version = new_version_no
        flow.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        
        logger.info(f"Updated flow {flow.name} to v{new_version_no}")
        return version
    
    def modify_flow_steps(
        self,
        flow_id: int,
        action: str,
        anchor_step_id: Optional[str] = None,
        position: Optional[str] = None,
        new_step: Optional[Dict] = None,
        step_id: Optional[str] = None,
        author: str = 'system'
    ) -> FlowVersion:
        """
        Modify flow steps (insert, update, delete)
        
        Args:
            action: 'insert_step', 'update_step', 'delete_step'
            anchor_step_id: Reference step for insertion
            position: 'before' or 'after' for insertion
            new_step: New step definition for insert/update
            step_id: Step ID for update/delete
        """
        # Load current flow
        flow_content = self.load_flow_content(flow_id)
        if not flow_content:
            raise ValueError(f"Flow {flow_id} not found")
        
        steps = flow_content.get('steps', [])
        
        # Perform modification
        if action == 'insert_step':
            if not anchor_step_id or not position or not new_step:
                raise ValueError("Insert requires anchor_step_id, position, and new_step")
            
            # Find anchor index
            anchor_idx = None
            for i, step in enumerate(steps):
                if step.get('id') == anchor_step_id:
                    anchor_idx = i
                    break
            
            if anchor_idx is None:
                raise ValueError(f"Anchor step {anchor_step_id} not found")
            
            # Insert step
            insert_idx = anchor_idx + 1 if position == 'after' else anchor_idx
            steps.insert(insert_idx, new_step)
            logger.info(f"Inserted step {new_step.get('id')} {position} {anchor_step_id}")
        
        elif action == 'update_step':
            if not step_id or not new_step:
                raise ValueError("Update requires step_id and new_step")
            
            # Find and update step
            updated = False
            for i, step in enumerate(steps):
                if step.get('id') == step_id:
                    steps[i] = new_step
                    updated = True
                    break
            
            if not updated:
                raise ValueError(f"Step {step_id} not found")
            
            logger.info(f"Updated step {step_id}")
        
        elif action == 'delete_step':
            if not step_id:
                raise ValueError("Delete requires step_id")
            
            # Find and remove step
            steps = [step for step in steps if step.get('id') != step_id]
            logger.info(f"Deleted step {step_id}")
        
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Create new version with modified steps
        return self.update_flow(flow_id, steps, author=author)
    
    def delete_flow(self, flow_id: int):
        """Delete flow and all versions"""
        flow = self.get_flow(flow_id)
        if not flow:
            return
        
        # Delete flow directory
        flow_dir = self.flows_dir / str(flow_id)
        if flow_dir.exists():
            import shutil
            shutil.rmtree(flow_dir)
        
        # Delete from database (cascade will handle versions)
        self.db_session.delete(flow)
        self.db_session.commit()
        
        logger.info(f"Deleted flow {flow_id}")
    
    def validate_flow(self, flow_content: Dict) -> tuple[bool, List[str]]:
        """Validate flow structure"""
        errors = []
        
        # Check required fields
        if 'id' not in flow_content:
            errors.append("Missing flow ID")
        if 'name' not in flow_content:
            errors.append("Missing flow name")
        if 'steps' not in flow_content:
            errors.append("Missing steps")
        
        # Validate steps
        steps = flow_content.get('steps', [])
        step_ids = set()
        
        for i, step in enumerate(steps):
            if 'id' not in step:
                errors.append(f"Step {i} missing ID")
            else:
                if step['id'] in step_ids:
                    errors.append(f"Duplicate step ID: {step['id']}")
                step_ids.add(step['id'])
            
            if 'name' not in step:
                errors.append(f"Step {i} missing name")
            if 'type' not in step:
                errors.append(f"Step {i} missing type")
        
        return len(errors) == 0, errors
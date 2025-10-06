# components/executor.py
from database import Run, RunStep
from components.flow_manager import FlowManager
from components.connector_manager import ConnectorManager
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class Executor:
    """Executes process flows step by step"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.flow_manager = FlowManager(db_session)
        self.connector_manager = ConnectorManager(db_session)
    
    def execute_flow(self, flow_id: int, version_no: int = None) -> Run:
        """Execute a flow and return run record"""
        # Load flow content
        flow_content = self.flow_manager.load_flow_content(flow_id, version_no)
        if not flow_content:
            raise ValueError(f"Flow {flow_id} not found")
        
        flow = self.flow_manager.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")
        
        # Use current version if not specified
        if version_no is None:
            version_no = flow.current_version
        
        # Create run record
        run = Run(
            flow_id=flow_id,
            version_no=version_no,
            status='running',
            started_at=datetime.utcnow()
        )
        self.db_session.add(run)
        self.db_session.commit()
        self.db_session.refresh(run)
        
        logger.info(f"Starting run {run.id} for flow {flow.name} v{version_no}")
        
        # Create run steps
        steps = flow_content.get('steps', [])
        for step in steps:
            run_step = RunStep(
                run_id=run.id,
                step_id=step.get('id', ''),
                name=step.get('name', ''),
                status='pending'
            )
            self.db_session.add(run_step)
        
        self.db_session.commit()
        
        # Execute steps
        try:
            for step in steps:
                self._execute_step(run.id, step)
            
            # Mark run as completed
            run.status = 'completed'
            run.finished_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Completed run {run.id}")
        
        except Exception as e:
            # Mark run as failed
            run.status = 'failed'
            run.finished_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.error(f"Run {run.id} failed: {e}")
            raise
        
        return run
    
    def _execute_step(self, run_id: int, step: dict):
        """Execute a single step"""
        step_id = step.get('id')
        step_name = step.get('name')
        connector_name = step.get('connector')
        action = step.get('action')
        params = step.get('params', {})
        
        # Get run step record
        run_step = self.db_session.query(RunStep).filter(
            RunStep.run_id == run_id,
            RunStep.step_id == step_id
        ).first()
        
        if not run_step:
            logger.error(f"Run step not found: {step_id}")
            return
        
        # Update status to running
        run_step.status = 'running'
        run_step.started_at = datetime.utcnow()
        self.db_session.commit()
        
        logger.info(f"Executing step {step_id}: {step_name}")
        
        try:
            # Execute connector action
            if connector_name and action:
                result = self.connector_manager.run_connector(connector_name, action, params)
            else:
                result = {'status': 'success', 'message': 'No action specified'}
            
            # Handle result
            if result.get('status') == 'error':
                # Check for retry policy
                retry = step.get('retry', {})
                if retry.get('enabled'):
                    max_attempts = retry.get('max_attempts', 3)
                    # For simplicity, we're not implementing retry logic here
                    logger.warning(f"Step {step_id} failed, retry enabled but not implemented")
                
                # Mark as failed
                run_step.status = 'failed'
                run_step.result_json = json.dumps(result)
                run_step.finished_at = datetime.utcnow()
                self.db_session.commit()
                
                # Check error handling
                on_error = step.get('onError', 'stop')
                if on_error == 'stop':
                    raise Exception(f"Step {step_id} failed: {result.get('message')}")
                elif on_error == 'continue':
                    logger.warning(f"Step {step_id} failed but continuing: {result.get('message')}")
            else:
                # Mark as completed
                run_step.status = 'completed'
                run_step.result_json = json.dumps(result)
                run_step.finished_at = datetime.utcnow()
                self.db_session.commit()
                
                logger.info(f"Step {step_id} completed successfully")
        
        except Exception as e:
            run_step.status = 'failed'
            run_step.result_json = json.dumps({'status': 'error', 'message': str(e)})
            run_step.finished_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.error(f"Step {step_id} execution error: {e}")
            raise
    
    def get_run(self, run_id: int) -> Run:
        """Get run by ID"""
        return self.db_session.query(Run).filter(Run.id == run_id).first()
    
    def get_run_steps(self, run_id: int) -> list:
        """Get all steps for a run"""
        return self.db_session.query(RunStep).filter(RunStep.run_id == run_id).all()
    
    def get_run_status(self, run_id: int) -> dict:
        """Get detailed run status"""
        run = self.get_run(run_id)
        if not run:
            return None
        
        steps = self.get_run_steps(run_id)
        
        return {
            'run_id': run.id,
            'flow_id': run.flow_id,
            'version_no': run.version_no,
            'status': run.status,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'finished_at': run.finished_at.isoformat() if run.finished_at else None,
            'steps': [
                {
                    'step_id': step.step_id,
                    'name': step.name,
                    'status': step.status,
                    'result': json.loads(step.result_json) if step.result_json else None,
                    'started_at': step.started_at.isoformat() if step.started_at else None,
                    'finished_at': step.finished_at.isoformat() if step.finished_at else None
                }
                for step in steps
            ]
        }
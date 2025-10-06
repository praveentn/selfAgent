# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from database import init_database, get_db_session
from components.intent_detector import IntentDetector
from components.flow_manager import FlowManager
from components.executor import Executor
from components.connector_manager import ConnectorManager
from components.memory_manager import MemoryManager, ConversationManager
from components.azure_client import AzureOpenAIClient
from config import Config
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Self Agent API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
engine, SessionLocal = init_database()

# Pydantic models
class IntentRequest(BaseModel):
    text: str
    session_id: Optional[str] = "default"
    user_id: Optional[str] = "default_user"

class IntentResponse(BaseModel):
    intent: str
    confidence: float
    parameters: Dict
    response: Optional[str] = None

class FlowCreate(BaseModel):
    name: str
    description: str
    steps: List[Dict]
    author: Optional[str] = "system"

class FlowModify(BaseModel):
    action: str  # insert_step, update_step, delete_step
    anchor_step_id: Optional[str] = None
    position: Optional[str] = None  # before, after
    new_step: Optional[Dict] = None
    step_id: Optional[str] = None
    author: Optional[str] = "system"

class FlowExecute(BaseModel):
    flow_id: int
    version_no: Optional[int] = None

class ConnectorTest(BaseModel):
    connector_name: str

class IndexText(BaseModel):
    text: str
    source_type: str
    source_id: str

class SemanticQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SQLExecute(BaseModel):
    query: str
    page: Optional[int] = 1
    page_size: Optional[int] = 50

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "running"
    }

@app.post("/intent", response_model=IntentResponse)
async def detect_intent(request: IntentRequest, db: Session = Depends(get_db)):
    """Detect user intent from natural language"""
    try:
        # Initialize components
        intent_detector = IntentDetector(db)
        conversation_manager = ConversationManager(db)
        azure_client = AzureOpenAIClient()
        
        # Get conversation history
        history = conversation_manager.get_recent_context(request.user_id, n=5)
        
        # Detect intent
        intent, confidence, parameters = intent_detector.detect_intent(
            request.text,
            conversation_history=history
        )
        
        # Generate response
        context = f"Detected intent: {intent} (confidence: {confidence:.2f})"
        response_text = azure_client.generate_response(
            request.text,
            context=context,
            conversation_history=history
        )
        
        # Store conversation
        conversation_manager.add_message(request.text, 'user', request.user_id)
        conversation_manager.add_message(response_text, 'assistant', request.user_id)
        
        return IntentResponse(
            intent=intent,
            confidence=confidence,
            parameters=parameters,
            response=response_text
        )
    
    except Exception as e:
        logger.error(f"Intent detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flows")
async def create_flow(flow: FlowCreate, db: Session = Depends(get_db)):
    """Create new flow"""
    try:
        flow_manager = FlowManager(db)
        new_flow = flow_manager.create_flow(
            name=flow.name,
            description=flow.description,
            steps=flow.steps,
            author=flow.author
        )
        
        return {
            "flow_id": new_flow.id,
            "name": new_flow.name,
            "version": new_flow.current_version,
            "status": "created"
        }
    
    except Exception as e:
        logger.error(f"Flow creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flows/{flow_id}")
async def get_flow(flow_id: int, db: Session = Depends(get_db)):
    """Get flow by ID"""
    try:
        flow_manager = FlowManager(db)
        flow = flow_manager.get_flow(flow_id)
        
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow_content = flow_manager.load_flow_content(flow_id)
        
        return {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "current_version": flow.current_version,
            "created_at": flow.created_at.isoformat(),
            "updated_at": flow.updated_at.isoformat(),
            "content": flow_content
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get flow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flows")
async def list_flows(db: Session = Depends(get_db)):
    """List all flows"""
    try:
        flow_manager = FlowManager(db)
        flows = flow_manager.list_flows()
        
        return [
            {
                "id": flow.id,
                "name": flow.name,
                "description": flow.description,
                "current_version": flow.current_version,
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat()
            }
            for flow in flows
        ]
    
    except Exception as e:
        logger.error(f"List flows error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flows/{flow_id}/execute")
async def execute_flow(flow_id: int, db: Session = Depends(get_db)):
    """Execute flow"""
    try:
        executor = Executor(db)
        run = executor.execute_flow(flow_id)
        
        return {
            "run_id": run.id,
            "flow_id": run.flow_id,
            "status": run.status,
            "started_at": run.started_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Flow execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/runs/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get run status"""
    try:
        executor = Executor(db)
        run_status = executor.get_run_status(run_id)
        
        if not run_status:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return run_status
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flows/{flow_id}/modify")
async def modify_flow(flow_id: int, modification: FlowModify, db: Session = Depends(get_db)):
    """Modify flow"""
    try:
        flow_manager = FlowManager(db)
        
        new_version = flow_manager.modify_flow_steps(
            flow_id=flow_id,
            action=modification.action,
            anchor_step_id=modification.anchor_step_id,
            position=modification.position,
            new_step=modification.new_step,
            step_id=modification.step_id,
            author=modification.author
        )
        
        return {
            "flow_id": flow_id,
            "version_no": new_version.version_no,
            "status": "modified"
        }
    
    except Exception as e:
        logger.error(f"Flow modification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{session_id}")
async def get_conversations(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get conversation history"""
    try:
        conversation_manager = ConversationManager(db)
        conversations = conversation_manager.get_conversation_history(
            user_id=session_id,
            limit=limit
        )
        
        return [
            {
                "id": conv.id,
                "message": conv.message,
                "role": conv.role,
                "timestamp": conv.timestamp.isoformat(),
                "flow_id": conv.flow_id
            }
            for conv in reversed(conversations)
        ]
    
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/connectors/test")
async def test_connector(test: ConnectorTest, db: Session = Depends(get_db)):
    """Test connector"""
    try:
        connector_manager = ConnectorManager(db)
        result = connector_manager.test_connector(test.connector_name)
        return result
    
    except Exception as e:
        logger.error(f"Connector test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/connectors")
async def list_connectors(db: Session = Depends(get_db)):
    """List all connectors"""
    try:
        connector_manager = ConnectorManager(db)
        return connector_manager.list_connectors()
    
    except Exception as e:
        logger.error(f"List connectors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index/text")
async def index_text(request: IndexText, db: Session = Depends(get_db)):
    """Index text for semantic search"""
    try:
        memory_manager = MemoryManager(db)
        memory_manager.index_memory(
            text=request.text,
            source_type=request.source_type,
            source_id=request.source_id
        )
        
        return {"status": "indexed"}
    
    except Exception as e:
        logger.error(f"Index text error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/semantic")
async def semantic_query(request: SemanticQuery, db: Session = Depends(get_db)):
    """Semantic search"""
    try:
        memory_manager = MemoryManager(db)
        results = memory_manager.recall(request.query, request.top_k)
        return {"results": results}
    
    except Exception as e:
        logger.error(f"Semantic query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/sql")
async def execute_sql(request: SQLExecute, db: Session = Depends(get_db)):
    """Execute raw SQL query with pagination"""
    try:
        # Execute query
        result = db.execute(text(request.query))
        
        # Handle SELECT queries
        if request.query.strip().upper().startswith('SELECT'):
            rows = result.fetchall()
            columns = list(result.keys()) if rows else []
            
            # Pagination
            total_rows = len(rows)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_rows = rows[start_idx:end_idx]
            
            return {
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in paginated_rows],
                "total_rows": total_rows,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": (total_rows + request.page_size - 1) // request.page_size
            }
        else:
            # For INSERT, UPDATE, DELETE, etc.
            db.commit()
            return {
                "status": "success",
                "message": "Query executed successfully",
                "rows_affected": result.rowcount
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"SQL execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
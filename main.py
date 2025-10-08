# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Self Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class FlowUpdate(BaseModel):
    description: Optional[str] = None
    steps: List[Dict]
    author: Optional[str] = "system"

class FlowModify(BaseModel):
    action: str
    anchor_step_id: Optional[str] = None
    position: Optional[str] = None
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

class FlowDescriptionRequest(BaseModel):
    description: str = Field(..., description="Natural language description of the flow")

class ToolGenerateRequest(BaseModel):
    tool_type: str = Field(default="file_reader", description="Type of tool to generate")
    params: Dict = Field(default_factory=dict, description="Tool parameters")

class MemoryStoreRequest(BaseModel):
    content: str
    user_id: Optional[str] = "default_user"

class RuleSetRequest(BaseModel):
    rule: str
    user_id: Optional[str] = "default_user"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "app": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "running"
    }

@app.post("/intent", response_model=IntentResponse)
async def detect_intent(request: IntentRequest, db: Session = Depends(get_db)):
    """Detect user intent with parameter extraction"""
    try:
        intent_detector = IntentDetector(db)
        conversation_manager = ConversationManager(db)
        memory_manager = MemoryManager(db)
        azure_client = AzureOpenAIClient()
        
        # Get conversation history
        history = conversation_manager.get_recent_context(
            request.user_id, 
            n=5, 
            session_id=request.session_id
        )
        
        # Detect intent with parameters
        intent, confidence, parameters = intent_detector.detect_intent(
            request.text,
            conversation_history=history
        )
        
        # Check if this is a memory storage request
        if any(keyword in request.text.lower() for keyword in ['remember', 'save this', 'store this', 'always', 'never']):
            memory_type = memory_manager.classify_memory_type(request.text)
            
            if memory_type == 'RULE':
                intent = 'set_rule'
                parameters['rule'] = request.text
            elif memory_type == 'LONG_TERM':
                intent = 'store_memory'
                parameters['content'] = request.text
                parameters['memory_type'] = 'LONG_TERM'
        
        # Get user context from long-term memory and rules
        user_context = memory_manager.get_context_for_user(request.user_id)
        
        # Get system prompt with rules
        base_prompt = f"Detected intent: {intent} (confidence: {confidence:.2f})"
        if user_context:
            base_prompt += f"\nUser context: {user_context}"
        
        system_prompt = memory_manager.get_system_prompt_with_rules(
            base_prompt,
            request.user_id
        )
        
        # Generate response
        response_text = azure_client.generate_response(
            request.text,
            context=system_prompt,
            conversation_history=history
        )
        
        # Store conversation
        conversation_manager.add_message(
            request.text, 
            'user', 
            request.user_id,
            session_id=request.session_id
        )
        conversation_manager.add_message(
            response_text, 
            'assistant', 
            request.user_id,
            session_id=request.session_id
        )
        
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

@app.post("/flows/{flow_id}/update")
async def update_flow(flow_id: int, update: FlowUpdate, db: Session = Depends(get_db)):
    """Update flow with new version"""
    try:
        flow_manager = FlowManager(db)
        
        new_version = flow_manager.update_flow(
            flow_id=flow_id,
            steps=update.steps,
            description=update.description,
            author=update.author
        )
        
        return {
            "flow_id": flow_id,
            "version_no": new_version.version_no,
            "status": "updated"
        }
    
    except Exception as e:
        logger.error(f"Flow update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/flows/{flow_id}")
async def delete_flow(flow_id: int, db: Session = Depends(get_db)):
    """Delete flow"""
    try:
        flow_manager = FlowManager(db)
        flow_manager.delete_flow(flow_id)
        
        return {"status": "deleted", "flow_id": flow_id}
    
    except Exception as e:
        logger.error(f"Flow deletion error: {e}")
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

@app.get("/conversations/{user_id}")
async def get_conversations(
    user_id: str,
    limit: int = 50,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get conversation history"""
    try:
        conversation_manager = ConversationManager(db)
        conversations = conversation_manager.get_conversation_history(
            user_id=user_id,
            limit=limit,
            session_id=session_id
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

@app.get("/conversations/sessions/{user_id}")
async def get_sessions(user_id: str, db: Session = Depends(get_db)):
    """Get all conversation sessions"""
    try:
        conversation_manager = ConversationManager(db)
        sessions = conversation_manager.get_all_sessions(user_id)
        
        return sessions
    
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversations/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Delete a conversation session"""
    try:
        conversation_manager = ConversationManager(db)
        conversation_manager.clear_session(session_id, user_id)
        
        return {"status": "deleted", "session_id": session_id}
    
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/store")
async def store_memory(request: MemoryStoreRequest, db: Session = Depends(get_db)):
    """Store memory with automatic classification"""
    try:
        memory_manager = MemoryManager(db)
        
        # Classify memory type
        memory_type = memory_manager.classify_memory_type(request.content)
        
        # Generate key from content
        key = request.content[:50].replace(' ', '_').lower()
        
        # Store memory
        memory_manager.store_memory(
            key=key,
            value=request.content,
            memory_type=memory_type,
            user_id=request.user_id
        )
        
        return {
            "status": "stored",
            "memory_type": memory_type,
            "content": request.content
        }
    
    except Exception as e:
        logger.error(f"Store memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/set_rule")
async def set_rule(request: RuleSetRequest, db: Session = Depends(get_db)):
    """Set behavior rule"""
    try:
        memory_manager = MemoryManager(db)
        
        # Generate key from rule
        key = request.rule[:50].replace(' ', '_').lower()
        
        # Store as rule
        memory_manager.store_memory(
            key=key,
            value=request.rule,
            memory_type='RULE',
            user_id=request.user_id
        )
        
        return {
            "status": "rule_set",
            "rule": request.rule
        }
    
    except Exception as e:
        logger.error(f"Set rule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/rules/{user_id}")
async def get_rules(user_id: str, db: Session = Depends(get_db)):
    """Get all rules for user"""
    try:
        memory_manager = MemoryManager(db)
        rules = memory_manager.get_all_rules(user_id)
        
        return rules
    
    except Exception as e:
        logger.error(f"Get rules error: {e}")
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
        result = db.execute(text(request.query))
        
        if request.query.strip().upper().startswith('SELECT'):
            rows = result.fetchall()
            columns = list(result.keys()) if rows else []
            
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

@app.post("/flows/create_from_description")
async def create_flow_from_description(
    request: FlowDescriptionRequest,
    db: Session = Depends(get_db)
):
    """Create flow from natural language description"""
    try:
        from components.agent_awareness import AgentAwareness
        
        azure_client = AzureOpenAIClient()
        agent_awareness = AgentAwareness(db)
        
        system_context = agent_awareness.get_system_context()
        
        flow_def = azure_client.generate_flow_from_description(
            request.description,
            system_context
        )
        
        if not flow_def or not flow_def.get('steps'):
            raise HTTPException(status_code=500, detail="Failed to generate valid flow definition")
        
        flow_manager = FlowManager(db)
        new_flow = flow_manager.create_flow(
            name=flow_def.get('name', 'Generated Flow'),
            description=flow_def.get('description', request.description),
            steps=flow_def.get('steps', []),
            author='agent'
        )
        
        return {
            "flow_id": new_flow.id,
            "name": new_flow.name,
            "version": new_flow.current_version,
            "status": "created",
            "definition": flow_def
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flow creation from description error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/generate")
async def generate_tool(request: ToolGenerateRequest, db: Session = Depends(get_db)):
    """Generate Python tool code"""
    try:
        from components.code_generator import CodeGenerator
        
        code_gen = CodeGenerator()
        
        if request.tool_type == 'file_reader':
            code = code_gen.generate_file_reader_tool(
                filename=request.params.get('filename', 'file1.txt'),
                file_path=request.params.get('file_path')
            )
        else:
            code = code_gen.generate_custom_tool(
                description=request.params.get('description', ''),
                requirements=request.params
            )
        
        return {
            "status": "success",
            "tool_type": request.tool_type,
            "code": code
        }
    
    except Exception as e:
        logger.error(f"Tool generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/awareness")
async def get_system_awareness(db: Session = Depends(get_db)):
    """Get system awareness context"""
    try:
        from components.agent_awareness import AgentAwareness
        
        awareness = AgentAwareness(db)
        
        return {
            "flows": awareness.get_available_flows(),
            "connectors": awareness.get_available_connectors(),
            "context": awareness.get_system_context()
        }
    
    except Exception as e:
        logger.error(f"System awareness error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
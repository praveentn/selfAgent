# database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import Config

Base = declarative_base()

class Flow(Base):
    __tablename__ = 'flows'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    versions = relationship("FlowVersion", back_populates="flow", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="flow", cascade="all, delete-orphan")

class FlowVersion(Base):
    __tablename__ = 'flow_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(Integer, ForeignKey('flows.id'), nullable=False)
    version_no = Column(Integer, nullable=False)
    filename = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    author = Column(String(255), default='system')
    
    flow = relationship("Flow", back_populates="versions")

class Run(Base):
    __tablename__ = 'runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(Integer, ForeignKey('flows.id'), nullable=False)
    version_no = Column(Integer, nullable=False)
    status = Column(String(50), default='queued')  # queued, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    
    flow = relationship("Flow", back_populates="runs")
    steps = relationship("RunStep", back_populates="run", cascade="all, delete-orphan")

class RunStep(Base):
    __tablename__ = 'run_steps'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey('runs.id'), nullable=False)
    step_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    result_json = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    
    run = relationship("Run", back_populates="steps")

class Connector(Base):
    __tablename__ = 'connectors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(100), nullable=False)
    capabilities_json = Column(Text)
    config_ref = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), default='default_user')
    flow_id = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_id = Column(String(255))

class MemoryKV(Base):
    __tablename__ = 'memory_kv'
    
    key = Column(String(255), primary_key=True)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

class VectorMeta(Base):
    __tablename__ = 'vector_meta'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(100), nullable=False)  # flow, run_step, conversation, memory
    source_id = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class IntentSample(Base):
    __tablename__ = 'intent_samples'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    intent = Column(String(100), nullable=False)
    sample_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database initialization
def init_database():
    """Initialize database and create all tables"""
    engine = create_engine(
        f'sqlite:///{Config.DB_PATH}',
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Seed initial intent samples
    session = SessionLocal()
    try:
        if session.query(IntentSample).count() == 0:
            seed_intents = [
                IntentSample(intent='run_flow', sample_text='run the invoice flow'),
                IntentSample(intent='run_flow', sample_text='execute the process'),
                IntentSample(intent='run_flow', sample_text='start the workflow'),
                IntentSample(intent='modify_flow', sample_text='add a step after validation'),
                IntentSample(intent='modify_flow', sample_text='update the process'),
                IntentSample(intent='modify_flow', sample_text='change the workflow'),
                IntentSample(intent='ask_history', sample_text='show me execution history'),
                IntentSample(intent='ask_history', sample_text='what happened in the last run'),
                IntentSample(intent='ask_history', sample_text='display previous runs'),
                IntentSample(intent='store_memory', sample_text='remember this for later'),
                IntentSample(intent='store_memory', sample_text='save this information'),
                IntentSample(intent='recall_memory', sample_text='what do you remember about'),
                IntentSample(intent='recall_memory', sample_text='find information about'),
                IntentSample(intent='create_flow', sample_text='create a new workflow'),
                IntentSample(intent='create_flow', sample_text='make a new process'),
                IntentSample(intent='list_flows', sample_text='show all workflows'),
                IntentSample(intent='list_flows', sample_text='what processes are available'),
            ]
            session.add_all(seed_intents)
            session.commit()
    finally:
        session.close()
    
    return engine, SessionLocal

def get_db_session():
    """Get database session"""
    _, SessionLocal = init_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

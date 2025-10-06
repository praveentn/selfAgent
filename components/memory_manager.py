# components/memory_manager.py
from database import MemoryKV, Conversation, VectorMeta
from components.vector_indexer import VectorIndexer
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages short-term and long-term memory"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.vector_indexer = VectorIndexer(index_path='faiss_index/memory')
    
    def store_kv(self, key: str, value: str):
        """Store key-value in memory"""
        existing = self.db_session.query(MemoryKV).filter(MemoryKV.key == key).first()
        
        if existing:
            existing.value = value
            existing.last_used_at = datetime.utcnow()
        else:
            memory = MemoryKV(key=key, value=value)
            self.db_session.add(memory)
        
        self.db_session.commit()
        logger.info(f"Stored memory: {key}")
    
    def get_kv(self, key: str) -> Optional[str]:
        """Retrieve key-value from memory"""
        memory = self.db_session.query(MemoryKV).filter(MemoryKV.key == key).first()
        
        if memory:
            memory.last_used_at = datetime.utcnow()
            self.db_session.commit()
            return memory.value
        
        return None
    
    def index_memory(self, text: str, source_type: str, source_id: str):
        """Index text for semantic search"""
        # Store in vector_meta
        meta = VectorMeta(
            source_type=source_type,
            source_id=source_id,
            text=text
        )
        self.db_session.add(meta)
        self.db_session.commit()
        self.db_session.refresh(meta)
        
        # Add to FAISS index
        self.vector_indexer.add_texts([text], [meta.id])
        logger.info(f"Indexed memory: {source_type}:{source_id}")
    
    def recall(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search in memory"""
        results = self.vector_indexer.search(query, top_k)
        
        memories = []
        for meta_id, similarity in results:
            meta = self.db_session.query(VectorMeta).filter(VectorMeta.id == meta_id).first()
            if meta:
                memories.append({
                    'text': meta.text,
                    'source_type': meta.source_type,
                    'source_id': meta.source_id,
                    'similarity': round(similarity, 3),
                    'created_at': meta.created_at.isoformat()
                })
        
        return memories

class ConversationManager:
    """Manages conversation history"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.memory_manager = MemoryManager(db_session)
    
    def add_message(
        self, 
        message: str, 
        role: str, 
        user_id: str = 'default_user',
        flow_id: Optional[int] = None,
        message_id: Optional[str] = None
    ) -> Conversation:
        """Add message to conversation history"""
        conversation = Conversation(
            user_id=user_id,
            flow_id=flow_id,
            message=message,
            role=role,
            message_id=message_id
        )
        self.db_session.add(conversation)
        self.db_session.commit()
        self.db_session.refresh(conversation)
        
        # Index important messages
        if role in ['user', 'assistant']:
            self.memory_manager.index_memory(
                text=message,
                source_type='conversation',
                source_id=str(conversation.id)
            )
        
        return conversation
    
    def get_conversation_history(
        self, 
        user_id: str = 'default_user',
        limit: int = 50,
        flow_id: Optional[int] = None
    ) -> List[Conversation]:
        """Get conversation history"""
        query = self.db_session.query(Conversation).filter(
            Conversation.user_id == user_id
        )
        
        if flow_id is not None:
            query = query.filter(Conversation.flow_id == flow_id)
        
        return query.order_by(Conversation.timestamp.desc()).limit(limit).all()
    
    def get_recent_context(self, user_id: str = 'default_user', n: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        conversations = self.get_conversation_history(user_id, limit=n)
        
        return [
            {
                'role': conv.role,
                'content': conv.message
            }
            for conv in reversed(conversations)
        ]
    
    def search_conversations(self, query: str, user_id: str = 'default_user', top_k: int = 5) -> List[Dict]:
        """Semantic search in conversations"""
        memories = self.memory_manager.recall(query, top_k)
        
        # Filter for conversations only
        conversations = []
        for mem in memories:
            if mem['source_type'] == 'conversation':
                conv = self.db_session.query(Conversation).filter(
                    Conversation.id == int(mem['source_id']),
                    Conversation.user_id == user_id
                ).first()
                
                if conv:
                    conversations.append({
                        'message': conv.message,
                        'role': conv.role,
                        'timestamp': conv.timestamp.isoformat(),
                        'similarity': mem['similarity']
                    })
        
        return conversations
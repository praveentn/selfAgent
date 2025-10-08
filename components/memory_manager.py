# components/memory_manager.py
from database import MemoryKV, Conversation, VectorMeta
from components.vector_indexer import VectorIndexer
from components.azure_client import AzureOpenAIClient
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages short-term, long-term memory, and agent rules"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.vector_indexer = VectorIndexer(index_path='faiss_index/memory')
        self.azure_client = AzureOpenAIClient()
    
    def classify_memory_type(self, message: str, context: str = "") -> str:
        """Classify memory as short-term, long-term, or rule"""
        
        prompt = f"""Analyze this user message and classify the memory type:

Message: "{message}"
Context: {context}

Classification rules:
- SHORT_TERM: Casual conversation, temporary context, current session info (e.g., "my name is John", "I'm working on project X today")
- LONG_TERM: Important facts to remember permanently (e.g., "always use this email format", "our company policy is...", "remember that I prefer...")
- RULE: Instructions that change agent behavior/system prompt (e.g., "always be formal", "don't use emojis", "respond in bullet points", "you are a financial expert")

Respond with ONLY one word: SHORT_TERM, LONG_TERM, or RULE"""
        
        try:
            response = self.azure_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            memory_type = response.strip().upper()
            if memory_type not in ['SHORT_TERM', 'LONG_TERM', 'RULE']:
                memory_type = 'SHORT_TERM'
            
            logger.info(f"Classified memory as: {memory_type}")
            return memory_type
        
        except Exception as e:
            logger.error(f"Memory classification error: {e}")
            return 'SHORT_TERM'
    
    def store_memory(self, key: str, value: str, memory_type: str = 'SHORT_TERM', 
                    user_id: str = 'default_user'):
        """Store memory with type classification"""
        
        # Create composite key with type
        typed_key = f"{memory_type}:{user_id}:{key}"
        
        existing = self.db_session.query(MemoryKV).filter(
            MemoryKV.key == typed_key
        ).first()
        
        if existing:
            existing.value = value
            existing.last_used_at = datetime.utcnow()
        else:
            memory = MemoryKV(key=typed_key, value=value)
            self.db_session.add(memory)
        
        self.db_session.commit()
        
        # Index long-term memories and rules for retrieval
        if memory_type in ['LONG_TERM', 'RULE']:
            self.index_memory(
                text=f"{key}: {value}",
                source_type=f'memory_{memory_type.lower()}',
                source_id=typed_key
            )
        
        logger.info(f"Stored {memory_type} memory: {key}")
    
    def get_all_rules(self, user_id: str = 'default_user') -> List[Dict]:
        """Get all rules for system prompt construction"""
        
        rules = self.db_session.query(MemoryKV).filter(
            MemoryKV.key.like(f'RULE:{user_id}:%')
        ).all()
        
        return [
            {
                'key': rule.key.split(':', 2)[2],
                'value': rule.value,
                'created': rule.created_at.isoformat()
            }
            for rule in rules
        ]
    
    def get_system_prompt_with_rules(self, base_prompt: str, 
                                    user_id: str = 'default_user') -> str:
        """Construct system prompt with user-defined rules"""
        
        rules = self.get_all_rules(user_id)
        
        if not rules:
            return base_prompt
        
        rules_text = "\n".join([f"- {rule['value']}" for rule in rules])
        
        enhanced_prompt = f"""{base_prompt}

USER-DEFINED BEHAVIOR RULES:
{rules_text}

Follow these rules in all interactions with this user."""
        
        return enhanced_prompt
    
    def store_kv(self, key: str, value: str):
        """Legacy method - defaults to SHORT_TERM"""
        self.store_memory(key, value, 'SHORT_TERM')
    
    def get_kv(self, key: str, user_id: str = 'default_user') -> Optional[str]:
        """Retrieve key-value from memory (checks all types)"""
        
        # Try each memory type
        for mem_type in ['SHORT_TERM', 'LONG_TERM', 'RULE']:
            typed_key = f"{mem_type}:{user_id}:{key}"
            memory = self.db_session.query(MemoryKV).filter(
                MemoryKV.key == typed_key
            ).first()
            
            if memory:
                memory.last_used_at = datetime.utcnow()
                self.db_session.commit()
                return memory.value
        
        return None
    
    def index_memory(self, text: str, source_type: str, source_id: str):
        """Index text for semantic search"""
        meta = VectorMeta(
            source_type=source_type,
            source_id=source_id,
            text=text
        )
        self.db_session.add(meta)
        self.db_session.commit()
        self.db_session.refresh(meta)
        
        self.vector_indexer.add_texts([text], [meta.id])
        logger.info(f"Indexed memory: {source_type}:{source_id}")
    
    def recall(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search in memory"""
        results = self.vector_indexer.search(query, top_k)
        
        memories = []
        for meta_id, similarity in results:
            meta = self.db_session.query(VectorMeta).filter(
                VectorMeta.id == meta_id
            ).first()
            if meta:
                memories.append({
                    'text': meta.text,
                    'source_type': meta.source_type,
                    'source_id': meta.source_id,
                    'similarity': round(similarity, 3),
                    'created_at': meta.created_at.isoformat()
                })
        
        return memories
    
    def get_context_for_user(self, user_id: str = 'default_user') -> str:
        """Get relevant context from long-term memory and rules"""
        
        long_term = self.db_session.query(MemoryKV).filter(
            MemoryKV.key.like(f'LONG_TERM:{user_id}:%')
        ).all()
        
        rules = self.get_all_rules(user_id)
        
        context_parts = []
        
        if long_term:
            facts = [mem.value for mem in long_term]
            context_parts.append(f"Known facts: {'; '.join(facts)}")
        
        if rules:
            rule_text = [rule['value'] for rule in rules]
            context_parts.append(f"Behavior rules: {'; '.join(rule_text)}")
        
        return " | ".join(context_parts) if context_parts else ""


class ConversationManager:
    """Manages conversation history with enhanced features"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.memory_manager = MemoryManager(db_session)
    
    def add_message(
        self, 
        message: str, 
        role: str, 
        user_id: str = 'default_user',
        flow_id: Optional[int] = None,
        message_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Conversation:
        """Add message to conversation history"""
        
        conversation = Conversation(
            user_id=user_id,
            flow_id=flow_id,
            message=message,
            role=role,
            message_id=message_id or session_id
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
        flow_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[Conversation]:
        """Get conversation history"""
        
        query = self.db_session.query(Conversation).filter(
            Conversation.user_id == user_id
        )
        
        if flow_id is not None:
            query = query.filter(Conversation.flow_id == flow_id)
        
        if session_id is not None:
            query = query.filter(Conversation.message_id == session_id)
        
        return query.order_by(Conversation.timestamp.desc()).limit(limit).all()
    
    def get_recent_context(self, user_id: str = 'default_user', 
                          n: int = 10, session_id: Optional[str] = None) -> List[Dict]:
        """Get recent conversation context"""
        
        conversations = self.get_conversation_history(
            user_id, limit=n, session_id=session_id
        )
        
        return [
            {
                'role': conv.role,
                'content': conv.message
            }
            for conv in reversed(conversations)
        ]
    
    def get_all_sessions(self, user_id: str = 'default_user') -> List[Dict]:
        """Get all conversation sessions"""
        
        from sqlalchemy import func, distinct
        
        sessions = self.db_session.query(
            Conversation.message_id,
            func.min(Conversation.timestamp).label('started'),
            func.max(Conversation.timestamp).label('last_updated'),
            func.count(Conversation.id).label('message_count')
        ).filter(
            Conversation.user_id == user_id,
            Conversation.message_id.isnot(None)
        ).group_by(
            Conversation.message_id
        ).order_by(
            func.max(Conversation.timestamp).desc()
        ).all()
        
        return [
            {
                'session_id': session.message_id,
                'started': session.started.isoformat() if session.started else None,
                'last_updated': session.last_updated.isoformat() if session.last_updated else None,
                'message_count': session.message_count
            }
            for session in sessions
        ]
    
    def clear_session(self, session_id: str, user_id: str = 'default_user'):
        """Clear a specific conversation session"""
        
        self.db_session.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.message_id == session_id
        ).delete()
        
        self.db_session.commit()
        logger.info(f"Cleared session: {session_id}")
    
    def search_conversations(self, query: str, user_id: str = 'default_user', 
                           top_k: int = 5) -> List[Dict]:
        """Semantic search in conversations"""
        
        memories = self.memory_manager.recall(query, top_k)
        
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
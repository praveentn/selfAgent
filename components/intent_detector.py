# components/intent_detector.py
from components.vector_indexer import VectorIndexer
from components.azure_client import AzureOpenAIClient
from components.agent_awareness import AgentAwareness
from database import IntentSample
from sqlalchemy.orm import Session
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

class IntentDetector:
    """Detects user intent using embedding-based matching with LLM fallback"""
    
    def __init__(self, db_session: Session, confidence_threshold: float = 0.78):
        self.db_session = db_session
        self.confidence_threshold = confidence_threshold
        self.vector_indexer = VectorIndexer(index_path='faiss_index/intents')
        self.azure_client = AzureOpenAIClient()
        self.agent_awareness = AgentAwareness(db_session)
        
        # Initialize intent index
        self._initialize_intent_index()
    
    def _initialize_intent_index(self):
        """Initialize FAISS index with intent samples"""
        intent_samples = self.db_session.query(IntentSample).all()
        
        if not intent_samples:
            logger.warning("No intent samples found in database")
            # Add default samples for new intents
            self._seed_new_intents()
            intent_samples = self.db_session.query(IntentSample).all()
        
        # Clear and rebuild index
        self.vector_indexer.clear_index()
        
        texts = [sample.sample_text for sample in intent_samples]
        ids = [sample.id for sample in intent_samples]
        
        self.vector_indexer.add_texts(texts, ids)
        logger.info(f"Initialized intent index with {len(texts)} samples")
    
    def _seed_new_intents(self):
        """Seed new intent samples for file operations"""
        new_samples = [
            IntentSample(intent='read_file', sample_text='read file from local'),
            IntentSample(intent='read_file', sample_text='show me contents of file'),
            IntentSample(intent='read_file', sample_text='read file1.txt'),
            IntentSample(intent='execute_code', sample_text='run python code'),
            IntentSample(intent='execute_code', sample_text='execute script'),
            IntentSample(intent='ask_capabilities', sample_text='what can you do'),
            IntentSample(intent='ask_capabilities', sample_text='show capabilities'),
        ]
        
        for sample in new_samples:
            self.db_session.add(sample)
        
        self.db_session.commit()
        logger.info("Seeded new intent samples")
    
    def detect_intent(self, user_message: str, conversation_history: list = None) -> Tuple[str, float, Dict]:
        """
        Detect user intent using embedding-based search with LLM fallback
        
        Returns: (intent_name, confidence, parameters)
        """
        # Get system context
        system_context = self.agent_awareness.get_system_context()
        
        # Step 1: Embedding-based matching
        search_results = self.vector_indexer.search(user_message, top_k=3)
        
        if search_results:
            top_match_id, similarity = search_results[0]
            
            # Get the intent from database
            intent_sample = self.db_session.query(IntentSample).filter(
                IntentSample.id == top_match_id
            ).first()
            
            if intent_sample and similarity >= self.confidence_threshold:
                logger.info(
                    f"Intent detected via embeddings: {intent_sample.intent} "
                    f"(confidence: {similarity:.2f})"
                )
                return intent_sample.intent, similarity, {}
        
        # Step 2: LLM fallback for complex/ambiguous cases
        logger.info("Using LLM fallback for intent detection")
        llm_result = self.azure_client.parse_intent(
            user_message, 
            conversation_history,
            system_context
        )
        
        intent = llm_result.get('intent', 'unknown')
        confidence = llm_result.get('confidence', 0.5)
        parameters = llm_result.get('parameters', {})
        
        logger.info(f"LLM detected intent: {intent} (confidence: {confidence:.2f})")
        
        return intent, confidence, parameters
    
    def add_intent_sample(self, intent: str, sample_text: str):
        """Add new intent sample and update index"""
        new_sample = IntentSample(intent=intent, sample_text=sample_text)
        self.db_session.add(new_sample)
        self.db_session.commit()
        
        # Update index
        self.vector_indexer.add_texts([sample_text], [new_sample.id])
        logger.info(f"Added new intent sample: {intent}")
    
    def get_intent_confidence(self, user_message: str, expected_intent: str) -> float:
        """Get confidence score for a specific intent"""
        search_results = self.vector_indexer.search(user_message, top_k=5)
        
        for match_id, similarity in search_results:
            intent_sample = self.db_session.query(IntentSample).filter(
                IntentSample.id == match_id
            ).first()
            
            if intent_sample and intent_sample.intent == expected_intent:
                return similarity
        
        return 0.0
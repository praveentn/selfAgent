# components/intent_detector.py
from components.vector_indexer import VectorIndexer
from components.azure_client import AzureOpenAIClient
from components.agent_awareness import AgentAwareness
from database import IntentSample
from sqlalchemy.orm import Session
import logging
from typing import Tuple, Dict
import re

logger = logging.getLogger(__name__)

class IntentDetector:
    """Detects user intent using embedding-based matching with LLM fallback and parameter extraction"""
    
    def __init__(self, db_session: Session, confidence_threshold: float = 0.78):
        self.db_session = db_session
        self.confidence_threshold = confidence_threshold
        self.vector_indexer = VectorIndexer(index_path='faiss_index/intents')
        self.azure_client = AzureOpenAIClient()
        self.agent_awareness = AgentAwareness(db_session)
        
        self._initialize_intent_index()
    
    def _initialize_intent_index(self):
        """Initialize FAISS index with intent samples"""
        intent_samples = self.db_session.query(IntentSample).all()
        
        if not intent_samples:
            logger.warning("No intent samples found in database")
            self._seed_new_intents()
            intent_samples = self.db_session.query(IntentSample).all()
        
        self.vector_indexer.clear_index()
        
        texts = [sample.sample_text for sample in intent_samples]
        ids = [sample.id for sample in intent_samples]
        
        self.vector_indexer.add_texts(texts, ids)
        logger.info(f"Initialized intent index with {len(texts)} samples")
    
    def _seed_new_intents(self):
        """Seed intent samples with clear distinction between flow operations and conversation rules"""
        new_samples = [
            # File operations
            IntentSample(intent='read_file', sample_text='read file from local'),
            IntentSample(intent='read_file', sample_text='show me contents of file'),
            IntentSample(intent='read_file', sample_text='read file1.txt'),
            
            # Code execution
            IntentSample(intent='execute_code', sample_text='run python code'),
            IntentSample(intent='execute_code', sample_text='execute script'),
            
            # Capabilities
            IntentSample(intent='ask_capabilities', sample_text='what can you do'),
            IntentSample(intent='ask_capabilities', sample_text='show capabilities'),
            
            # CONVERSATION RULES (not flow modifications)
            IntentSample(intent='set_rule', sample_text='always ask a follow up question'),
            IntentSample(intent='set_rule', sample_text='respond in a formal tone'),
            IntentSample(intent='set_rule', sample_text='never use emojis'),
            IntentSample(intent='set_rule', sample_text='be concise in responses'),
            IntentSample(intent='set_rule', sample_text='act as a financial expert'),
            IntentSample(intent='set_rule', sample_text='respond in bullet points'),
            IntentSample(intent='set_rule', sample_text='include examples in explanations'),
            
            # Memory storage (facts to remember)
            IntentSample(intent='store_memory', sample_text='remember my email is'),
            IntentSample(intent='store_memory', sample_text='save this information'),
            IntentSample(intent='store_memory', sample_text='keep this in mind'),
            
            # Memory recall
            IntentSample(intent='recall_memory', sample_text='what do you remember'),
            IntentSample(intent='recall_memory', sample_text='do you know anything about'),
            
            # FLOW OPERATIONS (actual workflow modifications)
            IntentSample(intent='modify_flow', sample_text='add a step to the invoice workflow'),
            IntentSample(intent='modify_flow', sample_text='change the email connector in the process'),
            IntentSample(intent='modify_flow', sample_text='update step 2 in the flow'),
            IntentSample(intent='modify_flow', sample_text='insert a notification after validation'),
            
            # Flow management
            IntentSample(intent='delete_flow', sample_text='remove the workflow'),
            IntentSample(intent='delete_flow', sample_text='delete the invoice flow'),
            IntentSample(intent='create_flow', sample_text='create a new workflow'),
            IntentSample(intent='run_flow', sample_text='execute the invoice process'),
            IntentSample(intent='list_flows', sample_text='show all workflows'),
        ]
        
        for sample in new_samples:
            self.db_session.add(sample)
        
        self.db_session.commit()
        logger.info("Seeded intent samples with clear distinctions")
    
    def detect_intent(self, user_message: str, conversation_history: list = None) -> Tuple[str, float, Dict]:
        """
        Detect user intent using LLM-first approach with better classification
        
        Returns: (intent_name, confidence, parameters)
        """
        
        # Get system context
        system_context = self.agent_awareness.get_system_context()
        
        # Use LLM for intent detection with clear instructions
        logger.info("Using LLM for intent detection with enhanced classification")
        llm_result = self.azure_client.parse_intent_enhanced(
            user_message, 
            conversation_history,
            system_context
        )
        
        intent = llm_result.get('intent', 'unknown')
        confidence = llm_result.get('confidence', 0.5)
        parameters = llm_result.get('parameters', {})
        
        # Extract additional parameters if not provided by LLM
        if not parameters or len(parameters) == 0:
            parameters = self.extract_parameters(user_message, intent)
        else:
            # Merge with extracted parameters
            extracted = self.extract_parameters(user_message, intent)
            parameters = {**extracted, **parameters}
        
        logger.info(f"Detected intent: {intent} (confidence: {confidence:.2f}, params: {parameters})")
        
        return intent, confidence, parameters
    
    def extract_parameters(self, user_message: str, intent: str) -> Dict:
        """Extract parameters from user message based on intent"""
        
        params = {}
        
        # Extract filename for file operations
        if intent == 'read_file':
            params = self._extract_file_params(user_message)
        
        # Extract flow identifier
        elif intent in ['run_flow', 'modify_flow', 'delete_flow']:
            params = self._extract_flow_params(user_message)
        
        # Extract memory content
        elif intent == 'store_memory':
            params = self._extract_memory_params(user_message)
        
        # Extract rule content
        elif intent == 'set_rule':
            params = self._extract_rule_params(user_message)
        
        # Use LLM for complex parameter extraction
        else:
            params = self._llm_extract_parameters(user_message, intent)
        
        logger.info(f"Extracted parameters: {params}")
        return params
    
    def _extract_file_params(self, message: str) -> Dict:
        """Extract file-related parameters"""
        params = {'filename': 'file1.txt'}  # Default
        
        # Pattern matching for filenames
        file_patterns = [
            r'(?:file|read|show|display)\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)',
            r'([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)',
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                params['filename'] = match.group(1)
                break
        
        return params
    
    def _extract_flow_params(self, message: str) -> Dict:
        """Extract flow-related parameters"""
        params = {}
        
        # Extract flow ID
        id_match = re.search(r'flow\s+(?:id\s+)?(\d+)', message, re.IGNORECASE)
        if id_match:
            params['flow_id'] = int(id_match.group(1))
        
        # Extract flow name
        name_patterns = [
            r'(?:flow|workflow|process)\s+["\']([^"\']+)["\']',
            r'(?:the\s+)?([a-zA-Z0-9\s_\-]+)\s+(?:flow|workflow|process)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                params['flow_name'] = match.group(1).strip()
                break
        
        return params
    
    def _extract_memory_params(self, message: str) -> Dict:
        """Extract memory storage parameters"""
        params = {'content': message}
        
        # Try to extract key-value pairs
        kv_match = re.search(r'(?:remember|save|store)\s+(?:that\s+)?(.+)', message, re.IGNORECASE)
        if kv_match:
            params['content'] = kv_match.group(1).strip()
        
        return params
    
    def _extract_rule_params(self, message: str) -> Dict:
        """Extract rule/behavior change parameters"""
        params = {'rule': message}
        
        # Extract the actual rule instruction
        rule_patterns = [
            r'(?:always|never)\s+(.+)',
            r'(?:respond|reply|answer)\s+(.+)',
            r'(?:be|act|sound)\s+(.+)',
        ]
        
        for pattern in rule_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                params['rule'] = match.group(0).strip()  # Get the full rule
                break
        
        return params
    
    def _llm_extract_parameters(self, message: str, intent: str) -> Dict:
        """Use LLM to extract parameters for complex cases"""
        
        prompt = f"""Extract parameters from this user message for the intent: {intent}

Message: "{message}"

Extract relevant parameters as a JSON object. For example:
- For file operations: {{"filename": "data.txt", "action": "read"}}
- For flow operations: {{"flow_name": "Invoice Flow", "modification": "add email step"}}

Return ONLY a valid JSON object with extracted parameters."""
        
        try:
            import json
            response = self.azure_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
        
        except Exception as e:
            logger.error(f"Parameter extraction error: {e}")
            return {}
    
    def add_intent_sample(self, intent: str, sample_text: str):
        """Add new intent sample and update index"""
        new_sample = IntentSample(intent=intent, sample_text=sample_text)
        self.db_session.add(new_sample)
        self.db_session.commit()
        
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
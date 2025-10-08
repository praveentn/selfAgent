# components/azure_client.py
from openai import AzureOpenAI
from config import Config
import logging
import json

logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Azure OpenAI client wrapper"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=Config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT.split('/openai/')[0],
            api_key=Config.AZURE_OPENAI_API_KEY,
        )
        self.deployment = Config.AZURE_OPENAI_DEPLOYMENT
    
    def chat_completion(
        self,
        messages: list, 
        temperature: float = 0.7,
        max_tokens: int = 800,
        response_format: dict = None
    ) -> str:
        """Generate chat completion"""
        try:
            kwargs = {
                "model": self.deployment,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
            }
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Azure OpenAI error: {e}")
            raise
    
    def parse_intent_enhanced(self, user_message: str, conversation_history: list = None, system_context: str = None) -> dict:
        """Enhanced intent parsing with clear distinction between flow operations and conversation rules"""
        
        system_prompt = """You are an intent classifier for a workflow automation system with conversational AI capabilities.

CRITICAL DISTINCTIONS:

1. **SET_RULE Intent** (Conversation Behavior):
   - User wants to CHANGE HOW THE AI RESPONDS in conversations
   - Examples: "always ask a follow up question", "be more formal", "respond in bullet points"
   - Keywords: "always", "never", "respond", "be", "act as", "sound like", "tone"
   - These affect the AI's conversation style, NOT workflow steps

2. **MODIFY_FLOW Intent** (Workflow Changes):
   - User wants to CHANGE AN EXISTING WORKFLOW/PROCESS
   - Examples: "add a step to the invoice flow", "update step 2", "change the connector"
   - Keywords: "flow", "workflow", "process", "step", "add step", "modify step"
   - Must reference a specific workflow or process

3. **CREATE_FLOW Intent** (New Workflow):
   - User wants to CREATE A NEW WORKFLOW
   - Examples: "create a flow to process invoices", "make a workflow for"
   - Clear request to build something new

Available intents:
- set_rule: Change AI conversation behavior (HOW it responds)
- store_memory: Store a fact to remember (WHAT to remember)
- recall_memory: Retrieve stored information
- create_flow: Create a new workflow
- run_flow: Execute an existing workflow
- modify_flow: Modify an existing workflow structure
- delete_flow: Delete a workflow
- list_flows: List available workflows
- read_file: Read a file
- execute_code: Execute Python code
- ask_capabilities: Ask about system capabilities
- general_query: General questions/conversation

Respond ONLY with valid JSON:
{
    "intent": "intent_name",
    "confidence": 0.95,
    "parameters": {
        "rule": "the behavior rule",
        "flow_name": "flow name if applicable"
    },
    "reasoning": "brief explanation of classification"
}"""
        
        if system_context:
            system_prompt += f"\n\nSYSTEM CONTEXT:\n{system_context}"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history[-3:])  # Last 3 messages for context
        
        messages.append({
            "role": "user", 
            "content": f"Classify this message:\n\n\"{user_message}\"\n\nRemember: If it's about HOW to respond (tone, style, format), it's SET_RULE. If it's about WHAT workflow to change, it's MODIFY_FLOW."
        })
        
        try:
            response = self.chat_completion(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            logger.info(f"Intent classification: {result.get('intent')} - {result.get('reasoning', '')}")
            return result
        
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            return {
                "intent": "general_query",
                "confidence": 0.3,
                "parameters": {},
                "reasoning": "Error in classification"
            }
    
    def generate_response(self, user_message: str, context: str = "", conversation_history: list = None, system_context: str = None) -> str:
        """Generate conversational response with system awareness"""
        system_prompt = f"""You are Self Agent, an intelligent workflow automation assistant.
You help users create, modify, and execute business process flows.

Context: {context}

Be helpful, concise, and professional. Explain what you're doing and ask for clarification when needed."""
        
        # Add system awareness
        if system_context:
            system_prompt += f"\n\n{system_context}"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history[-10:])
        
        messages.append({"role": "user", "content": user_message})
        
        return self.chat_completion(messages=messages, temperature=0.7, max_tokens=500)
    

    def generate_flow_from_description(self, description: str, system_context: str = None) -> dict:
        """Generate flow definition from natural language description"""
        system_prompt = f"""You are a workflow designer. Generate a complete workflow definition from the user's description.

IMPORTANT: Use EXACT action names from the connectors below:
- local_file connector: use 'read_file', 'write_file', 'list_files', 'file_exists'
- sql connector: use 'query', 'insert', 'update', 'delete'
- sharepoint connector: use 'read_file', 'write_file', 'list_files'
- email connector: use 'send', 'read', 'list'
- notification connector: use 'send_notification', 'send_alert'
- python_executor connector: use 'execute_code', 'execute_script', 'create_script'

{system_context if system_context else ''}

For file operations:
- Use connector: "local_file"
- Use action: "read_file" (NOT "read")
- For filepath parameter, use format: "file1.txt" (NOT "data/file1.txt" - the data/ is automatic)

Return a JSON object with this structure:
{{
    "name": "Flow Name",
    "description": "What this flow does",
    "steps": [
        {{
            "id": "step_1",
            "name": "Step Name",
            "type": "connector_type",
            "connector": "connector_name",
            "action": "exact_action_name",
            "params": {{"filename": "file1.txt"}}
        }}
    ]
}}

CRITICAL: Use exact action names listed above. DO NOT invent new action names."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a flow: {description}"}
        ]
        
        try:
            response = self.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            # Post-process to fix common mistakes
            if 'steps' in result:
                for step in result['steps']:
                    if step.get('connector') == 'local_file':
                        if step.get('action') in ['read', 'read_file']:
                            step['action'] = 'read_file'
                            if 'params' in step and 'filepath' in step['params']:
                                filepath = step['params']['filepath']
                                step['params']['filename'] = filepath.replace('data/', '').replace('data\\', '')
                                if 'filepath' in step['params']:
                                    del step['params']['filepath']
            
            return result
        except Exception as e:
            logger.error(f"Flow generation error: {e}")
            return {}
    
    def extract_flow_modification(self, user_message: str, current_flow: dict) -> dict:
        """Extract flow modification details"""
        system_prompt = f"""You are analyzing a request to modify a workflow.
Current flow structure: {json.dumps(current_flow, indent=2)}

Extract the modification details and respond with JSON:
{{
    "action": "insert_step|update_step|delete_step",
    "anchor_step_id": "step_id_reference",
    "position": "before|after",
    "new_step": {{
        "id": "new_step_id",
        "name": "Step Name",
        "type": "connector_type",
        "action": "action_name",
        "params": {{}}
    }}
}}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            response = self.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Flow modification extraction error: {e}")
            return {}
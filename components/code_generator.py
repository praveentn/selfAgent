# components/code_generator.py
"""
Code Generator Service - Generate Python tools dynamically
"""
import logging
from components.azure_client import AzureOpenAIClient

logger = logging.getLogger(__name__)

class CodeGenerator:
    """Generate Python code for tools/connectors"""
    
    def __init__(self):
        self.azure_client = AzureOpenAIClient()
    
    def generate_file_reader_tool(self, filename: str, file_path: str = None) -> str:
        """Generate Python code to read a file"""
        
        if not file_path:
            file_path = f"data/{filename}"
        
        code_template = f'''# Generated file reader tool
import sys
from pathlib import Path

def read_file(filepath):
    """Read and return file content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: File not found - {{filepath}}"
    except Exception as e:
        return f"Error reading file: {{str(e)}}"

if __name__ == "__main__":
    # File path
    file_path = Path.cwd().parent / "{file_path}"
    
    # Read file
    content = read_file(file_path)
    
    # Print content
    print("=== File Content ===")
    print(content)
    print("=== End of File ===")
'''
        
        return code_template
    
    def generate_custom_tool(self, description: str, requirements: dict) -> str:
        """Generate custom tool using LLM"""
        
        system_prompt = """You are a Python code generator. Generate clean, working Python code based on requirements.
The code should:
- Be production-ready
- Include error handling
- Have clear comments
- Work standalone
- Print results to stdout

Return ONLY the Python code, no explanations."""
        
        user_prompt = f"""Generate Python code for the following:

Description: {description}

Requirements:
{requirements}

The code should be complete and executable."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            code = self.azure_client.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=1000
            )
            
            # Clean code (remove markdown if present)
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            
            return code
        
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return f"# Error generating code: {str(e)}"
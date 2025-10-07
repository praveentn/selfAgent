# components/connectors/python_executor_connector.py
"""
Python Executor Connector - Execute Python code dynamically
"""
import os
import subprocess
import sys
from pathlib import Path
import json
import logging
from typing import Dict, List
import tempfile

logger = logging.getLogger(__name__)

class PythonExecutorConnector:
    """Connector for executing Python code"""
    
    def __init__(self, venv_path: str = None, code_dir: str = None):
        self.code_dir = Path(code_dir) if code_dir else Path.cwd() / "code"
        self.code_dir.mkdir(exist_ok=True)
        
        # Default venv path
        self.venv_path = Path(venv_path) if venv_path else Path.cwd() / "expts"
        
        # Python executable in venv
        if sys.platform == "win32":
            self.python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            self.python_exe = self.venv_path / "bin" / "python"
    
    def capabilities(self) -> List[str]:
        return [
            'execute_code',
            'execute_script',
            'create_script',
            'list_scripts'
        ]
    
    def run(self, action: str, params: dict) -> dict:
        """Execute Python action"""
        try:
            if action == 'execute_code':
                return self._execute_code(params)
            elif action == 'execute_script':
                return self._execute_script(params)
            elif action == 'create_script':
                return self._create_script(params)
            elif action == 'list_scripts':
                return self._list_scripts(params)
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}'
                }
        except Exception as e:
            logger.error(f"PythonExecutorConnector error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _execute_code(self, params: dict) -> dict:
        """Execute Python code string"""
        code = params.get('code')
        
        if not code:
            return {'status': 'error', 'message': 'code is required'}
        
        # Create temporary script
        script_name = f"temp_script_{os.getpid()}.py"
        script_path = self.code_dir / script_name
        
        try:
            # Write code to file
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute
            result = self._run_script(script_path)
            
            # Cleanup
            script_path.unlink(missing_ok=True)
            
            return result
        
        except Exception as e:
            script_path.unlink(missing_ok=True)
            return {
                'status': 'error',
                'message': f'Error executing code: {str(e)}'
            }
    
    def _execute_script(self, params: dict) -> dict:
        """Execute existing Python script"""
        script_name = params.get('script_name')
        
        if not script_name:
            return {'status': 'error', 'message': 'script_name is required'}
        
        script_path = self.code_dir / script_name
        
        if not script_path.exists():
            return {
                'status': 'error',
                'message': f'Script not found: {script_name}'
            }
        
        return self._run_script(script_path)
    
    def _run_script(self, script_path: Path) -> dict:
        """Run Python script using venv"""
        try:
            # Check if venv python exists
            if not self.python_exe.exists():
                # Fallback to system python
                python_cmd = sys.executable
                logger.warning(f"Venv python not found, using system python: {python_cmd}")
            else:
                python_cmd = str(self.python_exe)
            
            # Execute script
            result = subprocess.run(
                [python_cmd, str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.code_dir)
            )
            
            return {
                'status': 'success' if result.returncode == 0 else 'error',
                'action': 'execute_script',
                'script': script_path.name,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'python_exe': python_cmd
            }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'message': 'Script execution timed out (30s limit)'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error running script: {str(e)}'
            }
    
    def _create_script(self, params: dict) -> dict:
        """Create Python script file"""
        script_name = params.get('script_name')
        code = params.get('code')
        
        if not script_name or not code:
            return {
                'status': 'error',
                'message': 'script_name and code are required'
            }
        
        script_path = self.code_dir / script_name
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            return {
                'status': 'success',
                'action': 'create_script',
                'script_name': script_name,
                'path': str(script_path),
                'size': len(code)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error creating script: {str(e)}'
            }
    
    def _list_scripts(self, params: dict) -> dict:
        """List Python scripts in code directory"""
        try:
            scripts = []
            for script_path in self.code_dir.glob("*.py"):
                scripts.append({
                    'name': script_path.name,
                    'size': script_path.stat().st_size,
                    'modified': script_path.stat().st_mtime
                })
            
            return {
                'status': 'success',
                'action': 'list_scripts',
                'scripts': scripts,
                'count': len(scripts),
                'path': str(self.code_dir)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error listing scripts: {str(e)}'
            }
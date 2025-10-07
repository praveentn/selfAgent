# components/connectors/local_file_connector.py
"""
Local File Connector - Read/Write files from local filesystem
"""
import os
from pathlib import Path
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class LocalFileConnector:
    """Connector for local file system operations"""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path.cwd() / "data"
        self.base_path.mkdir(exist_ok=True)
    
    def capabilities(self) -> List[str]:
        return [
            'read_file',
            'read',  # Alias for read_file
            'write_file',
            'write',  # Alias for write_file
            'list_files',
            'file_exists',
            'delete_file',
            'get_file_info'
        ]
    
    def run(self, action: str, params: dict) -> dict:
        """Execute file operation"""
        try:
            # Normalize action names (handle aliases)
            action_map = {
                'read': 'read_file',
                'write': 'write_file',
                'list': 'list_files',
                'exists': 'file_exists',
                'delete': 'delete_file',
                'info': 'get_file_info'
            }
            
            # Map alias to actual action
            normalized_action = action_map.get(action, action)
            
            if normalized_action == 'read_file':
                return self._read_file(params)
            elif normalized_action == 'write_file':
                return self._write_file(params)
            elif normalized_action == 'list_files':
                return self._list_files(params)
            elif normalized_action == 'file_exists':
                return self._file_exists(params)
            elif normalized_action == 'delete_file':
                return self._delete_file(params)
            elif normalized_action == 'get_file_info':
                return self._get_file_info(params)
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}',
                    'supported_actions': self.capabilities()
                }
        except Exception as e:
            logger.error(f"LocalFileConnector error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _read_file(self, params: dict) -> dict:
        """Read file content"""
        # Support both 'filename' and 'filepath' parameters
        filename = params.get('filename') or params.get('filepath')
        encoding = params.get('encoding', 'utf-8')
        
        if not filename:
            return {'status': 'error', 'message': 'filename or filepath is required'}
        
        # Handle absolute and relative paths
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            # Remove leading 'data/' if present (since base_path is already data/)
            filename_clean = filename.replace('data/', '').replace('data\\', '')
            filepath = self.base_path / filename_clean
        
        if not filepath.exists():
            return {
                'status': 'error',
                'message': f'File not found: {filename} (looked in: {filepath})',
                'searched_path': str(filepath)
            }
        
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                'status': 'success',
                'action': 'read_file',
                'filename': filename,
                'content': content,
                'size': len(content),
                'size_bytes': filepath.stat().st_size,
                'path': str(filepath),
                'lines': len(content.split('\n'))
            }
        except UnicodeDecodeError:
            # Try reading as binary if UTF-8 fails
            try:
                with open(filepath, 'rb') as f:
                    content_bytes = f.read()
                return {
                    'status': 'success',
                    'action': 'read_file',
                    'filename': filename,
                    'content': f'[Binary file, {len(content_bytes)} bytes]',
                    'content_preview': str(content_bytes[:100]),
                    'size_bytes': len(content_bytes),
                    'path': str(filepath),
                    'is_binary': True
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Error reading file: {str(e)}'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error reading file: {str(e)}'
            }
    
    def _write_file(self, params: dict) -> dict:
        """Write content to file"""
        filename = params.get('filename') or params.get('filepath')
        content = params.get('content', '')
        encoding = params.get('encoding', 'utf-8')
        mode = params.get('mode', 'w')  # 'w' or 'a'
        
        if not filename:
            return {'status': 'error', 'message': 'filename or filepath is required'}
        
        # Handle path
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filename_clean = filename.replace('data/', '').replace('data\\', '')
            filepath = self.base_path / filename_clean
        
        try:
            # Create parent directories if needed
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)
            
            return {
                'status': 'success',
                'action': 'write_file',
                'filename': filename,
                'bytes_written': len(content),
                'path': str(filepath)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error writing file: {str(e)}'
            }
    
    def _list_files(self, params: dict) -> dict:
        """List files in directory"""
        pattern = params.get('pattern', '*')
        
        try:
            files = []
            for filepath in self.base_path.glob(pattern):
                if filepath.is_file():
                    files.append({
                        'name': filepath.name,
                        'size': filepath.stat().st_size,
                        'modified': filepath.stat().st_mtime
                    })
            
            return {
                'status': 'success',
                'action': 'list_files',
                'files': files,
                'count': len(files),
                'path': str(self.base_path)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error listing files: {str(e)}'
            }
    
    def _file_exists(self, params: dict) -> dict:
        """Check if file exists"""
        filename = params.get('filename') or params.get('filepath')
        
        if not filename:
            return {'status': 'error', 'message': 'filename or filepath is required'}
        
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filename_clean = filename.replace('data/', '').replace('data\\', '')
            filepath = self.base_path / filename_clean
        
        exists = filepath.exists()
        
        return {
            'status': 'success',
            'action': 'file_exists',
            'filename': filename,
            'exists': exists,
            'path': str(filepath)
        }
    
    def _delete_file(self, params: dict) -> dict:
        """Delete file"""
        filename = params.get('filename') or params.get('filepath')
        
        if not filename:
            return {'status': 'error', 'message': 'filename or filepath is required'}
        
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filename_clean = filename.replace('data/', '').replace('data\\', '')
            filepath = self.base_path / filename_clean
        
        if not filepath.exists():
            return {
                'status': 'error',
                'message': f'File not found: {filename}'
            }
        
        try:
            filepath.unlink()
            return {
                'status': 'success',
                'action': 'delete_file',
                'filename': filename,
                'message': f'File deleted: {filename}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting file: {str(e)}'
            }
    
    def _get_file_info(self, params: dict) -> dict:
        """Get file information"""
        filename = params.get('filename') or params.get('filepath')
        
        if not filename:
            return {'status': 'error', 'message': 'filename or filepath is required'}
        
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filename_clean = filename.replace('data/', '').replace('data\\', '')
            filepath = self.base_path / filename_clean
        
        if not filepath.exists():
            return {
                'status': 'error',
                'message': f'File not found: {filename}'
            }
        
        stat = filepath.stat()
        
        return {
            'status': 'success',
            'action': 'get_file_info',
            'filename': filename,
            'size': stat.st_size,
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'path': str(filepath)
        }
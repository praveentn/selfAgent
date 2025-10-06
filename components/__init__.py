# components/__init__.py
"""
Self Agent Components Package
Contains core business logic components
"""

from components.azure_client import AzureOpenAIClient
from components.intent_detector import IntentDetector
from components.flow_manager import FlowManager
from components.executor import Executor
from components.connector_manager import ConnectorManager
from components.memory_manager import MemoryManager, ConversationManager
from components.vector_indexer import VectorIndexer

__all__ = [
    'AzureOpenAIClient',
    'IntentDetector',
    'FlowManager',
    'Executor',
    'ConnectorManager',
    'MemoryManager',
    'ConversationManager',
    'VectorIndexer'
]


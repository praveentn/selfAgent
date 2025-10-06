# config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Configuration management for Fin Planner Pro"""
    
    # Application Settings
    APP_NAME = "Self Agent"
    APP_VERSION = "1.0.0"
    DEFAULT_PORT = 7367
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server Configuration
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", DEFAULT_PORT))
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///selfagent.db")
    DB_PATH = os.getenv("DB_PATH", "selfagent.db")

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1")
    
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_vars = [
            ("AZURE_OPENAI_ENDPOINT", cls.AZURE_OPENAI_ENDPOINT),
            ("AZURE_OPENAI_API_KEY", cls.AZURE_OPENAI_API_KEY),
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def get_database_path(cls):
        """Get absolute database path"""
        return Path(cls.DB_PATH).absolute()
    
    @classmethod
    def ensure_upload_folder(cls):
        """Ensure upload folder exists"""
        Path(cls.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        return Path(cls.UPLOAD_FOLDER).absolute()

# Initialize configuration
config = Config()
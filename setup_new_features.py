# setup_new_features.py
"""
Setup script for new Self Agent features
Run this to initialize the database with new features
"""

import os
from pathlib import Path
from database import init_database, SessionLocal
from database import IntentSample
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories"""
    directories = ['data', 'code', 'flows', 'faiss_index']
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        logger.info(f"✅ Created directory: {dir_name}")

def create_sample_files():
    """Create sample data files"""
    data_dir = Path('data')
    
    # Sample file 1
    file1 = data_dir / 'file1.txt'
    if not file1.exists():
        file1.write_text("""This is the content of file1.txt.
It contains sample data for testing the file reading functionality.
Line 1: Sample data
Line 2: More sample data
Line 3: Even more data""")
        logger.info(f"✅ Created {file1}")
    
    # Sample file 2
    file2 = data_dir / 'file2.txt'
    if not file2.exists():
        file2.write_text("""This is file2.txt with different content.
This file is used to test dynamic parameter extraction.
The agent should be able to read this when asked for file2.txt.""")
        logger.info(f"✅ Created {file2}")
    
    # Sample JSON config
    config_file = data_dir / 'config.json'
    if not config_file.exists():
        config_file.write_text("""{
  "app_name": "Self Agent",
  "version": "1.0.0",
  "features": [
    "Memory Classification",
    "Parameter Extraction",
    "Session Management",
    "Flow Modification"
  ]
}""")
        logger.info(f"✅ Created {config_file}")

def seed_new_intents():
    """Seed new intent samples for enhanced features"""
    _, SessionLocal = init_database()
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing = db.query(IntentSample).filter(
            IntentSample.intent == 'set_rule'
        ).first()
        
        if existing:
            logger.info("⏭️  Intent samples already seeded")
            return
        
        new_intents = [
            # Memory and rules
            IntentSample(intent='store_memory', sample_text='remember this information'),
            IntentSample(intent='store_memory', sample_text='save this for later'),
            IntentSample(intent='store_memory', sample_text='keep this in mind'),
            IntentSample(intent='recall_memory', sample_text='what do you remember about'),
            IntentSample(intent='recall_memory', sample_text='do you know anything about'),
            IntentSample(intent='set_rule', sample_text='always respond in a formal tone'),
            IntentSample(intent='set_rule', sample_text='never use emojis'),
            IntentSample(intent='set_rule', sample_text='be concise in your responses'),
            IntentSample(intent='set_rule', sample_text='you should act as a financial advisor'),
            
            # Flow management
            IntentSample(intent='modify_flow', sample_text='change the workflow'),
            IntentSample(intent='modify_flow', sample_text='update the process'),
            IntentSample(intent='modify_flow', sample_text='edit the flow'),
            IntentSample(intent='delete_flow', sample_text='remove the workflow'),
            IntentSample(intent='delete_flow', sample_text='delete the flow'),
            IntentSample(intent='delete_flow', sample_text='get rid of this process'),
            
            # File operations with parameters
            IntentSample(intent='read_file', sample_text='read the file'),
            IntentSample(intent='read_file', sample_text='show me the contents'),
            IntentSample(intent='read_file', sample_text='open the document'),
            
            # Session management
            IntentSample(intent='new_chat', sample_text='start a new conversation'),
            IntentSample(intent='new_chat', sample_text='begin fresh chat'),
            IntentSample(intent='list_sessions', sample_text='show my chat history'),
            IntentSample(intent='list_sessions', sample_text='view previous conversations'),
        ]
        
        for sample in new_intents:
            db.add(sample)
        
        db.commit()
        logger.info(f"✅ Seeded {len(new_intents)} new intent samples")
    
    finally:
        db.close()

def verify_setup():
    """Verify that everything is set up correctly"""
    logger.info("\n" + "="*50)
    logger.info("🔍 Verifying setup...")
    
    # Check directories
    for dir_name in ['data', 'code', 'flows', 'faiss_index']:
        if Path(dir_name).exists():
            logger.info(f"✅ Directory exists: {dir_name}")
        else:
            logger.warning(f"⚠️  Missing directory: {dir_name}")
    
    # Check database
    if Path('selfagent.db').exists():
        logger.info("✅ Database exists: selfagent.db")
    else:
        logger.warning("⚠️  Database not found")
    
    # Check sample files
    for file_name in ['file1.txt', 'file2.txt', 'config.json']:
        file_path = Path('data') / file_name
        if file_path.exists():
            logger.info(f"✅ Sample file exists: {file_name}")
        else:
            logger.warning(f"⚠️  Missing file: {file_name}")
    
    logger.info("="*50 + "\n")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "🎉 "*20)
    print("\n✅ Setup Complete!\n")
    print("📋 Next Steps:\n")
    print("1. Verify your .env file has Azure OpenAI credentials:")
    print("   - AZURE_OPENAI_ENDPOINT")
    print("   - AZURE_OPENAI_API_KEY")
    print("   - AZURE_OPENAI_DEPLOYMENT")
    print("")
    print("2. Start the API server:")
    print("   python main.py")
    print("")
    print("3. In a new terminal, start Streamlit:")
    print("   streamlit run app.py")
    print("")
    print("4. Open your browser:")
    print("   http://localhost:8501")
    print("")
    print("🧪 Test the new features:")
    print("   • Memory: 'Remember to always be formal'")
    print("   • Parameters: 'Read file2.txt'")
    print("   • Sessions: Click 'New Chat' button")
    print("   • Flows: Click 'Modify' on any flow")
    print("")
    print("📚 See IMPLEMENTATION_GUIDE.md for detailed docs")
    print("\n" + "🎉 "*20 + "\n")

def main():
    """Main setup function"""
    print("\n" + "🚀 "*20)
    print("\n🔧 Self Agent - New Features Setup\n")
    print("="*50 + "\n")
    
    try:
        # Step 1: Create directories
        logger.info("Step 1: Creating directories...")
        setup_directories()
        
        # Step 2: Initialize database
        logger.info("\nStep 2: Initializing database...")
        init_database()
        logger.info("✅ Database initialized")
        
        # Step 3: Create sample files
        logger.info("\nStep 3: Creating sample files...")
        create_sample_files()
        
        # Step 4: Seed intents
        logger.info("\nStep 4: Seeding intent samples...")
        seed_new_intents()
        
        # Step 5: Verify setup
        verify_setup()
        
        # Print next steps
        print_next_steps()
        
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
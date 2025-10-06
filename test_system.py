# test_system.py
"""
Self Agent - System Test Script
Tests all core components and connections
"""

import sys
from datetime import datetime

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def test_imports():
    """Test if all required modules can be imported"""
    print_header("Testing Imports")
    
    modules = [
        'streamlit',
        'fastapi',
        'sqlalchemy',
        'openai',
        'faiss',
        'sentence_transformers',
        'yaml',
        'pandas',
        'httpx'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n⚠️  Failed to import: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All imports successful")
    return True

def test_config():
    """Test configuration"""
    print_header("Testing Configuration")
    
    try:
        from config import Config
        
        print(f"App Name: {Config.APP_NAME}")
        print(f"Version: {Config.APP_VERSION}")
        print(f"Host: {Config.HOST}")
        print(f"Port: {Config.PORT}")
        print(f"Database: {Config.DB_PATH}")
        
        # Test validation
        Config.validate_config()
        print("\n✅ Configuration valid")
        return True
    
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        print("Check your .env file")
        return False

def test_database():
    """Test database connection and initialization"""
    print_header("Testing Database")
    
    try:
        from database import init_database, Flow, Connector
        from sqlalchemy.orm import Session
        
        engine, SessionLocal = init_database()
        print("✅ Database initialized")
        
        # Test session
        db = SessionLocal()
        try:
            flow_count = db.query(Flow).count()
            connector_count = db.query(Connector).count()
            
            print(f"✅ Flows in database: {flow_count}")
            print(f"✅ Connectors in database: {connector_count}")
            
            if connector_count == 0:
                print("⚠️  No connectors found - they will be created on first run")
            
            return True
        finally:
            db.close()
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_azure_openai():
    """Test Azure OpenAI connection"""
    print_header("Testing Azure OpenAI")
    
    try:
        from components.azure_client import AzureOpenAIClient
        
        client = AzureOpenAIClient()
        print("✅ Azure OpenAI client created")
        
        # Test simple completion
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say 'test successful'"}],
            max_tokens=20
        )
        
        print(f"✅ API Response: {response[:50]}...")
        return True
    
    except Exception as e:
        print(f"❌ Azure OpenAI error: {e}")
        print("Check your API credentials in .env")
        return False

def test_vector_indexer():
    """Test FAISS vector indexer"""
    print_header("Testing Vector Indexer")
    
    try:
        from components.vector_indexer import VectorIndexer
        
        indexer = VectorIndexer(index_path='faiss_index/test')
        print("✅ Vector indexer created")
        
        # Test adding texts
        texts = ["Hello world", "Test document"]
        ids = indexer.add_texts(texts, [1, 2])
        print(f"✅ Added {len(ids)} texts to index")
        
        # Test search
        results = indexer.search("hello", top_k=1)
        print(f"✅ Search returned {len(results)} results")
        
        return True
    
    except Exception as e:
        print(f"❌ Vector indexer error: {e}")
        return False

def test_components():
    """Test core components"""
    print_header("Testing Components")
    
    try:
        from database import init_database
        from components.flow_manager import FlowManager
        from components.connector_manager import ConnectorManager
        from components.memory_manager import MemoryManager
        
        engine, SessionLocal = init_database()
        db = SessionLocal()
        
        try:
            # Test Flow Manager
            flow_manager = FlowManager(db)
            flows = flow_manager.list_flows()
            print(f"✅ Flow Manager: {len(flows)} flows")
            
            # Test Connector Manager
            connector_manager = ConnectorManager(db)
            connectors = connector_manager.list_connectors()
            print(f"✅ Connector Manager: {len(connectors)} connectors")
            
            # Test Memory Manager
            memory_manager = MemoryManager(db)
            memory_manager.store_kv("test_key", "test_value")
            value = memory_manager.get_kv("test_key")
            print(f"✅ Memory Manager: Stored and retrieved test value")
            
            return True
        finally:
            db.close()
    
    except Exception as e:
        print(f"❌ Components error: {e}")
        return False

def test_api_server():
    """Test if FastAPI server is running"""
    print_header("Testing API Server")
    
    try:
        import httpx
        from config import Config
        
        url = f"http://{Config.HOST}:{Config.PORT}/"
        
        response = httpx.get(url, timeout=2.0)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Server is running")
            print(f"   App: {data.get('app')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"⚠️  API Server returned status {response.status_code}")
            return False
    
    except httpx.ConnectError:
        print("⚠️  API Server is not running")
        print("Start it with: python main.py")
        return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪" * 30)
    print("  SELF AGENT - SYSTEM TEST")
    print("  " + str(datetime.now()))
    print("🧪" * 30)
    
    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Database": test_database(),
        "Azure OpenAI": test_azure_openai(),
        "Vector Indexer": test_vector_indexer(),
        "Components": test_components(),
        "API Server": test_api_server()
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
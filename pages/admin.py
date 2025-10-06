# pages/admin.py
import streamlit as st
import httpx
import pandas as pd
import json

def render():
    st.title("⚙️ Admin Panel")
    st.markdown("System administration and configuration")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🗄️ SQL Executor", "📊 System Stats", "🔧 Configuration"])
    
    with tab1:
        render_sql_executor()
    
    with tab2:
        render_system_stats()
    
    with tab3:
        render_configuration()

def render_sql_executor():
    """SQL query executor with pagination"""
    st.subheader("SQL Executor")
    st.markdown("Execute raw SQL queries against the database")
    
    # Query input
    query = st.text_area(
        "SQL Query",
        height=150,
        placeholder="Enter your SQL query here...\nExample: SELECT * FROM flows",
        help="Execute any SQL query (SELECT, INSERT, UPDATE, DELETE, etc.)"
    )
    
    # Pagination controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        execute_btn = st.button("▶️ Execute Query", type="primary", use_container_width=True)
    with col2:
        page_size = st.selectbox("Page Size", [10, 25, 50, 100, 500], index=2)
    with col3:
        page = st.number_input("Page", min_value=1, value=1)
    
    # Execute query
    if execute_btn and query.strip():
        try:
            with st.spinner("Executing query..."):
                response = httpx.post(
                    f"{st.session_state.api_url}/admin/sql",
                    json={
                        "query": query.strip(),
                        "page": page,
                        "page_size": page_size
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check if SELECT query
                    if 'rows' in result:
                        st.success(f"✅ Query executed successfully")
                        
                        # Display metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Rows", result.get('total_rows', 0))
                        with col2:
                            st.metric("Current Page", f"{result.get('page', 1)}/{result.get('total_pages', 1)}")
                        with col3:
                            st.metric("Rows Shown", len(result.get('rows', [])))
                        
                        # Display results
                        if result.get('rows'):
                            df = pd.DataFrame(result['rows'])
                            
                            # Format dataframe
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                height=400
                            )
                            
                            # Download button
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name="query_results.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("No rows returned")
                    
                    else:
                        # Non-SELECT query (INSERT, UPDATE, DELETE, etc.)
                        st.success(f"✅ {result.get('message', 'Query executed')}")
                        st.metric("Rows Affected", result.get('rows_affected', 0))
                
                else:
                    st.error("Query execution failed")
        
        except httpx.TimeoutException:
            st.error("❌ Query timeout - query took too long to execute")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    # Quick query templates
    with st.expander("📋 Query Templates"):
        st.markdown("### Common Queries")
        
        templates = {
            "List all flows": "SELECT * FROM flows ORDER BY created_at DESC",
            "List all runs": "SELECT * FROM runs ORDER BY started_at DESC LIMIT 100",
            "Flow execution stats": """SELECT 
    f.name as flow_name,
    COUNT(r.id) as total_runs,
    SUM(CASE WHEN r.status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) as failed
FROM flows f
LEFT JOIN runs r ON f.id = r.flow_id
GROUP BY f.id, f.name""",
            "Recent conversations": "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 50",
            "All connectors": "SELECT * FROM connectors",
            "Memory KV store": "SELECT * FROM memory_kv ORDER BY last_used_at DESC",
            "Vector metadata": "SELECT * FROM vector_meta ORDER BY created_at DESC LIMIT 100",
            "Intent samples": "SELECT intent, COUNT(*) as count FROM intent_samples GROUP BY intent",
        }
        
        for name, sql in templates.items():
            if st.button(name, key=f"template_{name}"):
                st.session_state.sql_template = sql
                st.rerun()
        
        # Apply template if selected
        if 'sql_template' in st.session_state:
            st.code(st.session_state.sql_template, language='sql')
            if st.button("Use This Query"):
                query = st.session_state.sql_template
                del st.session_state.sql_template

def render_system_stats():
    """Display system statistics"""
    st.subheader("System Statistics")
    
    from database import Flow, Run, Conversation, Connector, MemoryKV
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from config import Config
    
    engine = create_engine(f'sqlite:///{Config.DB_PATH}')
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get counts
        flow_count = db.query(Flow).count()
        run_count = db.query(Run).count()
        conversation_count = db.query(Conversation).count()
        connector_count = db.query(Connector).count()
        memory_count = db.query(MemoryKV).count()
        
        # Display metrics
        st.markdown("### Database Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Flows", flow_count)
            st.metric("🗄️ Memory Items", memory_count)
        
        with col2:
            st.metric("▶️ Runs", run_count)
            st.metric("🔌 Connectors", connector_count)
        
        with col3:
            st.metric("💬 Conversations", conversation_count)
        
        st.markdown("---")
        
        # Run statistics
        st.markdown("### Run Statistics")
        
        completed_runs = db.query(Run).filter(Run.status == 'completed').count()
        failed_runs = db.query(Run).filter(Run.status == 'failed').count()
        running_runs = db.query(Run).filter(Run.status == 'running').count()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", run_count)
        with col2:
            st.metric("✅ Completed", completed_runs)
        with col3:
            st.metric("❌ Failed", failed_runs)
        with col4:
            st.metric("🔄 Running", running_runs)
        
        # Success rate
        if run_count > 0:
            success_rate = (completed_runs / run_count) * 100
            st.progress(success_rate / 100)
            st.caption(f"Success Rate: {success_rate:.1f}%")
        
        st.markdown("---")
        
        # Database info
        st.markdown("### Database Information")
        
        import os
        db_path = Config.DB_PATH
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
            st.metric("Database Size", f"{db_size / 1024:.2f} KB")
            st.caption(f"Path: {db_path}")
        
        # FAISS index info
        faiss_path = "faiss_index"
        if os.path.exists(faiss_path):
            total_size = sum(
                os.path.getsize(os.path.join(faiss_path, f))
                for f in os.listdir(faiss_path)
                if os.path.isfile(os.path.join(faiss_path, f))
            )
            st.metric("FAISS Index Size", f"{total_size / 1024:.2f} KB")
    
    finally:
        db.close()

def render_configuration():
    """System configuration"""
    from config import Config
    st.subheader("System Configuration")
    
    # Display current configuration
    st.markdown("### Current Configuration")
    
    config_data = {
        "Application": {
            "Name": Config.APP_NAME,
            "Version": Config.APP_VERSION,
            "Debug Mode": Config.DEBUG
        },
        "Server": {
            "Host": Config.HOST,
            "Port": Config.PORT
        },
        "Database": {
            "Path": Config.DB_PATH,
            "URL": Config.DATABASE_URL
        },
        "Azure OpenAI": {
            "Endpoint": Config.AZURE_OPENAI_ENDPOINT[:50] + "...",
            "API Version": Config.AZURE_OPENAI_API_VERSION,
            "Deployment": Config.AZURE_OPENAI_DEPLOYMENT,
            "Model": Config.AZURE_OPENAI_MODEL
        }
    }
    
    for section, values in config_data.items():
        with st.expander(f"🔧 {section}"):
            for key, value in values.items():
                st.markdown(f"**{key}:** `{value}`")
    
    st.markdown("---")
    
    # System actions
    st.markdown("### System Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Rebuild FAISS Index", use_container_width=True):
            with st.spinner("Rebuilding index..."):
                try:
                    from components.vector_indexer import VectorIndexer
                    indexer = VectorIndexer()
                    indexer.clear_index()
                    st.success("✅ FAISS index cleared and ready for rebuild")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with col2:
        if st.button("📊 Export Database Schema", use_container_width=True):
            schema = """
-- Self Agent Database Schema

CREATE TABLE flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    current_version INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE flow_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    author VARCHAR(255) DEFAULT 'system',
    FOREIGN KEY (flow_id) REFERENCES flows(id)
);

CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    FOREIGN KEY (flow_id) REFERENCES flows(id)
);

CREATE TABLE run_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    result_json TEXT,
    started_at DATETIME,
    finished_at DATETIME,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE connectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL,
    capabilities_json TEXT,
    config_ref TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(255) DEFAULT 'default_user',
    flow_id INTEGER,
    message TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_id VARCHAR(255)
);

CREATE TABLE memory_kv (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vector_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type VARCHAR(100) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE intent_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent VARCHAR(100) NOT NULL,
    sample_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
            """
            st.download_button(
                label="📥 Download Schema",
                data=schema,
                file_name="schema.sql",
                mime="text/plain",
                use_container_width=True
            )
    
    st.markdown("---")
    
    # Danger zone
    with st.expander("⚠️ Danger Zone", expanded=False):
        st.warning("These actions are irreversible!")
        
        if st.button("🗑️ Clear All Conversations", type="secondary"):
            st.error("This feature is disabled for safety")
        
        if st.button("🗑️ Clear All Runs", type="secondary"):
            st.error("This feature is disabled for safety")
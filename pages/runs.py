# pages/runs.py
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime
import time

def render():
    st.title("📊 Execution Runs")
    st.markdown("Monitor and track workflow executions")
    
    # Tabs
    tab1, tab2 = st.tabs(["📋 Run History", "🔍 Run Details"])
    
    with tab1:
        render_run_history()
    
    with tab2:
        render_run_details()

def render_run_history():
    """Display execution history"""
    st.subheader("Run History")
    
    # Get all flows to fetch their runs
    try:
        flows_response = httpx.get(f"{st.session_state.api_url}/flows", timeout=5.0)
        
        if flows_response.status_code != 200:
            st.error("Failed to load flows")
            return
        
        flows = flows_response.json()
        
        if not flows:
            st.info("No flows found")
            return
        
        # Collect all runs from database
        from database import Run, Flow
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        engine = create_engine(f'sqlite:///{Config.DB_PATH}')
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            runs = db.query(Run).order_by(Run.started_at.desc()).limit(50).all()
            
            if not runs:
                st.info("No execution history found. Execute a flow to see results here.")
                return
            
            # Create dataframe
            runs_data = []
            for run in runs:
                flow = db.query(Flow).filter(Flow.id == run.flow_id).first()
                runs_data.append({
                    'Run ID': run.id,
                    'Flow': flow.name if flow else f'Flow {run.flow_id}',
                    'Version': f'v{run.version_no}',
                    'Status': run.status,
                    'Started': run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else 'N/A',
                    'Finished': run.finished_at.strftime('%Y-%m-%d %H:%M:%S') if run.finished_at else 'Running...',
                })
            
            df = pd.DataFrame(runs_data)
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=['completed', 'running', 'failed', 'queued'],
                    default=['completed', 'running', 'failed']
                )
            
            with col2:
                flow_filter = st.multiselect(
                    "Filter by Flow",
                    options=df['Flow'].unique().tolist(),
                    default=df['Flow'].unique().tolist()
                )
            
            # Apply filters
            if status_filter:
                df = df[df['Status'].isin(status_filter)]
            if flow_filter:
                df = df[df['Flow'].isin(flow_filter)]
            
            # Display with color coding
            def color_status(val):
                colors = {
                    'completed': 'background-color: #d1fae5',
                    'running': 'background-color: #fef3c7',
                    'failed': 'background-color: #fee2e2',
                    'queued': 'background-color: #e5e7eb'
                }
                return colors.get(val, '')
            
            styled_df = df.style.applymap(color_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Quick view buttons
            st.markdown("### Quick View")
            cols = st.columns(min(5, len(runs)))
            for idx, (col, run) in enumerate(zip(cols, runs[:5])):
                with col:
                    if st.button(f"Run {run.id}", key=f"qv_{run.id}"):
                        st.session_state.selected_run_id = run.id
                        st.rerun()
        
        finally:
            db.close()
    
    except Exception as e:
        st.error(f"Error loading run history: {str(e)}")

def render_run_details():
    """Display detailed run information"""
    st.subheader("Run Details")
    
    # Run ID input
    col1, col2 = st.columns([3, 1])
    with col1:
        run_id = st.number_input(
            "Enter Run ID",
            min_value=1,
            value=st.session_state.get('selected_run_id', 1),
            key="run_id_input"
        )
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    
    # Fetch run details
    try:
        response = httpx.get(
            f"{st.session_state.api_url}/runs/{run_id}",
            timeout=5.0
        )
        
        if response.status_code == 404:
            st.warning(f"Run {run_id} not found")
            return
        
        if response.status_code != 200:
            st.error("Failed to load run details")
            return
        
        run = response.json()
        
        # Display run summary
        st.markdown("### Run Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = run['status']
            status_emoji = {
                'completed': '✅',
                'running': '🔄',
                'failed': '❌',
                'queued': '⏳'
            }.get(status, '❓')
            st.metric("Status", f"{status_emoji} {status.upper()}")
        
        with col2:
            st.metric("Flow ID", run['flow_id'])
        
        with col3:
            st.metric("Version", f"v{run['version_no']}")
        
        with col4:
            st.metric("Run ID", run['run_id'])
        
        # Timeline
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Started:** {run.get('started_at', 'N/A')}")
        with col2:
            st.markdown(f"**Finished:** {run.get('finished_at', 'N/A')}")
        
        st.markdown("---")
        
        # Display steps
        if run.get('steps'):
            st.markdown("### Execution Steps")
            
            for idx, step in enumerate(run['steps'], 1):
                status = step['status']
                
                # Status icon and color
                status_config = {
                    'completed': ('🟢', '#10b981'),
                    'running': ('🟡', '#f59e0b'),
                    'failed': ('🔴', '#ef4444'),
                    'pending': ('⚪', '#6b7280')
                }
                
                icon, color = status_config.get(status, ('⚪', '#6b7280'))
                
                with st.expander(f"{icon} Step {idx}: {step['name']} - {status.upper()}", expanded=(status in ['running', 'failed'])):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Step ID:** `{step['step_id']}`")
                        st.markdown(f"**Status:** {status}")
                    
                    with col2:
                        if step.get('started_at'):
                            st.markdown(f"**Started:** {step['started_at']}")
                        if step.get('finished_at'):
                            st.markdown(f"**Finished:** {step['finished_at']}")
                    
                    # Display result
                    if step.get('result'):
                        st.markdown("**Result:**")
                        st.json(step['result'])
            
            # Progress bar
            completed_steps = len([s for s in run['steps'] if s['status'] == 'completed'])
            total_steps = len(run['steps'])
            progress = completed_steps / total_steps if total_steps > 0 else 0
            
            st.progress(progress)
            st.caption(f"{completed_steps}/{total_steps} steps completed")
        else:
            st.info("No steps found for this run")
    
    except Exception as e:
        st.error(f"Error loading run details: {str(e)}")
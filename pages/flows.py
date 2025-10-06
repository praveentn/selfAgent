# pages/flows.py
import streamlit as st
import httpx
import yaml
import json
from datetime import datetime

def render():
    st.title("🔄 Process Flows")
    st.markdown("Create, manage, and execute process workflows")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 All Flows", "➕ Create Flow", "📝 Flow Designer"])
    
    with tab1:
        render_flows_list()
    
    with tab2:
        render_create_flow()
    
    with tab3:
        render_flow_designer()

def render_flows_list():
    """Display list of all flows"""
    st.subheader("All Flows")
    
    try:
        response = httpx.get(f"{st.session_state.api_url}/flows", timeout=5.0)
        
        if response.status_code == 200:
            flows = response.json()
            
            if not flows:
                st.info("No flows found. Create your first flow!")
                return
            
            # Display flows as cards
            for flow in flows:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"### {flow['name']}")
                        st.caption(flow['description'])
                    
                    with col2:
                        st.metric("Version", f"v{flow['current_version']}")
                        st.caption(f"Updated: {flow['updated_at'][:10]}")
                    
                    with col3:
                        if st.button("▶️ Execute", key=f"exec_{flow['id']}"):
                            execute_flow(flow['id'])
                        
                        if st.button("👁️ View", key=f"view_{flow['id']}"):
                            st.session_state.selected_flow_id = flow['id']
                            st.rerun()
                    
                    st.markdown("---")
            
            # Show flow details if selected
            if 'selected_flow_id' in st.session_state:
                show_flow_details(st.session_state.selected_flow_id)
        
        else:
            st.error("Failed to load flows")
    
    except Exception as e:
        st.error(f"Error loading flows: {str(e)}")

def show_flow_details(flow_id):
    """Show detailed flow information"""
    try:
        response = httpx.get(
            f"{st.session_state.api_url}/flows/{flow_id}",
            timeout=5.0
        )
        
        if response.status_code == 200:
            flow = response.json()
            
            st.markdown("---")
            st.subheader(f"📄 Flow Details: {flow['name']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {flow['id']}")
                st.markdown(f"**Version:** v{flow['current_version']}")
            with col2:
                st.markdown(f"**Created:** {flow['created_at'][:10]}")
                st.markdown(f"**Updated:** {flow['updated_at'][:10]}")
            
            st.markdown(f"**Description:** {flow['description']}")
            
            # Display steps
            if flow.get('content') and flow['content'].get('steps'):
                st.markdown("### Steps")
                
                for i, step in enumerate(flow['content']['steps'], 1):
                    with st.expander(f"Step {i}: {step.get('name', 'Unnamed')}"):
                        st.json(step)
            
            # Display YAML
            with st.expander("📋 View YAML"):
                st.code(yaml.dump(flow['content'], default_flow_style=False), language='yaml')
            
            if st.button("🔙 Back to List"):
                del st.session_state.selected_flow_id
                st.rerun()
    
    except Exception as e:
        st.error(f"Error loading flow details: {str(e)}")

def execute_flow(flow_id):
    """Execute a flow"""
    try:
        with st.spinner("Executing flow..."):
            response = httpx.post(
                f"{st.session_state.api_url}/flows/{flow_id}/execute",
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                st.success(f"✅ Flow executed! Run ID: {result['run_id']}")
                st.session_state.last_run_id = result['run_id']
                
                # Show run status
                with st.expander("📊 View Run Status"):
                    show_run_status(result['run_id'])
            else:
                st.error("Failed to execute flow")
    
    except Exception as e:
        st.error(f"Error executing flow: {str(e)}")

def show_run_status(run_id):
    """Show run status"""
    try:
        response = httpx.get(
            f"{st.session_state.api_url}/runs/{run_id}",
            timeout=5.0
        )
        
        if response.status_code == 200:
            run = response.json()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", run['status'].upper())
            with col2:
                st.metric("Flow ID", run['flow_id'])
            with col3:
                st.metric("Version", f"v{run['version_no']}")
            
            # Display steps
            if run.get('steps'):
                st.markdown("### Steps")
                for step in run['steps']:
                    status_color = {
                        'completed': '🟢',
                        'running': '🟡',
                        'failed': '🔴',
                        'pending': '⚪'
                    }.get(step['status'], '⚪')
                    
                    st.markdown(f"{status_color} **{step['name']}** - {step['status']}")
    
    except Exception as e:
        st.error(f"Error loading run status: {str(e)}")

def render_create_flow():
    """Form to create new flow"""
    st.subheader("Create New Flow")
    
    with st.form("create_flow_form"):
        name = st.text_input("Flow Name", placeholder="e.g., Invoice Processing")
        description = st.text_area("Description", placeholder="What does this flow do?")
        
        st.markdown("### Steps")
        num_steps = st.number_input("Number of Steps", min_value=1, max_value=10, value=2)
        
        steps = []
        for i in range(num_steps):
            with st.expander(f"Step {i+1}"):
                step_id = st.text_input(f"Step ID", value=f"step_{i+1}", key=f"sid_{i}")
                step_name = st.text_input(f"Step Name", placeholder="e.g., Read Invoice", key=f"sname_{i}")
                step_type = st.selectbox(
                    f"Type",
                    ["sql", "sharepoint", "email", "notification"],
                    key=f"stype_{i}"
                )
                step_action = st.text_input(f"Action", placeholder="e.g., query", key=f"saction_{i}")
                
                steps.append({
                    "id": step_id,
                    "name": step_name,
                    "type": step_type,
                    "connector": step_type,
                    "action": step_action,
                    "params": {}
                })
        
        submitted = st.form_submit_button("Create Flow")
        
        if submitted:
            if not name:
                st.error("Flow name is required")
                return
            
            try:
                response = httpx.post(
                    f"{st.session_state.api_url}/flows",
                    json={
                        "name": name,
                        "description": description,
                        "steps": steps
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Flow created! ID: {result['flow_id']}")
                else:
                    st.error("Failed to create flow")
            
            except Exception as e:
                st.error(f"Error creating flow: {str(e)}")

def render_flow_designer():
    """YAML/JSON flow designer"""
    st.subheader("Flow Designer")
    st.markdown("Design flows using YAML or JSON")
    
    format_choice = st.radio("Format", ["YAML", "JSON"], horizontal=True)
    
    # Template
    template = {
        "name": "Sample Flow",
        "description": "A sample workflow",
        "steps": [
            {
                "id": "step_1",
                "name": "Read Data",
                "type": "sharepoint",
                "connector": "sharepoint",
                "action": "read_file",
                "params": {"filename": "data.xlsx"}
            },
            {
                "id": "step_2",
                "name": "Process Data",
                "type": "sql",
                "connector": "sql",
                "action": "insert",
                "params": {"table": "invoices"}
            },
            {
                "id": "step_3",
                "name": "Send Notification",
                "type": "email",
                "connector": "email",
                "action": "send",
                "params": {"to": "finance@company.com"}
            }
        ]
    }
    
    if format_choice == "YAML":
        flow_text = st.text_area(
            "Flow Definition (YAML)",
            value=yaml.dump(template, default_flow_style=False),
            height=400
        )
    else:
        flow_text = st.text_area(
            "Flow Definition (JSON)",
            value=json.dumps(template, indent=2),
            height=400
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Validate"):
            try:
                if format_choice == "YAML":
                    flow_data = yaml.safe_load(flow_text)
                else:
                    flow_data = json.loads(flow_text)
                
                st.success("✅ Valid format!")
                st.json(flow_data)
            except Exception as e:
                st.error(f"❌ Invalid format: {str(e)}")
    
    with col2:
        if st.button("💾 Create Flow"):
            try:
                if format_choice == "YAML":
                    flow_data = yaml.safe_load(flow_text)
                else:
                    flow_data = json.loads(flow_text)
                
                response = httpx.post(
                    f"{st.session_state.api_url}/flows",
                    json={
                        "name": flow_data.get("name", "Untitled Flow"),
                        "description": flow_data.get("description", ""),
                        "steps": flow_data.get("steps", [])
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Flow created! ID: {result['flow_id']}")
                else:
                    st.error("Failed to create flow")
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
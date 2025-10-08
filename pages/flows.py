# pages/flows.py
import streamlit as st
import httpx
import yaml
import json
from datetime import datetime

def render():
    st.title("📄 Process Flows")
    st.markdown("Create, manage, and execute process workflows")
    
    tabs = st.tabs(["📋 All Flows", "➕ Create Flow", "🔧 Flow Designer"])
    
    with tabs[0]:
        render_flows_list()
    
    with tabs[1]:
        render_create_flow()
    
    with tabs[2]:
        render_flow_designer()


def render_flows_list():
    """Display list of all flows with modify/delete options"""
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
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.markdown(f"### {flow['name']}")
                        st.caption(flow['description'])
                    
                    with col2:
                        st.metric("Version", f"v{flow['current_version']}")
                        st.caption(f"Updated: {flow['updated_at'][:10]}")
                    
                    with col3:
                        action_col1, action_col2 = st.columns(2)
                        
                        with action_col1:
                            if st.button("▶️ Execute", key=f"exec_{flow['id']}", use_container_width=True):
                                execute_flow(flow['id'])
                            
                            if st.button("✏️ Modify", key=f"mod_{flow['id']}", use_container_width=True):
                                st.session_state.modify_flow_id = flow['id']
                                st.rerun()
                        
                        with action_col2:
                            if st.button("👁️ View", key=f"view_{flow['id']}", use_container_width=True):
                                st.session_state.selected_flow_id = flow['id']
                                st.rerun()
                            
                            if st.button("🗑️ Delete", key=f"del_{flow['id']}", use_container_width=True, type="secondary"):
                                st.session_state.delete_flow_id = flow['id']
                                st.rerun()
                    
                    st.markdown("---")
            
            # Show flow details if selected
            if 'selected_flow_id' in st.session_state:
                show_flow_details(st.session_state.selected_flow_id)
            
            # Show modify flow dialog
            if 'modify_flow_id' in st.session_state:
                show_modify_flow_dialog(st.session_state.modify_flow_id)
            
            # Show delete confirmation
            if 'delete_flow_id' in st.session_state:
                show_delete_confirmation(st.session_state.delete_flow_id)
        
        else:
            st.error("Failed to load flows")
    
    except Exception as e:
        st.error(f"Error loading flows: {str(e)}")


def show_flow_details(flow_id):
    """Show detailed flow information"""
    try:
        response = httpx.get(f"{st.session_state.api_url}/flows/{flow_id}", timeout=5.0)
        
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


def show_modify_flow_dialog(flow_id):
    """Show flow modification dialog"""
    st.markdown("---")
    st.subheader("✏️ Modify Flow")
    
    try:
        response = httpx.get(f"{st.session_state.api_url}/flows/{flow_id}", timeout=5.0)
        
        if response.status_code == 200:
            flow = response.json()
            flow_content = flow.get('content', {})
            
            with st.form("modify_flow_form"):
                st.markdown(f"**Modifying:** {flow['name']}")
                
                # Update description
                new_description = st.text_area(
                    "Description",
                    value=flow['description'],
                    height=100
                )
                
                # Modify steps
                st.markdown("### Steps")
                
                steps = flow_content.get('steps', [])
                modified_steps = []
                
                for i, step in enumerate(steps):
                    with st.expander(f"Step {i+1}: {step.get('name', 'Unnamed')}", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            step_name = st.text_input(
                                "Step Name",
                                value=step.get('name', ''),
                                key=f"mod_name_{i}"
                            )
                            
                            step_connector = st.text_input(
                                "Connector",
                                value=step.get('connector', ''),
                                key=f"mod_conn_{i}"
                            )
                            
                            step_action = st.text_input(
                                "Action",
                                value=step.get('action', ''),
                                key=f"mod_action_{i}"
                            )
                            
                            step_params = st.text_area(
                                "Parameters (JSON)",
                                value=json.dumps(step.get('params', {}), indent=2),
                                key=f"mod_params_{i}",
                                height=100
                            )
                        
                        with col2:
                            remove_step = st.checkbox("Remove", key=f"mod_remove_{i}")
                        
                        if not remove_step:
                            try:
                                params = json.loads(step_params)
                            except:
                                params = {}
                            
                            modified_steps.append({
                                "id": step.get('id', f"step_{i+1}"),
                                "name": step_name,
                                "type": step.get('type', step_connector),
                                "connector": step_connector,
                                "action": step_action,
                                "params": params
                            })
                
                # Add new step option
                st.markdown("### Add New Step")
                add_new = st.checkbox("Add new step")
                
                if add_new:
                    new_step_name = st.text_input("New Step Name")
                    new_step_connector = st.selectbox(
                        "Connector",
                        ["local_file", "sql", "sharepoint", "email", "notification", "python_executor"]
                    )
                    new_step_action = st.text_input("Action")
                    new_step_params = st.text_area("Parameters (JSON)", value="{}")
                    
                    if new_step_name and new_step_action:
                        try:
                            params = json.loads(new_step_params)
                        except:
                            params = {}
                        
                        modified_steps.append({
                            "id": f"step_{len(modified_steps) + 1}",
                            "name": new_step_name,
                            "type": new_step_connector,
                            "connector": new_step_connector,
                            "action": new_step_action,
                            "params": params
                        })
                
                col1, col2 = st.columns(2)
                
                with col1:
                    submitted = st.form_submit_button("💾 Save Changes", type="primary")
                
                with col2:
                    cancel = st.form_submit_button("❌ Cancel")
                
                if cancel:
                    del st.session_state.modify_flow_id
                    st.rerun()
                
                if submitted:
                    try:
                        # Update flow
                        update_response = httpx.post(
                            f"{st.session_state.api_url}/flows/{flow_id}/update",
                            json={
                                "description": new_description,
                                "steps": modified_steps
                            },
                            timeout=10.0
                        )
                        
                        if update_response.status_code == 200:
                            st.success("✅ Flow updated successfully!")
                            del st.session_state.modify_flow_id
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to update flow")
                    
                    except Exception as e:
                        st.error(f"Error updating flow: {str(e)}")
    
    except Exception as e:
        st.error(f"Error loading flow: {str(e)}")


def show_delete_confirmation(flow_id):
    """Show delete confirmation dialog"""
    st.markdown("---")
    st.warning("⚠️ **Delete Flow Confirmation**")
    
    try:
        response = httpx.get(f"{st.session_state.api_url}/flows/{flow_id}", timeout=5.0)
        
        if response.status_code == 200:
            flow = response.json()
            
            st.markdown(f"Are you sure you want to delete **{flow['name']}**?")
            st.caption("This action cannot be undone.")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("🗑️ Yes, Delete", type="primary"):
                    delete_flow(flow_id)
            
            with col2:
                if st.button("❌ Cancel"):
                    del st.session_state.delete_flow_id
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


def delete_flow(flow_id):
    """Delete a flow"""
    try:
        response = httpx.delete(
            f"{st.session_state.api_url}/flows/{flow_id}",
            timeout=5.0
        )
        
        if response.status_code == 200:
            st.success("✅ Flow deleted successfully!")
            if 'delete_flow_id' in st.session_state:
                del st.session_state.delete_flow_id
            time.sleep(1)
            st.rerun()
        else:
            st.error("Failed to delete flow")
    
    except Exception as e:
        st.error(f"Error deleting flow: {str(e)}")


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
            else:
                st.error("Failed to execute flow")
    
    except Exception as e:
        st.error(f"Error executing flow: {str(e)}")


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
            with st.expander(f"Step {i+1}", expanded=True):
                step_id = st.text_input(f"Step ID", value=f"step_{i+1}", key=f"sid_{i}")
                step_name = st.text_input(f"Step Name", placeholder="e.g., Read Invoice", key=f"sname_{i}")
                step_type = st.selectbox(
                    f"Connector",
                    ["local_file", "sql", "sharepoint", "email", "notification", "python_executor"],
                    key=f"stype_{i}"
                )
                step_action = st.text_input(f"Action", placeholder="e.g., read_file", key=f"saction_{i}")
                
                steps.append({
                    "id": step_id,
                    "name": step_name,
                    "type": step_type,
                    "connector": step_type,
                    "action": step_action,
                    "params": {}
                })
        
        submitted = st.form_submit_button("Create Flow", type="primary")
        
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
    
    template = {
        "name": "Sample Flow",
        "description": "A sample workflow",
        "steps": [
            {
                "id": "step_1",
                "name": "Read Data",
                "type": "local_file",
                "connector": "local_file",
                "action": "read_file",
                "params": {"filename": "data.txt"}
            },
            {
                "id": "step_2",
                "name": "Process Data",
                "type": "sql",
                "connector": "sql",
                "action": "insert",
                "params": {"table": "invoices"}
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
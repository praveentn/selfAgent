# pages/connectors.py
import streamlit as st
import httpx
import json

def render():
    st.title("🔌 Connectors")
    st.markdown("Manage tool integrations and capabilities")
    
    # Tabs
    tab1, tab2 = st.tabs(["📋 Available Connectors", "🧪 Test Connector"])
    
    with tab1:
        render_connectors_list()
    
    with tab2:
        render_test_connector()

def render_connectors_list():
    """Display list of available connectors"""
    st.subheader("Available Connectors")
    
    try:
        response = httpx.get(f"{st.session_state.api_url}/connectors", timeout=5.0)
        
        if response.status_code == 200:
            connectors = response.json()
            
            if not connectors:
                st.info("No connectors available")
                return
            
            # Display as cards
            for connector in connectors:
                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])
                    
                    with col1:
                        # Connector icon
                        icon = {
                            'sql': '🗄️',
                            'sharepoint': '📁',
                            'email': '📧',
                            'notification': '🔔'
                        }.get(connector['name'], '🔌')
                        
                        st.markdown(f"## {icon} {connector['name'].upper()}")
                        st.caption(f"Type: {connector['type']}")
                    
                    with col2:
                        st.markdown("**Capabilities:**")
                        capabilities = connector.get('capabilities', [])
                        if capabilities:
                            for cap in capabilities:
                                st.markdown(f"✓ `{cap}`")
                        else:
                            st.caption("No capabilities listed")
                    
                    with col3:
                        if st.button("Test", key=f"test_{connector['id']}"):
                            test_connector_inline(connector['name'])
                    
                    st.markdown("---")
        
        else:
            st.error("Failed to load connectors")
    
    except Exception as e:
        st.error(f"Error loading connectors: {str(e)}")

def test_connector_inline(connector_name):
    """Test connector and show result"""
    try:
        with st.spinner(f"Testing {connector_name}..."):
            response = httpx.post(
                f"{st.session_state.api_url}/connectors/test",
                json={"connector_name": connector_name},
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'success':
                    st.success(f"✅ {connector_name} is working!")
                    with st.expander("View Details"):
                        st.json(result)
                else:
                    st.error(f"❌ {connector_name} test failed")
                    st.json(result)
            else:
                st.error("Test failed")
    
    except Exception as e:
        st.error(f"Error testing connector: {str(e)}")

def render_test_connector():
    """Test connector with custom actions"""
    st.subheader("Test Connector")
    st.markdown("Execute connector actions with custom parameters")
    
    # Get list of connectors
    try:
        response = httpx.get(f"{st.session_state.api_url}/connectors", timeout=5.0)
        
        if response.status_code == 200:
            connectors = response.json()
            connector_names = [c['name'] for c in connectors]
            
            if not connector_names:
                st.info("No connectors available")
                return
            
            # Test form
            with st.form("test_connector_form"):
                selected_connector = st.selectbox("Select Connector", connector_names)
                
                # Get capabilities for selected connector
                selected_conn_data = next(
                    (c for c in connectors if c['name'] == selected_connector),
                    None
                )
                
                if selected_conn_data:
                    capabilities = selected_conn_data.get('capabilities', [])
                    if capabilities:
                        action = st.selectbox("Action", capabilities)
                    else:
                        action = st.text_input("Action")
                else:
                    action = st.text_input("Action")
                
                params_json = st.text_area(
                    "Parameters (JSON)",
                    value='{}',
                    height=150,
                    help="Enter parameters as JSON object"
                )
                
                submitted = st.form_submit_button("Execute")
                
                if submitted:
                    try:
                        params = json.loads(params_json)
                        
                        with st.spinner("Executing..."):
                            # Execute connector action
                            test_response = httpx.post(
                                f"{st.session_state.api_url}/connectors/test",
                                json={"connector_name": selected_connector},
                                timeout=10.0
                            )
                            
                            if test_response.status_code == 200:
                                result = test_response.json()
                                
                                st.success("✅ Execution completed")
                                
                                # Display result
                                st.markdown("### Result")
                                st.json(result)
                                
                                # Show execution details
                                with st.expander("Execution Details"):
                                    st.markdown(f"**Connector:** {selected_connector}")
                                    st.markdown(f"**Action:** {action}")
                                    st.markdown(f"**Parameters:**")
                                    st.json(params)
                            else:
                                st.error("Execution failed")
                    
                    except json.JSONDecodeError:
                        st.error("Invalid JSON in parameters")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        else:
            st.error("Failed to load connectors")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    # Example parameters
    with st.expander("💡 Example Parameters"):
        st.markdown("### SQL Connector")
        st.code('{\n  "query": "SELECT * FROM users",\n  "table": "users"\n}', language='json')
        
        st.markdown("### SharePoint Connector")
        st.code('{\n  "filename": "invoice.xlsx",\n  "path": "/documents"\n}', language='json')
        
        st.markdown("### Email Connector")
        st.code('{\n  "to": "user@example.com",\n  "subject": "Test Email",\n  "body": "Hello World"\n}', language='json')
        
        st.markdown("### Notification Connector")
        st.code('{\n  "message": "Process completed",\n  "priority": "high"\n}', language='json')
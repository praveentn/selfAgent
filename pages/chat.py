# pages/chat.py
import streamlit as st
import httpx
from datetime import datetime
import json
import time

def render():
    st.title("💬 Chat Console")
    st.markdown("Interact with Self Agent using natural language")
    
    # Initialize chat history
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
        # Load conversation history from API
        try:
            response = httpx.get(
                f"{st.session_state.api_url}/conversations/{st.session_state.user_id}",
                timeout=5.0
            )
            if response.status_code == 200:
                conversations = response.json()
                st.session_state.chat_messages = [
                    {"role": conv["role"], "content": conv["message"]}
                    for conv in conversations
                ]
        except Exception as e:
            st.info("Starting new conversation")
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display structured data if present
            if message.get("data"):
                with st.expander("📊 View Data"):
                    st.json(message["data"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = httpx.post(
                        f"{st.session_state.api_url}/intent",
                        json={
                            "text": prompt,
                            "session_id": st.session_state.user_id,
                            "user_id": st.session_state.user_id
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        assistant_response = data.get("response", "I'm not sure how to respond to that.")
                        intent = data.get("intent", "unknown")
                        confidence = data.get("confidence", 0.0)
                        parameters = data.get("parameters", {})
                        
                        # Handle specific intents with actual execution
                        execution_result = None
                        
                        if intent == "create_flow" and confidence > 0.7:
                            execution_result = handle_create_flow(prompt, parameters)
                            if execution_result:
                                assistant_response = execution_result
                        
                        elif intent == "read_file" and confidence > 0.7:
                            execution_result = handle_read_file(parameters)
                            if execution_result:
                                assistant_response = execution_result
                        
                        elif intent == "run_flow" and confidence > 0.7:
                            execution_result = handle_run_flow(parameters)
                            if execution_result:
                                assistant_response = execution_result
                        
                        # Display response
                        st.markdown(assistant_response)
                        
                        # Show intent details in expander
                        with st.expander("🔍 Intent Details"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Intent", intent)
                            with col2:
                                st.metric("Confidence", f"{confidence:.2%}")
                            
                            if parameters:
                                st.json(parameters)
                        
                        # Add to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                    
                    else:
                        error_msg = "Sorry, I encountered an error. Please try again."
                        st.error(error_msg)
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                
                except httpx.TimeoutException:
                    error_msg = "Request timed out. Please try again."
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Sidebar with chat options
    with st.sidebar:
        st.markdown("### Chat Options")
        
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        
        if st.button("📋 List Flows"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "List all available flows"
            })
            st.rerun()
        
        if st.button("🔌 Show Connectors"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "What connectors are available?"
            })
            st.rerun()
        
        if st.button("📊 Recent Runs"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Show me recent execution history"
            })
            st.rerun()
        
        if st.button("📁 Read File"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Read file1.txt from data folder"
            })
            st.rerun()


def handle_create_flow(description: str, parameters: dict) -> str:
    """Handle flow creation from description"""
    try:
        with st.spinner("Creating flow..."):
            response = httpx.post(
                f"{st.session_state.api_url}/flows/create_from_description",
                json={"description": description},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                flow_info = f"""✅ **Flow Created Successfully!**

**Name:** {result['name']}
**Flow ID:** {result['flow_id']}
**Version:** v{result['version']}

The flow has been created and is ready to execute. You can run it by saying "execute {result['name']}" or "run flow {result['flow_id']}"."""
                
                with st.expander("📄 View Flow Definition"):
                    st.json(result.get('definition', {}))
                
                return flow_info
            else:
                return "❌ Failed to create flow. Please try again with more details."
    
    except Exception as e:
        return f"❌ Error creating flow: {str(e)}"


def handle_read_file(parameters: dict) -> str:
    """Handle file reading by creating and executing a flow"""
    filename = parameters.get('filename', 'file1.txt')
    
    try:
        with st.spinner(f"Reading {filename}..."):
            # Create a flow to read the file
            flow_def = {
                "name": f"Read {filename}",
                "description": f"Read contents of {filename}",
                "steps": [
                    {
                        "id": "read_step",
                        "name": f"Read {filename}",
                        "type": "local_file",
                        "connector": "local_file",
                        "action": "read_file",
                        "params": {"filename": filename}
                    }
                ]
            }
            
            # Create flow
            create_response = httpx.post(
                f"{st.session_state.api_url}/flows",
                json=flow_def,
                timeout=10.0
            )
            
            if create_response.status_code == 200:
                flow_id = create_response.json()['flow_id']
                
                # Execute flow
                exec_response = httpx.post(
                    f"{st.session_state.api_url}/flows/{flow_id}/execute",
                    timeout=30.0
                )
                
                if exec_response.status_code == 200:
                    run_id = exec_response.json()['run_id']
                    
                    # Wait for execution and get result
                    result = wait_for_run_completion(run_id, max_wait=10)
                    
                    if result:
                        return result
                    else:
                        return f"❌ Could not retrieve execution results for run {run_id}"
            
            return "❌ Failed to execute file reading operation"
    
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


def handle_run_flow(parameters: dict) -> str:
    """Handle flow execution and display results"""
    flow_name = parameters.get('flow_name')
    flow_id = parameters.get('flow_id')
    
    try:
        # Find flow by name if only name provided
        if not flow_id and flow_name:
            flows_response = httpx.get(
                f"{st.session_state.api_url}/flows",
                timeout=5.0
            )
            
            if flows_response.status_code == 200:
                flows = flows_response.json()
                matching = [f for f in flows if flow_name.lower() in f['name'].lower()]
                
                if matching:
                    flow_id = matching[0]['id']
                    flow_name = matching[0]['name']
        
        if flow_id:
            with st.spinner(f"Executing flow..."):
                # Execute flow
                exec_response = httpx.post(
                    f"{st.session_state.api_url}/flows/{flow_id}/execute",
                    timeout=30.0
                )
                
                if exec_response.status_code == 200:
                    run_id = exec_response.json()['run_id']
                    
                    # Wait for execution and get result
                    result = wait_for_run_completion(run_id, max_wait=10)
                    
                    if result:
                        return result
                    else:
                        return f"✅ Flow execution started (Run ID: {run_id}). Check the Runs tab for details."
                else:
                    return "❌ Failed to execute flow"
        else:
            return f"❌ Could not find flow: {flow_name}"
    
    except Exception as e:
        return f"❌ Error executing flow: {str(e)}"


def wait_for_run_completion(run_id: int, max_wait: int = 10) -> str:
    """Wait for run to complete and format results"""
    for i in range(max_wait):
        try:
            time.sleep(1)  # Wait 1 second between checks
            
            run_response = httpx.get(
                f"{st.session_state.api_url}/runs/{run_id}",
                timeout=5.0
            )
            
            if run_response.status_code == 200:
                run_data = run_response.json()
                
                if run_data['status'] in ['completed', 'failed']:
                    return format_run_results(run_data)
                
        except Exception as e:
            continue
    
    return None


def format_run_results(run_data: dict) -> str:
    """Format run results for display"""
    status = run_data['status']
    
    if status == 'failed':
        return f"❌ **Execution Failed**\n\nRun ID: {run_data['run_id']}\nStatus: {status}"
    
    # Build result message
    result_parts = [f"✅ **Execution Completed Successfully!**\n"]
    result_parts.append(f"**Run ID:** {run_data['run_id']}")
    result_parts.append(f"**Flow ID:** {run_data['flow_id']}\n")
    
    # Process steps and extract meaningful results
    steps = run_data.get('steps', [])
    
    for step in steps:
        if step['status'] == 'completed' and step.get('result'):
            result = step['result']
            
            # Handle file read results
            if result.get('action') == 'read_file' and result.get('content'):
                content = result['content']
                filename = result.get('filename', 'file')
                
                result_parts.append(f"### 📄 File Content: `{filename}`\n")
                result_parts.append(f"**Size:** {result.get('size_bytes', 0)} bytes")
                result_parts.append(f"**Lines:** {result.get('lines', 0)}\n")
                result_parts.append("**Content:**")
                result_parts.append(f"```\n{content}\n```")
                
                # Display in expander if content is long
                if len(content) > 500:
                    with st.expander("📄 View Full Content"):
                        st.text_area(
                            "File Content",
                            value=content,
                            height=300,
                            disabled=True
                        )
            
            # Handle other result types
            elif result.get('status') == 'success':
                result_parts.append(f"\n**Step:** {step['name']}")
                result_parts.append(f"**Result:** {result.get('result', 'Success')}")
    
    return "\n".join(result_parts)
# pages/chat.py
import streamlit as st
import httpx
from datetime import datetime
import json
import time
import uuid

def render():
    st.title("💬 Chat Console")
    st.markdown("Interact with Self Agent using natural language")
    
    # Initialize session management
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = str(uuid.uuid4())
    
    # Sidebar: Conversation history and sessions
    with st.sidebar:
        render_session_manager()
    
    # Initialize chat history
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
        load_session_history()
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message.get("data"):
                with st.expander("📊 View Data"):
                    st.json(message["data"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = httpx.post(
                        f"{st.session_state.api_url}/intent",
                        json={
                            "text": prompt,
                            "session_id": st.session_state.current_session_id,
                            "user_id": st.session_state.user_id
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        assistant_response = data.get("response", "I'm not sure how to respond.")
                        intent = data.get("intent", "unknown")
                        confidence = data.get("confidence", 0.0)
                        parameters = data.get("parameters", {})
                        
                        # Handle specific intents with better messaging
                        execution_result = None
                        
                        if intent == "set_rule" and confidence > 0.7:
                            execution_result = handle_set_rule(parameters)
                        
                        elif intent == "create_flow" and confidence > 0.7:
                            execution_result = handle_create_flow(prompt, parameters)
                        
                        elif intent == "read_file" and confidence > 0.7:
                            execution_result = handle_read_file(parameters)
                        
                        elif intent == "run_flow" and confidence > 0.7:
                            execution_result = handle_run_flow(parameters)
                        
                        elif intent == "store_memory" and confidence > 0.7:
                            execution_result = handle_store_memory(parameters)
                        
                        if execution_result:
                            assistant_response = execution_result
                        
                        # Display response
                        st.markdown(assistant_response)
                        
                        # Show intent details
                        with st.expander("🔍 Intent Details"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Intent", intent)
                            with col2:
                                st.metric("Confidence", f"{confidence:.2%}")
                            
                            if parameters:
                                st.json(parameters)
                        
                        # Add to history
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


def render_session_manager():
    """Render session management sidebar"""
    st.markdown("### 💬 Chat Sessions")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.chat_messages = []
        st.rerun()
    
    st.markdown("---")
    
    try:
        response = httpx.get(
            f"{st.session_state.api_url}/conversations/sessions/{st.session_state.user_id}",
            timeout=5.0
        )
        
        if response.status_code == 200:
            sessions = response.json()
            
            if sessions:
                st.markdown("**Recent Sessions:**")
                
                for session in sessions[:10]:
                    session_id = session['session_id']
                    message_count = session['message_count']
                    last_updated = session['last_updated'][:16] if session['last_updated'] else 'N/A'
                    
                    is_current = (session_id == st.session_state.current_session_id)
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if st.button(
                            f"{'🟢' if is_current else '⚪'} Session ({message_count} msgs)",
                            key=f"session_{session_id}",
                            use_container_width=True,
                            disabled=is_current
                        ):
                            st.session_state.current_session_id = session_id
                            st.session_state.chat_messages = []
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️", key=f"del_{session_id}"):
                            delete_session(session_id)
                            st.rerun()
                    
                    st.caption(f"Updated: {last_updated}")
            else:
                st.info("No previous sessions")
    
    except Exception as e:
        st.caption(f"Error loading sessions")
    
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("📋 List Flows"):
        st.session_state.chat_messages.append({
            "role": "user",
            "content": "List all available flows"
        })
        st.rerun()
    
    if st.button("🧠 View Memory"):
        st.switch_page("pages/memory.py")


def load_session_history():
    """Load conversation history for current session"""
    try:
        response = httpx.get(
            f"{st.session_state.api_url}/conversations/{st.session_state.user_id}",
            params={"session_id": st.session_state.current_session_id},
            timeout=5.0
        )
        
        if response.status_code == 200:
            conversations = response.json()
            st.session_state.chat_messages = [
                {"role": conv["role"], "content": conv["message"]}
                for conv in conversations
            ]
    except:
        pass


def delete_session(session_id: str):
    """Delete a conversation session"""
    try:
        httpx.delete(
            f"{st.session_state.api_url}/conversations/sessions/{session_id}",
            params={"user_id": st.session_state.user_id},
            timeout=5.0
        )
    except:
        pass


def handle_set_rule(parameters: dict) -> str:
    """Handle behavior rule setting with proper messaging"""
    rule = parameters.get('rule', '')
    
    try:
        response = httpx.post(
            f"{st.session_state.api_url}/memory/set_rule",
            json={
                "rule": rule,
                "user_id": st.session_state.user_id
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            return f"""✅ **Behavior Rule Set**

**Rule:** {rule}

This rule will now affect how I respond in all our conversations. I'll apply this guideline from now on.

You can view all active rules in the **🧠 Memory** tab, where you can also see how they modify my system prompt."""
        else:
            return "❌ Failed to set rule"
    
    except Exception as e:
        return f"❌ Error setting rule: {str(e)}"


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

The workflow has been created and is ready to execute."""
                
                with st.expander("📄 View Flow Definition"):
                    st.json(result.get('definition', {}))
                
                return flow_info
            else:
                return "❌ Failed to create flow. Please try again."
    
    except Exception as e:
        return f"❌ Error creating flow: {str(e)}"


def handle_read_file(parameters: dict) -> str:
    """Handle file reading with dynamic parameters"""
    filename = parameters.get('filename', 'file1.txt')
    
    try:
        with st.spinner(f"Reading {filename}..."):
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
            
            create_response = httpx.post(
                f"{st.session_state.api_url}/flows",
                json=flow_def,
                timeout=10.0
            )
            
            if create_response.status_code == 200:
                flow_id = create_response.json()['flow_id']
                
                exec_response = httpx.post(
                    f"{st.session_state.api_url}/flows/{flow_id}/execute",
                    timeout=30.0
                )
                
                if exec_response.status_code == 200:
                    run_id = exec_response.json()['run_id']
                    result = wait_for_run_completion(run_id, max_wait=10)
                    
                    if result:
                        return result
            
            return f"❌ Failed to read {filename}"
    
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


def handle_run_flow(parameters: dict) -> str:
    """Handle flow execution with parameters"""
    flow_name = parameters.get('flow_name')
    flow_id = parameters.get('flow_id')
    
    try:
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
                exec_response = httpx.post(
                    f"{st.session_state.api_url}/flows/{flow_id}/execute",
                    timeout=30.0
                )
                
                if exec_response.status_code == 200:
                    run_id = exec_response.json()['run_id']
                    result = wait_for_run_completion(run_id, max_wait=10)
                    
                    if result:
                        return result
                    else:
                        return f"✅ Flow execution started (Run ID: {run_id})"
        else:
            return f"❌ Could not find flow: {flow_name}"
    
    except Exception as e:
        return f"❌ Error executing flow: {str(e)}"


def handle_store_memory(parameters: dict) -> str:
    """Handle memory storage"""
    content = parameters.get('content', '')
    
    try:
        response = httpx.post(
            f"{st.session_state.api_url}/memory/store",
            json={
                "content": content,
                "user_id": st.session_state.user_id
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            result = response.json()
            memory_type = result.get('memory_type', 'short-term')
            return f"✅ Stored as {memory_type} memory: {content}"
        else:
            return "❌ Failed to store memory"
    
    except Exception as e:
        return f"❌ Error storing memory: {str(e)}"


def wait_for_run_completion(run_id: int, max_wait: int = 10) -> str:
    """Wait for run to complete and format results"""
    for i in range(max_wait):
        try:
            time.sleep(1)
            
            run_response = httpx.get(
                f"{st.session_state.api_url}/runs/{run_id}",
                timeout=5.0
            )
            
            if run_response.status_code == 200:
                run_data = run_response.json()
                
                if run_data['status'] in ['completed', 'failed']:
                    return format_run_results(run_data)
        except:
            continue
    
    return None


def format_run_results(run_data: dict) -> str:
    """Format run results for display"""
    status = run_data['status']
    
    if status == 'failed':
        return f"❌ **Execution Failed**\n\nRun ID: {run_data['run_id']}"
    
    result_parts = [f"✅ **Execution Completed!**\n"]
    result_parts.append(f"**Run ID:** {run_data['run_id']}\n")
    
    steps = run_data.get('steps', [])
    
    for step in steps:
        if step['status'] == 'completed' and step.get('result'):
            result = step['result']
            
            if result.get('action') == 'read_file' and result.get('content'):
                content = result['content']
                filename = result.get('filename', 'file')
                
                result_parts.append(f"### 📄 File: `{filename}`\n")
                result_parts.append(f"**Size:** {result.get('size_bytes', 0)} bytes")
                result_parts.append(f"**Lines:** {result.get('lines', 0)}\n")
                result_parts.append("**Content:**")
                result_parts.append(f"```\n{content}\n```")
                
                if len(content) > 500:
                    with st.expander("📄 View Full Content"):
                        st.text_area("File Content", value=content, height=300, disabled=True)
            
            elif result.get('status') == 'success':
                result_parts.append(f"\n**Step:** {step['name']}")
                result_parts.append(f"**Result:** {result.get('result', 'Success')}")
    
    return "\n".join(result_parts)
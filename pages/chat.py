# pages/chat.py
import streamlit as st
import httpx
from datetime import datetime

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
                        
                        # Display response
                        st.markdown(assistant_response)
                        
                        # Show intent details in expander
                        with st.expander("🔍 Intent Details"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Intent", intent)
                            with col2:
                                st.metric("Confidence", f"{confidence:.2%}")
                            
                            if data.get("parameters"):
                                st.json(data["parameters"])
                        
                        # Add to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                        
                        # Handle specific intents
                        if intent == "run_flow" and confidence > 0.7:
                            st.info("💡 Tip: Go to the Flows page to execute workflows")
                        elif intent == "list_flows" and confidence > 0.7:
                            st.info("💡 Tip: Check the Flows page to see all workflows")
                    
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
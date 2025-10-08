# pages/memory.py
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime

def render():
    st.title("🧠 Memory & Rules")
    st.markdown("View and manage agent's memory, rules, and conversation behavior")
    
    # Tabs for different memory types
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Active Rules",
        "📚 Long-Term Memory", 
        "💬 Short-Term Context",
        "🔧 System Prompt"
    ])
    
    with tab1:
        render_rules()
    
    with tab2:
        render_long_term_memory()
    
    with tab3:
        render_short_term_memory()
    
    with tab4:
        render_system_prompt()


def render_rules():
    """Display active behavior rules"""
    st.subheader("🎯 Active Conversation Rules")
    st.markdown("These rules modify how the agent responds to you")
    
    try:
        # Get rules from API
        response = httpx.get(
            f"{st.session_state.api_url}/memory/rules/{st.session_state.user_id}",
            timeout=5.0
        )
        
        if response.status_code == 200:
            rules = response.json()
            
            if rules:
                st.info(f"📊 **{len(rules)} active rule(s)** affecting agent behavior")
                
                for idx, rule in enumerate(rules, 1):
                    with st.expander(f"Rule {idx}: {rule['key'][:50]}...", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown("**Rule:**")
                            st.write(f"✓ {rule['value']}")
                            
                            st.caption(f"Created: {rule['created'][:19]}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_rule_{idx}"):
                                delete_memory_item(f"RULE:{st.session_state.user_id}:{rule['key']}")
                                st.rerun()
                
                # Show combined effect
                st.markdown("---")
                st.markdown("### 📝 Combined Effect on Agent")
                st.info("These rules are automatically applied to every conversation:")
                for rule in rules:
                    st.markdown(f"• {rule['value']}")
            
            else:
                st.info("ℹ️ No active rules. Set rules by saying things like:")
                st.markdown("""
                - "Always ask a follow-up question"
                - "Respond in a formal tone"
                - "Be concise and use bullet points"
                - "Act as a financial advisor"
                """)
        
        else:
            st.error("Failed to load rules")
    
    except Exception as e:
        st.error(f"Error loading rules: {str(e)}")
    
    # Add new rule manually
    with st.expander("➕ Add Rule Manually"):
        new_rule = st.text_area(
            "Rule Description",
            placeholder="e.g., Always provide examples when explaining concepts",
            height=100
        )
        
        if st.button("Add Rule"):
            if new_rule:
                try:
                    response = httpx.post(
                        f"{st.session_state.api_url}/memory/set_rule",
                        json={
                            "rule": new_rule,
                            "user_id": st.session_state.user_id
                        },
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        st.success("✅ Rule added!")
                        st.rerun()
                    else:
                        st.error("Failed to add rule")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def render_long_term_memory():
    """Display long-term memories"""
    st.subheader("📚 Long-Term Memory")
    st.markdown("Facts and information stored permanently")
    
    try:
        # Query database for long-term memories
        response = httpx.post(
            f"{st.session_state.api_url}/admin/sql",
            json={
                "query": f"SELECT key, value, created_at, last_used_at FROM memory_kv WHERE key LIKE 'LONG_TERM:{st.session_state.user_id}:%' ORDER BY last_used_at DESC"
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            if rows:
                st.info(f"📊 **{len(rows)} long-term memor{'y' if len(rows) == 1 else 'ies'}**")
                
                for idx, row in enumerate(rows, 1):
                    # Extract key without prefix
                    key_parts = row['key'].split(':', 2)
                    display_key = key_parts[2] if len(key_parts) > 2 else row['key']
                    
                    with st.expander(f"Memory {idx}: {display_key[:50]}...", expanded=idx <= 3):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown("**Stored Information:**")
                            st.write(row['value'])
                            
                            st.caption(f"Created: {row['created_at'][:19]}")
                            st.caption(f"Last used: {row['last_used_at'][:19]}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_lt_{idx}"):
                                delete_memory_item(row['key'])
                                st.rerun()
            
            else:
                st.info("ℹ️ No long-term memories stored yet")
                st.markdown("Long-term memories are created when you say things like:")
                st.markdown("""
                - "Remember my email is john@company.com"
                - "My preferred working hours are 9-5"
                - "I always use format X for dates"
                """)
        
        else:
            st.error("Failed to load memories")
    
    except Exception as e:
        st.error(f"Error loading memories: {str(e)}")


def render_short_term_memory():
    """Display short-term context"""
    st.subheader("💬 Short-Term Context")
    st.markdown("Temporary information for the current session")
    
    try:
        # Query database for short-term memories
        response = httpx.post(
            f"{st.session_state.api_url}/admin/sql",
            json={
                "query": f"SELECT key, value, created_at FROM memory_kv WHERE key LIKE 'SHORT_TERM:{st.session_state.user_id}:%' ORDER BY created_at DESC LIMIT 20"
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            if rows:
                st.info(f"📊 **{len(rows)} short-term context item(s)**")
                
                for idx, row in enumerate(rows, 1):
                    key_parts = row['key'].split(':', 2)
                    display_key = key_parts[2] if len(key_parts) > 2 else row['key']
                    
                    with st.expander(f"{idx}. {display_key[:60]}..."):
                        st.write(row['value'])
                        st.caption(f"Created: {row['created_at'][:19]}")
            
            else:
                st.info("ℹ️ No short-term context")
                st.markdown("Short-term context includes:")
                st.markdown("""
                - Current conversation topics
                - Temporary working data
                - Session-specific information
                """)
        
        else:
            st.error("Failed to load context")
    
    except Exception as e:
        st.error(f"Error loading context: {str(e)}")


def render_system_prompt():
    """Display the current system prompt with rules applied"""
    st.subheader("🔧 Current System Prompt")
    st.markdown("See how your rules modify the agent's behavior")
    
    try:
        # Get rules
        rules_response = httpx.get(
            f"{st.session_state.api_url}/memory/rules/{st.session_state.user_id}",
            timeout=5.0
        )
        
        # Base system prompt
        base_prompt = """You are Self Agent, an intelligent workflow automation assistant.
You help users create, modify, and execute business process flows.

Be helpful, concise, and professional. Explain what you're doing and ask for clarification when needed."""
        
        st.markdown("### 📄 Base System Prompt")
        st.code(base_prompt, language="text")
        
        if rules_response.status_code == 200:
            rules = rules_response.json()
            
            if rules:
                st.markdown("### ➕ Your Custom Rules")
                st.info(f"{len(rules)} rule(s) active")
                
                rules_text = "\n".join([f"- {rule['value']}" for rule in rules])
                st.code(rules_text, language="text")
                
                st.markdown("### 🎯 Combined System Prompt")
                st.markdown("This is what the agent actually uses:")
                
                combined_prompt = f"""{base_prompt}

USER-DEFINED BEHAVIOR RULES:
{rules_text}

Follow these rules in all interactions with this user."""
                
                st.code(combined_prompt, language="text")
                
                st.success("✅ These rules are automatically applied to every conversation")
            
            else:
                st.markdown("### ℹ️ No Custom Rules")
                st.info("The agent uses only the base system prompt. Add rules to customize behavior.")
        
        else:
            st.error("Failed to load rules")
    
    except Exception as e:
        st.error(f"Error loading system prompt: {str(e)}")
    
    # Show how rules affect responses
    with st.expander("💡 How Rules Work"):
        st.markdown("""
        **Rules modify the agent's conversation behavior:**
        
        1. **Without Rules**: Standard professional responses
        2. **With Rule "Always ask follow-up questions"**: Every response includes a question
        3. **With Rule "Respond in bullet points"**: Answers use bullet format
        
        **Rules vs. Workflow Changes:**
        - ✅ Rules: "Always be formal" → Changes conversation style
        - ❌ Not Rules: "Add email step to invoice flow" → Changes workflow structure
        """)


def delete_memory_item(key: str):
    """Delete a memory item"""
    try:
        response = httpx.post(
            f"{st.session_state.api_url}/admin/sql",
            json={
                "query": f"DELETE FROM memory_kv WHERE key = '{key}'"
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            st.success("✅ Deleted successfully")
        else:
            st.error("Failed to delete")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_memory_stats():
    """Display memory statistics"""
    try:
        response = httpx.post(
            f"{st.session_state.api_url}/admin/sql",
            json={
                "query": f"""
                SELECT 
                    CASE 
                        WHEN key LIKE 'SHORT_TERM:%' THEN 'Short-Term'
                        WHEN key LIKE 'LONG_TERM:%' THEN 'Long-Term'
                        WHEN key LIKE 'RULE:%' THEN 'Rules'
                        ELSE 'Other'
                    END as type,
                    COUNT(*) as count
                FROM memory_kv
                WHERE key LIKE '%{st.session_state.user_id}%'
                GROUP BY type
                """
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            if rows:
                col1, col2, col3 = st.columns(3)
                
                for row in rows:
                    if row['type'] == 'Rules':
                        with col1:
                            st.metric("🎯 Rules", row['count'])
                    elif row['type'] == 'Long-Term':
                        with col2:
                            st.metric("📚 Long-Term", row['count'])
                    elif row['type'] == 'Short-Term':
                        with col3:
                            st.metric("💬 Short-Term", row['count'])
    
    except Exception as e:
        pass  # Silent fail for stats
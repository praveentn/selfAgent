# app.py
import streamlit as st
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enterprise look
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 600;
    }
    
    /* Cards */
    .stCard {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
    }
    
    /* Status badges */
    .status-completed {
        background-color: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-running {
        background-color: #f59e0b;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-failed {
        background-color: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-pending {
        background-color: #6b7280;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .chat-user {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
    }
    
    .chat-assistant {
        background-color: #f3f4f6;
        border-left: 4px solid #6b7280;
    }
    
    /* Tables */
    .dataframe {
        border: none !important;
    }
    
    .dataframe td, .dataframe th {
        border: 1px solid #e5e7eb !important;
        padding: 8px !important;
    }
    
    .dataframe th {
        background-color: #f3f4f6 !important;
        font-weight: 600 !important;
        color: #374151 !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title(f"🤖 {Config.APP_NAME}")
st.sidebar.markdown(f"**Version:** {Config.APP_VERSION}")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["💬 Chat", "🔄 Flows", "🔌 Connectors", "📊 Runs", "⚙️ Admin"],
    label_visibility="collapsed"
)

# Initialize session state
if 'api_url' not in st.session_state:
    st.session_state.api_url = f"http://{Config.HOST}:{Config.PORT}"

if 'user_id' not in st.session_state:
    st.session_state.user_id = "default_user"

# Display API status in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")

import httpx
try:
    response = httpx.get(f"{st.session_state.api_url}/", timeout=2.0)
    if response.status_code == 200:
        st.sidebar.success("✅ API Connected")
    else:
        st.sidebar.error("❌ API Error")
except Exception as e:
    st.sidebar.error("❌ API Offline")
    st.sidebar.caption(f"Start API: `python main.py`")

# Page routing
if page == "💬 Chat":
    from pages import chat
    chat.render()
elif page == "🔄 Flows":
    from pages import flows
    flows.render()
elif page == "🔌 Connectors":
    from pages import connectors
    connectors.render()
elif page == "📊 Runs":
    from pages import runs
    runs.render()
elif page == "⚙️ Admin":
    from pages import admin
    admin.render()
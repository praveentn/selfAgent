# Self Agent - AI-Powered Workflow Automation Platform
A self-configuring, agent-aware, tool-aware process automation system that can create, configure, execute, and adapt - through chat

An intelligent, conversational workflow automation system built with Python, Streamlit, FastAPI, and Azure OpenAI.

## 🚀 Features

- **💬 Conversational Interface**: Chat with your workflows using natural language
- **🔄 Process Automation**: Create and execute multi-step business processes
- **🔌 Pluggable Connectors**: Extensible tool integrations (SQL, SharePoint, Email, etc.)
- **🧠 Smart Intent Detection**: Embedding-based + LLM fallback for accurate intent recognition
- **📊 Real-time Monitoring**: Track workflow executions with live status updates
- **🗄️ Semantic Memory**: FAISS-powered vector search for conversations and workflows
- **⚙️ Admin Panel**: SQL executor, system stats, and configuration management

## 📋 Prerequisites

- Python 3.8 or higher
- Azure OpenAI API access
- Windows OS (for batch scripts)

## 🛠️ Installation

1. **Clone or download the project**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Azure OpenAI**
   
   Edit `.env` file and add your Azure OpenAI credentials:
   ```env
   AZURE_OPENAI_ENDPOINT=your_endpoint_here
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   AZURE_OPENAI_DEPLOYMENT=gpt-4.1
   AZURE_OPENAI_MODEL=gpt-4.1
   ```

4. **Initialize database**
   ```bash
   python -c "from database import init_database; init_database()"
   ```

## 🎯 Quick Start

### Option 1: Using Startup Script (Recommended for Windows)

```bash
start.bat
```

This will:
- Install dependencies if needed
- Initialize the database
- Start FastAPI backend (port 7367)
- Launch Streamlit frontend (port 8501)

### Option 2: Manual Start

**Terminal 1 - Start FastAPI Backend:**
```bash
python main.py
```

**Terminal 2 - Start Streamlit Frontend:**
```bash
streamlit run app.py
```

## 📱 Access the Application

- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:7367/docs
- **API Base URL**: http://localhost:7367

## 🏗️ Architecture

```
Self Agent
├── Frontend (Streamlit)
│   ├── Chat Console
│   ├── Flow Manager
│   ├── Connector Manager
│   ├── Run Viewer
│   └── Admin Panel
│
├── Backend (FastAPI)
│   ├── Intent Detector (Embeddings + LLM)
│   ├── Flow Manager (YAML/JSON)
│   ├── Executor
│   ├── Connector Manager
│   ├── Memory Manager
│   └── Conversation Manager
│
├── Storage
│   ├── SQLite (Metadata)
│   ├── FAISS (Vector Search)
│   └── File System (Flow Versions)
│
└── AI Integration
    └── Azure OpenAI (GPT-4.1)
```

## 📚 Usage Guide

### Creating a Flow

1. Navigate to **🔄 Flows** tab
2. Click **➕ Create Flow**
3. Define flow name, description, and steps
4. Click **Create Flow**

### Executing a Flow

1. Go to **🔄 Flows** tab
2. Click **▶️ Execute** next to the desired flow
3. Monitor execution in **📊 Runs** tab

### Chat Interaction

1. Open **💬 Chat** tab
2. Type natural language commands:
   - "Run the invoice flow"
   - "Show me recent execution history"
   - "What connectors are available?"
   - "Create a new workflow for processing invoices"

### SQL Execution (Admin)

1. Navigate to **⚙️ Admin** tab
2. Go to **🗄️ SQL Executor**
3. Enter SQL query
4. Click **Execute Query**
5. View paginated results

## 🔌 Available Connectors

- **SQL**: Database operations (query, insert, update, delete)
- **SharePoint**: File operations (read, write, list)
- **Email**: Send and manage emails
- **Notification**: Send alerts and notifications

## 📊 Database Schema

Key tables:
- `flows` - Workflow definitions
- `flow_versions` - Version history
- `runs` - Execution records
- `run_steps` - Step-level execution logs
- `connectors` - Tool registry
- `conversations` - Chat history
- `memory_kv` - Key-value memory store
- `vector_meta` - Vector search metadata
- `intent_samples` - Intent training data

## 🔧 Configuration

Edit `config.py` to customize:
- Application name and version
- Server host and port
- Database path
- Azure OpenAI settings

## 🧪 API Endpoints

### Core Endpoints
- `POST /intent` - Detect user intent
- `POST /flows` - Create flow
- `GET /flows` - List all flows
- `GET /flows/{id}` - Get flow details
- `POST /flows/{id}/execute` - Execute flow
- `GET /runs/{id}` - Get run status
- `POST /flows/{id}/modify` - Modify flow
- `POST /admin/sql` - Execute SQL query

### Connector Endpoints
- `GET /connectors` - List connectors
- `POST /connectors/test` - Test connector

### Memory Endpoints
- `POST /index/text` - Index text for search
- `POST /query/semantic` - Semantic search

## 📝 Example Flow (YAML)

```yaml
name: Invoice Processing
description: Process invoices from SharePoint
version: 1
steps:
  - id: step_1
    name: Read Invoice
    type: sharepoint
    connector: sharepoint
    action: read_file
    params:
      filename: invoice.xlsx
  
  - id: step_2
    name: Save to Database
    type: sql
    connector: sql
    action: insert
    params:
      table: invoices
  
  - id: step_3
    name: Send Notification
    type: email
    connector: email
    action: send
    params:
      to: finance@company.com
      subject: Invoice Processed
```

## 🛡️ Security Notes

- Authentication is parked for MVP
- Store API keys securely in `.env`
- Do not commit `.env` to version control
- Admin SQL executor has full database access

## 🐛 Troubleshooting

### API Connection Failed
- Ensure FastAPI is running: `python main.py`
- Check port 7367 is not in use
- Verify API URL in Streamlit app

### Database Errors
- Reinitialize database: `python -c "from database import init_database; init_database()"`
- Check file permissions on `selfagent.db`

### FAISS Index Issues
- Rebuild index via Admin panel
- Delete `faiss_index` folder and restart

## 📦 Project Structure

```
self-agent/
├── app.py                  # Streamlit entry point
├── main.py                 # FastAPI server
├── config.py               # Configuration
├── database.py             # Database models
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── start.bat              # Windows startup script
├── components/            # Backend components
│   ├── azure_client.py
│   ├── intent_detector.py
│   ├── flow_manager.py
│   ├── executor.py
│   ├── connector_manager.py
│   ├── memory_manager.py
│   └── vector_indexer.py
├── pages/                 # Streamlit pages
│   ├── chat.py
│   ├── flows.py
│   ├── connectors.py
│   ├── runs.py
│   └── admin.py
└── flows/                 # Flow version storage
```

## 🤝 Contributing

This is an MVP implementation. Future enhancements:
- User authentication & authorization
- Multi-tenant support
- Advanced connector library
- Workflow scheduling
- Real-time collaboration
- Enhanced error recovery

## 📄 License

Internal use only - Commercial deployment requires proper licensing

## 🙋 Support

For issues or questions:
1. Check the Admin panel for system stats
2. Review logs in console output
3. Test API endpoints via `/docs`
4. Verify database schema via SQL executor

---

**Version**: 1.0.0  
**Built with**: Python, Streamlit, FastAPI, SQLite, FAISS, Azure OpenAI
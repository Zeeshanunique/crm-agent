# 🤖 Ralph - CRM Web Interface

A beautiful, modern web interface for interacting with Ralph, your CRM Marketing Assistant.

## ✨ Features

- **💬 Interactive Chat**: Natural conversation with Ralph about your customers and campaigns
- **🎯 Smart Suggestions**: Pre-built query suggestions to get you started
- **⚡ Real-time Streaming**: See Ralph's responses as they're generated
- **🛡️ Human-in-the-Loop**: Approval workflow for sensitive actions like sending campaigns
- **📊 Session Management**: Track your conversation history and statistics
- **🚀 YOLO Mode**: Option to skip approval for faster interactions
- **📱 Responsive Design**: Works on desktop, tablet, and mobile

## 🚀 Quick Start

### Option 1: Use the startup script (Recommended)
```bash
# From the project root
uv run python start_web.py
```

### Option 2: Run directly
```bash
# Install dependencies
uv sync

# Start the web interface
cd frontend
uv run streamlit run web_chat.py
```

The interface will open automatically in your browser at `http://localhost:8501`

## 🎯 How to Use

1. **Start a Conversation**: Type your question in the chat input
2. **Try Suggestions**: Click on the sample queries in the sidebar
3. **Approve Actions**: When Ralph needs to send emails or create campaigns, you'll see an approval prompt
4. **Explore Features**: Use the sidebar to toggle YOLO mode or clear chat history

## 💡 Sample Queries

Try these to get started:
- "Show me our top 5 customers by spending"
- "How many customers are in each RFM segment?"
- "Create a loyalty campaign for champions"
- "Analyze customer purchase patterns"
- "Send re-engagement emails to at-risk customers"

## 🔧 Configuration

Make sure you have these environment variables set in your `.env` file:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URI`: Your Supabase database connection string
- `SLACK_BOT_TOKEN` (optional): For Slack integration
- `SLACK_TEAM_ID` (optional): For Slack integration

## 🎨 Interface Overview

### Main Chat Area
- **Chat History**: See all your conversations with Ralph
- **Message Input**: Type your questions and requests
- **Tool Calls**: See when Ralph is using tools (database queries, etc.)
- **Approval Workflow**: Review and approve sensitive actions

### Sidebar
- **Settings**: Toggle YOLO mode and other preferences
- **Capabilities**: Overview of what Ralph can do
- **Sample Queries**: Quick-start suggestions
- **Session Stats**: Track your conversation metrics

### Quick Actions Panel
- **Analytics**: Quick access to customer analytics
- **Campaigns**: View and manage marketing campaigns
- **Customers**: Browse customer database
- **Revenue**: Revenue and performance metrics

## 🛠️ Technical Details

- **Framework**: Streamlit for the web interface
- **Backend**: LangGraph agent with OpenAI GPT-4
- **Database**: PostgreSQL via Supabase
- **Real-time**: Async streaming for live responses
- **Responsive**: Mobile-friendly design

## 🔐 Security

- Human approval required for sensitive actions (campaigns, emails)
- All database queries are read-only unless explicitly approved
- YOLO mode can be toggled for faster interactions when needed

## 🎯 Next Steps

- Explore Ralph's capabilities with the sample queries
- Set up your database and environment variables
- Try creating marketing campaigns and analyzing customer data
- Customize the interface by modifying `web_chat.py`

Happy chatting with Ralph! 🤖✨ 
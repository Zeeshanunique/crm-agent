# Ralph CRM Assistant GUI

A simple, minimalist web interface for the Ralph CRM Assistant.

## 🚀 Quick Start

### 1. Start the GUI
```bash
uv run python start_gui.py
```

The GUI will automatically open in your web browser at `http://localhost:8501`

### 2. Alternative: Direct Streamlit Command
```bash
uv run streamlit run frontend/chat_gui.py
```

## 🎯 Features

### 💬 Chat Interface
- Clean, intuitive chat interface similar to ChatGPT
- Real-time message streaming
- Conversation history maintained during session

### ⚙️ Settings Panel (Sidebar)
- **YOLO Mode**: Toggle to skip human approval for protected operations
- **Reset Conversation**: Clear chat history and start fresh
- **Initialize Ralph**: Manually reinitialize the agent if needed

### 🔍 Human Approval Workflow
When Ralph needs approval for sensitive operations (like sending marketing emails), you'll see:
- **Tool Call Details**: JSON view of what Ralph wants to do
- **Three Options**:
  - ✅ **Continue**: Proceed with the action as-is
  - ✏️ **Update**: Modify the parameters before proceeding
  - 💬 **Feedback**: Provide feedback to Ralph about why not to proceed

## 🛠️ Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Backend**: LangGraph agent with MCP server connections
- **State Management**: Streamlit session state for conversation persistence

### Key Components
- **Chat Interface**: Displays conversation history
- **Input Field**: Bottom-positioned input for new messages
- **Approval System**: Modal dialogs for human-in-the-loop workflows
- **Error Handling**: Graceful error display and recovery

## 🔧 Troubleshooting

### Common Issues

1. **"Configuration error: Missing 'transport' key"**
   - Ensure your MCP configuration in `src/ralph/my_mcp/mcp_config.json` is correct
   - Check that all required environment variables are set in `.env`

2. **Import errors**
   - Make sure you've run `uv sync` to install dependencies
   - Verify the `src/ralph` module is accessible

3. **Database connection issues**
   - Check your `SUPABASE_URI` in the `.env` file
   - Ensure your database is running and accessible

### Environment Variables Required
Create a `.env` file in the project root with:
```env
SUPABASE_URI=your_database_connection_string
SLACK_BOT_TOKEN=your_slack_bot_token  # Optional
SLACK_TEAM_ID=your_slack_team_id      # Optional
OPENAI_API_KEY=your_openai_api_key
```

## 🎨 Interface Overview

```
┌─────────────────────────────────────────────────────┐
│ 🤖 Ralph - CRM Assistant                           │
│ Your customer service agent and marketing expert    │
├─────────────────────────────────────────────────────┤
│ Settings          │ 💬 Chat                        │
│ □ YOLO Mode       │                                │
│ 🔄 Reset          │ 🤖: Hello! I'm Ralph...        │
│ 🏠 Initialize     │                                │
│                   │ 👤: Help me with...            │
│                   │                                │
│                   │ 🤖: I can help you...          │
│                   │                                │
│                   │ ┌─────────────────────────────┐ │
│                   │ │ Type your message here...   │ │
│                   │ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 🔄 Comparison with CLI Version

| Feature | CLI | GUI |
|---------|-----|-----|
| Chat Interface | Text-based terminal | Web-based chat UI |
| Message History | Session only | Visual history with styling |
| Approval Workflow | Text prompts | Interactive buttons & forms |
| Tool Call Display | Plain text | Formatted JSON with syntax highlighting |
| Accessibility | Terminal required | Any web browser |
| Multi-session | Single session | Multiple browser tabs |

## 🚀 Getting Started Tips

1. **First Run**: Click "Initialize Ralph" in the sidebar when you first start
2. **Test Connection**: Ask Ralph "What can you help me with?" to verify everything works
3. **Explore Features**: Try asking Ralph to analyze customer data or create marketing campaigns
4. **Approval Testing**: Disable YOLO mode to see the approval workflow in action

The GUI provides the same powerful CRM functionality as the command-line version but with a more user-friendly interface perfect for daily use. 
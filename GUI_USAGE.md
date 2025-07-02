# Ralph CRM GUI Usage Guide

## 🚀 Quick Start

### Available Interfaces

Ralph CRM offers multiple GUI options to suit your needs:

#### 1. **Clean Interface** (Recommended) 🧹
**File**: `frontend/chat_gui_clean.py`
**Startup**: `python start_clean_gui.py`

**Features:**
- ✅ **No formatting artifacts** - Clean, readable responses
- ✅ **Error separation** - Errors appear in proper warning boxes
- ✅ **Professional data tables** - Real DataFrames with search/filter/download
- ✅ **Clean tool call display** - Beautiful gradient headers
- ✅ **Monetary formatting** - Proper currency display ($11,025.24)

#### 2. **Optimized Interface** 📊
**File**: `frontend/chat_gui_optimized.py`
**Startup**: `python start_gui.py`

**Features:**
- Enhanced content parsing
- Data table visualization
- Professional styling
- Approval workflow

#### 3. **Final Interface** 🎯
**File**: `frontend/chat_gui_final.py`

**Features:**
- Complete feature set
- Advanced formatting
- Rich UI components

#### 4. **Basic Interface** 🔧
**File**: `frontend/chat_gui.py`
**Startup**: `uv run streamlit run frontend/chat_gui.py`

**Features:**
- Simple chat interface
- Basic functionality
- Development version

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- UV package manager
- Streamlit

### Install Dependencies
```bash
uv sync
```

### Start the Interface

#### Method 1: Use Startup Scripts (Recommended)
```bash
# Clean interface (best formatting)
python start_clean_gui.py

# Original optimized interface
python start_gui.py
```

#### Method 2: Direct Streamlit Command
```bash
# Clean version
uv run streamlit run frontend/chat_gui_clean.py

# Optimized version
uv run streamlit run frontend/chat_gui_optimized.py

# Basic version
uv run streamlit run frontend/chat_gui.py
```

## 🖥️ Interface Overview

### Main Components

1. **Header**: Beautiful gradient header with title and description
2. **Chat Area**: Clean conversation display with proper message formatting
3. **Sidebar**: Settings and controls panel
4. **Input Area**: Message input with placeholder text

### Sidebar Features

- ⚙️ **Settings Panel**
  - YOLO Mode toggle (skip human approval)
  - Session status indicators
  
- 🎮 **Quick Actions**
  - Reset conversation
  - Initialize Ralph
  - Test connection
  
- 💡 **Sample Queries**
  - Pre-written example questions
  - Copy-paste ready queries

## 💬 Using the Chat Interface

### Getting Started

1. **Initialize Ralph**: Click "🚀 Initialize Ralph" in the sidebar
2. **Start Chatting**: Type your question in the input box
3. **Review Responses**: Clean, formatted responses with proper data tables

### Sample Queries

```
Data Analysis:
- "Show me our top 5 customers by total spending"
- "What are our customer segments based on RFM analysis?"
- "Who are our at-risk customers?"

Campaign Management:
- "Create a loyalty program for high-value customers"
- "Draft an email campaign for customer retention"
- "Analyze customer purchase patterns"

Insights:
- "What's our customer lifetime value?"
- "Which products are most popular?"
- "Show me seasonal purchase trends"
```

## 🔧 Settings & Configuration

### YOLO Mode
- **OFF** (Default): Human approval required for sensitive operations
- **ON**: Automatic execution of all operations

### Session Management
- **Reset Chat**: Clear conversation history
- **Initialize Ralph**: Restart the AI agent
- **Test Connection**: Verify system status

## 📊 Data Visualization Features

### Table Display
- **Professional DataFrames**: Clean, searchable data tables
- **Column Controls**: Show/hide, sort, filter columns
- **Download Options**: Export data as CSV
- **Monetary Formatting**: Automatic currency formatting

### Content Formatting
- **Tool Call Headers**: Beautiful blue gradient headers
- **SQL Query Display**: Syntax-highlighted SQL code
- **Error Handling**: Clean error messages in warning boxes
- **Text Cleaning**: No formatting artifacts or JSON remnants

## 🎯 Best Practices

### For Best Results:
1. **Use Specific Questions**: "Show top 5 customers by spending" vs. "show customers"
2. **One Question at a Time**: Avoid complex multi-part queries
3. **Review Approvals**: Check tool calls before approving (when YOLO mode is off)
4. **Download Data**: Use CSV export for further analysis

### Query Tips:
- Be specific about metrics (spending, frequency, recency)
- Use time frames when relevant ("last month", "this year")
- Ask for actionable insights ("recommend actions", "suggest campaigns")

## 🐛 Troubleshooting

### Common Issues:

#### "Ralph not initialized"
- **Solution**: Click "🚀 Initialize Ralph" in sidebar
- **Cause**: Graph not loaded on startup

#### "Page not loading"
- **Solution**: Check if port 8501 is available
- **Alternative**: Use different port with `--server.port 8502`

#### "Import errors"
- **Solution**: Run `uv sync` to install dependencies
- **Check**: Ensure you're in the project root directory

#### "Formatting artifacts"
- **Solution**: Use the Clean Interface (`chat_gui_clean.py`)
- **Features**: Specifically designed to eliminate formatting issues

### Getting Help:
1. Check the terminal for error messages
2. Restart the interface
3. Clear browser cache
4. Verify all dependencies are installed

## 🚀 Performance Tips

### For Faster Response:
- Use YOLO mode for testing (skip approvals)
- Keep queries focused and specific
- Reset session if it becomes slow
- Use the Clean interface for best performance

### Data Handling:
- Download large datasets as CSV
- Use table filters for big results
- Clear conversation history periodically

## 🎨 Customization

The interfaces are built with Streamlit and can be customized:
- Modify CSS styling in the `st.markdown()` sections
- Adjust colors in the gradient headers
- Add new sidebar components
- Customize data table formatting

---

**Need Help?** The Clean Interface (`chat_gui_clean.py`) provides the best user experience with proper error handling and clean data presentation. Start there for optimal results! 
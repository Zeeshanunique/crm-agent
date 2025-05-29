# 🤖 CRM Agent Tutorial - Ralph the Marketing AI

Welcome to the **CRM Agent Tutorial**! This project demonstrates how to build an intelligent Customer Relationship Management (CRM) system using AI agents, LangGraph, and real customer data. Meet **Ralph** - your AI-powered marketing assistant who can analyze customer behavior and create personalized marketing campaigns.

## 🎯 What You'll Learn

- Build an AI agent using **LangGraph** and **OpenAI GPT-4**
- Implement **human-in-the-loop** workflows for sensitive operations
- Create **RFM (Recency, Frequency, Monetary) analysis** for customer segmentation
- Design **personalized marketing campaigns** using AI
- Integrate **PostgreSQL** with AI agents for real-time data analysis
- Use **Model Context Protocol (MCP)** for tool integration

## 🏗️ Project Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Ralph Agent   │    │   Database      │
│   (Chat UI)     │◄──►│   (LangGraph)   │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  MCP Marketing  │
                       │     Server      │
                       └─────────────────┘
```

## 🚀 Features

- **🧠 Intelligent Customer Analysis**: Ralph analyzes customer purchase history and behavior patterns
- **📧 Personalized Email Campaigns**: Creates targeted marketing emails with customer-specific content
- **🎯 Customer Segmentation**: Uses RFM analysis to categorize customers (Champions, At Risk, etc.)
- **✋ Human Approval**: Requires human review for sensitive actions like sending campaigns
- **📊 Real-time Data**: Works with actual retail transaction data
- **🔄 Campaign Types**:
  - **Re-engagement**: Win back inactive customers
  - **Referral**: Leverage high-value customers for referrals
  - **Loyalty**: Thank and retain valuable customers

## ⚡ Quick Start

Want to get started immediately? Here's the fastest path:

1. **Clone and setup**:
   ```bash
   git clone <your-repo-url>
   cd crm-agent
   curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
   uv sync  # Install dependencies
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and Supabase URI
   ```

3. **Setup database** (create free Supabase account at [supabase.com](https://supabase.com)):
   ```bash
   psql "your-supabase-connection-string" -f db/migration-create-tables.sql
   uv run python db/generate_data_tables.py
   ```

4. **Verify and run**:
   ```bash
   uv run python verify_setup.py  # Check everything works
   cd frontend && uv run python chat_local.py  # Start chatting with Ralph!
   ```

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.13+** installed
- **PostgreSQL** database (we'll use Supabase)
- **OpenAI API key**
- **Git** for cloning the repository

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd crm-agent
```

### 2. Install Dependencies

This project uses `uv` for dependency management. If you don't have `uv` installed:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

Alternatively, you can use pip:

```bash
pip install -e .
```

### 3. Database Setup (Supabase)

#### Option A: Use Supabase (Recommended)

1. **Create a Supabase account** at [supabase.com](https://supabase.com)

2. **Create a new project**:
   - Go to your Supabase dashboard
   - Click "New Project"
   - Choose a name and password
   - Wait for the project to be ready

3. **Get your database URL**:
   - Go to Project Settings → Database
   - Copy the "Connection string" (URI format)
   - It should look like: `postgresql://postgres:[password]@[host]:5432/postgres`

4. **Run the database migration**:
   ```bash
   # Connect to your Supabase database and run the migration
   psql "your-supabase-connection-string" -f db/migration-create-tables.sql
   ```

5. **Load sample data**:
   ```bash
   # Activate your virtual environment first
   uv run python db/generate_data_tables.py
   ```

#### Option B: Local PostgreSQL

If you prefer to use a local PostgreSQL instance:

```bash
# Install PostgreSQL (macOS)
brew install postgresql
brew services start postgresql

# Create database
createdb crm_agent

# Run migration
psql crm_agent -f db/migration-create-tables.sql

# Load sample data
uv run python db/generate_data_tables.py
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# Database Connection (required)
SUPABASE_URI=postgresql://postgres:[password]@[host]:5432/postgres

# Optional: Adjust model settings
OPENAI_MODEL=gpt-4o-mini-2024-07-18
```

### 5. Verify Setup

We've included a handy verification script to test your installation:

```bash
# Run the setup verification script
uv run python verify_setup.py
```

This script will check:
- ✅ Environment variables are configured
- ✅ Database connection is working
- ✅ Required tables exist and have data
- ✅ OpenAI API is accessible
- ✅ All Python dependencies are installed

If all checks pass, you're ready to go! If not, the script will tell you exactly what needs to be fixed.

## 🎮 Running the Application

### Start the Chat Interface

```bash
cd frontend
uv run python chat_local.py
```

You should see Ralph introduce himself:

```
---- 🤖 Assistant ----

Hi there! I'm Ralph, your customer service agent and marketing expert. I'm here to help you understand your customers better and create targeted marketing campaigns that drive results.

I have access to your CRM database with customer information, transaction history, and RFM analysis. I can help you:

🎯 Analyze customer behavior and segments
📧 Create personalized marketing campaigns
📊 Generate insights from your customer data
✉️ Send targeted emails to specific customer groups

What would you like to work on today?
```

### Example Interactions

Try these commands to see Ralph in action:

1. **Customer Analysis**:
   ```
   "Show me our top 5 customers by total spending"
   ```

2. **Segment Analysis**:
   ```
   "How many customers do we have in each RFM segment?"
   ```

3. **Create a Campaign**:
   ```
   "Create a re-engagement campaign for customers who haven't purchased in the last 6 months"
   ```

4. **Send Personalized Emails**:
   ```
   "Send a loyalty email to our champion customers thanking them for their business"
   ```

## 📊 Understanding the Data

### Customer Segments (RFM Analysis)

Ralph uses RFM analysis to categorize customers:

- **🏆 Champions** (555): Best customers - high recency, frequency, and monetary value
- **🆕 Recent Customers** (5XX): Recently active customers
- **🔄 Frequent Buyers** (X5X): Customers who buy often
- **💰 Big Spenders** (XX5): High-value customers
- **⚠️ At Risk** (1XX): Haven't purchased recently
- **👥 Others**: Everyone else

### Database Schema

The project includes these main tables:

- **customers**: Customer information and contact details
- **transactions**: Purchase history and transaction data
- **items**: Product catalog with descriptions and prices
- **rfm**: Customer segmentation scores
- **marketing_campaigns**: Campaign tracking
- **campaign_emails**: Email delivery and engagement tracking

## 🔧 Customization

### Adding New Campaign Types

Edit `src/ralph/prompts.py` to add new campaign types:

```python
# Add to the MARKETING_CAMPAIGNS section
4. seasonal: Send emails about seasonal promotions and offers
```

Then update the database constraint in `db/migration-create-tables.sql`.

### Modifying Ralph's Personality

Customize Ralph's behavior by editing the system prompt in `src/ralph/prompts.py`:

```python
ralph_system_prompt = f"""You are Ralph, a [your custom personality here]...
```

### Adding New Tools

Create new MCP tools in `src/ralph/mymcp/servers/marketing_server.py`:

```python
@mcp.tool()
async def your_new_tool(param: str) -> str:
    """Your tool description."""
    # Your implementation here
    return "Tool result"
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**:
   ```
   Error: could not connect to server
   ```
   - Verify your `SUPABASE_URI` in `.env`
   - Check if your Supabase project is running
   - Ensure your IP is allowed in Supabase settings

2. **OpenAI API Error**:
   ```
   Error: Incorrect API key provided
   ```
   - Verify your `OPENAI_API_KEY` in `.env`
   - Check your OpenAI account has credits
   - Ensure the API key has the correct permissions

3. **Import Errors**:
   ```
   ModuleNotFoundError: No module named 'ralph'
   ```
   - Run `uv sync` to install dependencies
   - Ensure you're in the correct directory
   - Try `pip install -e .` as an alternative

4. **Human Approval Not Working**:
   - Make sure you're responding with exactly: `continue`, `update`, or `feedback`
   - Check that protected tools are properly configured in `graph.py`

### Getting Help

If you encounter issues:

1. Check the [Issues](link-to-issues) section
2. Review the troubleshooting section above
3. Ensure all prerequisites are installed correctly
4. Verify your environment variables are set properly

## 📚 Learning Resources

### Key Concepts Covered

- **LangGraph**: Framework for building stateful AI agents
- **MCP (Model Context Protocol)**: Standard for AI tool integration
- **RFM Analysis**: Customer segmentation methodology
- **Human-in-the-loop**: AI systems with human oversight
- **PostgreSQL**: Relational database for customer data

### Recommended Reading

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [RFM Analysis Guide](https://en.wikipedia.org/wiki/RFM_(market_research))
- [OpenAI API Documentation](https://platform.openai.com/docs)

## 🤝 Contributing

This is a tutorial project, but contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain/LangGraph** team for the amazing AI framework
- **OpenAI** for the powerful language models
- **Supabase** for the excellent PostgreSQL hosting
- **UCI Machine Learning Repository** for the retail dataset

---

**Happy Learning! 🚀**

If you found this tutorial helpful, please ⭐ star the repository and subscribe to the YouTube channel for more AI tutorials!
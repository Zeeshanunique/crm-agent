import streamlit as st
import sys
import os
import asyncio
import json
from typing import AsyncGenerator, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ralph.graph import build_graph, AgentState
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.types import Command

# Page configuration
st.set_page_config(
    page_title="Ralph - CRM Marketing Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        text-align: center;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        max-width: 80%;
    }
    
    .user-message {
        background-color: #f0f2f6;
        margin-left: auto;
        border-left: 4px solid #667eea;
    }
    
    .assistant-message {
        background-color: #e8f4f8;
        margin-right: auto;
        border-left: 4px solid #52c41a;
    }
    
    .tool-call {
        background-color: #fff7e6;
        border-left: 4px solid #faad14;
        font-family: monospace;
        font-size: 0.9em;
    }
    
    .approval-needed {
        background-color: #fff2f0;
        border-left: 4px solid #ff4d4f;
        border: 2px dashed #ff4d4f;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .feature-badge {
        background-color: #e6f7ff;
        color: #1890ff;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

async def stream_graph_responses(
    input_data: dict[str, Any],
    graph,
    **kwargs
) -> AsyncGenerator[tuple[str, str], None]:
    """Stream responses from the graph with message type classification."""
    async for message_chunk, metadata in graph.astream(
        input=input_data,
        stream_mode="messages",
        **kwargs
    ):
        if isinstance(message_chunk, AIMessageChunk):
            if message_chunk.response_metadata:
                finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                if finish_reason == "tool_calls":
                    yield ("separator", "\n\n")

            if message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]
                tool_name = tool_chunk.get("name", "")
                args = tool_chunk.get("args", "")

                if tool_name:
                    yield ("tool_call", f"🔧 **Tool Call:** {tool_name}")
                if args:
                    yield ("tool_args", f"```json\n{args}\n```")
            else:
                if message_chunk.content:
                    yield ("assistant", message_chunk.content)

def initialize_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'graph' not in st.session_state:
        st.session_state.graph = None
    if 'config' not in st.session_state:
        st.session_state.config = {
            "configurable": {
                "thread_id": "streamlit_session"
            }
        }
    if 'awaiting_approval' not in st.session_state:
        st.session_state.awaiting_approval = False
    if 'current_interrupt' not in st.session_state:
        st.session_state.current_interrupt = None
    if 'yolo_mode' not in st.session_state:
        st.session_state.yolo_mode = False

async def initialize_graph():
    """Initialize the graph if not already done."""
    if st.session_state.graph is None:
        with st.spinner("🤖 Initializing Ralph..."):
            st.session_state.graph = await build_graph()
        st.success("✅ Ralph is ready!")

def display_message(message_type: str, content: str):
    """Display a message with appropriate styling."""
    if message_type == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 You:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif message_type == "assistant":
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Ralph:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif message_type == "tool_call":
        st.markdown(f"""
        <div class="chat-message tool-call">
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif message_type == "tool_args":
        st.markdown(f"""
        <div class="chat-message tool-call">
            {content}
        </div>
        """, unsafe_allow_html=True)

async def handle_user_input(user_input: str):
    """Handle user input and get response from Ralph."""
    # Add user message to chat
    st.session_state.messages.append(("user", user_input))
    
    # Create graph input
    graph_input = AgentState(
        messages=[HumanMessage(content=user_input)],
        yolo_mode=st.session_state.yolo_mode
    )
    
    # Get response from Ralph
    response_placeholder = st.empty()
    current_response = ""
    
    async for message_type, content in stream_graph_responses(
        graph_input, 
        st.session_state.graph, 
        config=st.session_state.config
    ):
        if message_type == "assistant":
            current_response += content
            response_placeholder.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Ralph:</strong><br>
                {current_response}
            </div>
            """, unsafe_allow_html=True)
        elif message_type in ["tool_call", "tool_args"]:
            st.session_state.messages.append((message_type, content))
    
    if current_response:
        st.session_state.messages.append(("assistant", current_response))
    
    # Check for interrupts
    thread_state = st.session_state.graph.get_state(config=st.session_state.config)
    if thread_state.interrupts:
        st.session_state.awaiting_approval = True
        st.session_state.current_interrupt = thread_state.interrupts[0]
        st.rerun()

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Ralph - Your CRM Marketing Assistant</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Settings")
        
        # YOLO Mode toggle
        yolo_mode = st.toggle(
            "🚀 YOLO Mode", 
            value=st.session_state.yolo_mode,
            help="Skip human approval for protected actions"
        )
        st.session_state.yolo_mode = yolo_mode
        
        st.markdown("---")
        
        # Ralph's capabilities
        st.markdown("### 🎯 Ralph's Capabilities")
        st.markdown("""
        <div class="sidebar-section">
            <span class="feature-badge">📊 Customer Analysis</span>
            <span class="feature-badge">📧 Email Campaigns</span>
            <span class="feature-badge">🎯 Customer Segmentation</span>
            <span class="feature-badge">📈 RFM Analysis</span>
            <span class="feature-badge">💼 Campaign Management</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Sample queries
        st.markdown("### 💡 Try These Queries")
        sample_queries = [
            "Show me our top 5 customers by spending",
            "How many customers are in each RFM segment?",
            "Create a loyalty campaign for champions",
            "Analyze customer purchase patterns",
            "Send re-engagement emails to at-risk customers"
        ]
        
        for query in sample_queries:
            if st.button(f"💬 {query}", key=f"sample_{hash(query)}", use_container_width=True):
                st.session_state.sample_query = query
                st.rerun()
        
        st.markdown("---")
        
        # Statistics
        st.markdown("### 📊 Session Stats")
        total_messages = len([m for m in st.session_state.messages if m[0] in ["user", "assistant"]])
        st.metric("Messages", total_messages)
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Main chat area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Initialize graph
        if st.session_state.graph is None:
            asyncio.run(initialize_graph())
        
        # Handle approval workflow
        if st.session_state.awaiting_approval and st.session_state.current_interrupt:
            st.markdown("""
            <div class="chat-message approval-needed">
                <strong>⚠️ Human Approval Required</strong>
            </div>
            """, unsafe_allow_html=True)
            
            interrupt_data = st.session_state.current_interrupt.value
            st.json(interrupt_data)
            
            col_approve, col_update, col_feedback = st.columns(3)
            
            with col_approve:
                if st.button("✅ Continue", use_container_width=True):
                    asyncio.run(handle_approval("continue", None))
            
            with col_update:
                if st.button("✏️ Update", use_container_width=True):
                    st.session_state.show_update_form = True
                    st.rerun()
            
            with col_feedback:
                if st.button("💬 Feedback", use_container_width=True):
                    st.session_state.show_feedback_form = True
                    st.rerun()
            
            # Update form
            if st.session_state.get('show_update_form', False):
                update_data = st.text_area("Enter updated JSON data:")
                if st.button("Submit Update"):
                    asyncio.run(handle_approval("update", update_data))
            
            # Feedback form
            if st.session_state.get('show_feedback_form', False):
                feedback_data = st.text_area("Enter feedback:")
                if st.button("Submit Feedback"):
                    asyncio.run(handle_approval("feedback", feedback_data))
        
        # Display chat messages
        st.markdown("### 💬 Chat History")
        for message_type, content in st.session_state.messages:
            display_message(message_type, content)
        
        # Chat input
        if not st.session_state.awaiting_approval:
            # Handle sample query
            if 'sample_query' in st.session_state:
                user_input = st.session_state.sample_query
                del st.session_state.sample_query
                asyncio.run(handle_user_input(user_input))
                st.rerun()
            
            # Regular chat input
            with st.form("chat_form", clear_on_submit=True):
                user_input = st.text_input(
                    "💬 Ask Ralph anything about your customers or marketing campaigns:",
                    placeholder="e.g., Show me our champion customers or Create a loyalty campaign"
                )
                submit_button = st.form_submit_button("Send 🚀", use_container_width=True)
                
                if submit_button and user_input:
                    asyncio.run(handle_user_input(user_input))
                    st.rerun()
        else:
            st.info("⏳ Waiting for your approval to continue...")
    
    with col2:
        st.markdown("### 🎯 Quick Actions")
        
        quick_actions = [
            ("📊", "Analytics", "Show customer analytics dashboard"),
            ("📧", "Campaigns", "View active marketing campaigns"),
            ("👥", "Customers", "Browse customer database"),
            ("💰", "Revenue", "Show revenue metrics"),
        ]
        
        for icon, title, desc in quick_actions:
            with st.container():
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{icon} {title}</h4>
                    <p style="font-size: 0.9em; color: #666;">{desc}</p>
                </div>
                """, unsafe_allow_html=True)

async def handle_approval(action: str, data: str):
    """Handle approval workflow."""
    command_data = {"action": action}
    if data:
        command_data["data"] = data
    
    # Send resume command
    response_placeholder = st.empty()
    current_response = ""
    
    async for message_type, content in stream_graph_responses(
        Command(resume=command_data),
        st.session_state.graph,
        config=st.session_state.config
    ):
        if message_type == "assistant":
            current_response += content
            response_placeholder.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Ralph:</strong><br>
                {current_response}
            </div>
            """, unsafe_allow_html=True)
    
    if current_response:
        st.session_state.messages.append(("assistant", current_response))
    
    # Reset approval state
    st.session_state.awaiting_approval = False
    st.session_state.current_interrupt = None
    st.session_state.show_update_form = False
    st.session_state.show_feedback_form = False
    
    st.rerun()

if __name__ == "__main__":
    main() 
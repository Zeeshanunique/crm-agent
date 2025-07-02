import streamlit as st
import sys
import os
import asyncio
from typing import AsyncGenerator, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ralph.graph import build_graph, AgentState
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.types import Command

# Page configuration
st.set_page_config(
    page_title="Ralph CRM Chat",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Simple CSS
st.markdown("""
<style>
    .main {
        max-width: 800px;
        padding: 2rem 1rem;
    }
    
    .chat-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
        max-width: 85%;
    }
    
    .user-message {
        background-color: #e3f2fd;
        margin-left: auto;
        text-align: right;
    }
    
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: auto;
    }
    
    .tool-message {
        background-color: #fff3e0;
        font-family: monospace;
        font-size: 0.9em;
    }
    
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
    
    .stButton > button {
        border-radius: 20px;
        background-color: #1976d2;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'graph' not in st.session_state:
        st.session_state.graph = None
    if 'config' not in st.session_state:
        st.session_state.config = {"configurable": {"thread_id": "simple_chat"}}
    if 'awaiting_approval' not in st.session_state:
        st.session_state.awaiting_approval = False
    if 'current_interrupt' not in st.session_state:
        st.session_state.current_interrupt = None

async def initialize_graph():
    """Initialize the graph."""
    if st.session_state.graph is None:
        with st.spinner("🤖 Initializing Ralph..."):
            st.session_state.graph = await build_graph()

async def stream_graph_responses(input_data, graph, **kwargs) -> AsyncGenerator[tuple[str, str], None]:
    """Stream responses from the graph."""
    async for message_chunk, metadata in graph.astream(
        input=input_data, stream_mode="messages", **kwargs
    ):
        if isinstance(message_chunk, AIMessageChunk):
            if message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]
                tool_name = tool_chunk.get("name", "")
                if tool_name:
                    yield ("tool", f"🔧 Using tool: {tool_name}")
            else:
                if message_chunk.content:
                    yield ("assistant", message_chunk.content)

def display_messages():
    """Display all chat messages."""
    for msg_type, content in st.session_state.messages:
        if msg_type == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)
        elif msg_type == "assistant":
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Ralph:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)
        elif msg_type == "tool":
            st.markdown(f"""
            <div class="chat-message tool-message">
                {content}
            </div>
            """, unsafe_allow_html=True)

async def handle_user_input(user_input: str):
    """Handle user input and get response."""
    # Add user message
    st.session_state.messages.append(("user", user_input))
    
    # Create graph input
    graph_input = AgentState(
        messages=[HumanMessage(content=user_input)],
        yolo_mode=True  # Simplified - no approval workflow
    )
    
    # Stream response
    response_container = st.empty()
    current_response = ""
    
    async for msg_type, content in stream_graph_responses(
        graph_input, st.session_state.graph, config=st.session_state.config
    ):
        if msg_type == "assistant":
            current_response += content
            response_container.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Ralph:</strong><br>{current_response}
            </div>
            """, unsafe_allow_html=True)
        elif msg_type == "tool":
            st.session_state.messages.append((msg_type, content))
    
    if current_response:
        st.session_state.messages.append(("assistant", current_response))

def main():
    # Header
    st.markdown("""
    <div class="chat-header">
        <h1>🤖 Ralph</h1>
        <p>Your CRM Marketing Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize
    initialize_session_state()
    
    # Initialize graph
    if st.session_state.graph is None:
        asyncio.run(initialize_graph())
    
    # Display messages
    display_messages()
    
    # Chat input
    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input(
            "💬 Ask Ralph about your customers or campaigns:",
            placeholder="e.g., Show me our top customers",
            label_visibility="collapsed",
            key="user_input"
        )
    
    with col2:
        send_button = st.button("Send", use_container_width=True)
    
    # Handle input
    if (send_button or st.session_state.get('user_input')) and user_input:
        asyncio.run(handle_user_input(user_input))
        st.rerun()
    
    # Quick actions
    st.markdown("### Quick Examples:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Top Customers", use_container_width=True):
            asyncio.run(handle_user_input("Show me our top 5 customers by spending"))
            st.rerun()
    
    with col2:
        if st.button("🎯 Customer Segments", use_container_width=True):
            asyncio.run(handle_user_input("How many customers are in each RFM segment?"))
            st.rerun()
    
    with col3:
        if st.button("📧 Create Campaign", use_container_width=True):
            asyncio.run(handle_user_input("Create a loyalty campaign for our champion customers"))
            st.rerun()
    
    # Clear chat button
    if st.session_state.messages:
        st.markdown("---")
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main() 
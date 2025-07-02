import streamlit as st
import asyncio
import sys
import os
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langgraph.types import Command

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ralph.graph import build_graph, AgentState


def init_session_state():
    """Initialize session state variables"""
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
    if 'pending_interrupt' not in st.session_state:
        st.session_state.pending_interrupt = None
    if 'yolo_mode' not in st.session_state:
        st.session_state.yolo_mode = False


async def initialize_graph():
    """Initialize the graph if not already done"""
    if st.session_state.graph is None:
        try:
            st.session_state.graph = await build_graph()
        except Exception as e:
            st.error(f"Failed to initialize graph: {str(e)}")
            return False
    return True


async def stream_response(input_data: Dict[str, Any], graph, config: Dict[str, Any]):
    """Stream response from the graph and return collected content"""
    response_content = []
    
    try:
        async for message_chunk, metadata in graph.astream(
            input=input_data,
            stream_mode="messages",
            config=config
        ):
            if hasattr(message_chunk, 'content') and message_chunk.content:
                response_content.append(message_chunk.content)
            elif hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]
                tool_name = tool_chunk.get("name", "")
                args = tool_chunk.get("args", "")
                
                if tool_name:
                    response_content.append(f"\n**🔧 Tool Call:** {tool_name}")
                if args:
                    response_content.append(f"```json\n{args}\n```")
                    
    except Exception as e:
        response_content.append(f"Error: {str(e)}")
    
    return "".join(response_content)


def handle_interrupt(interrupt_data: Dict[str, Any]):
    """Handle approval workflow for interrupts"""
    st.subheader("🔍 Human Approval Required")
    
    # Display interrupt information
    with st.expander("Tool Call Details", expanded=True):
        st.json(interrupt_data)
    
    # Create approval interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Continue", key="continue_btn"):
            return {"action": "continue", "data": None}
    
    with col2:
        if st.button("✏️ Update", key="update_btn"):
            st.session_state.show_update_form = True
    
    with col3:
        if st.button("💬 Feedback", key="feedback_btn"):
            st.session_state.show_feedback_form = True
    
    # Update form
    if st.session_state.get('show_update_form', False):
        st.subheader("Update Tool Arguments")
        updated_args = st.text_area(
            "Enter updated JSON arguments:",
            value=json.dumps(interrupt_data.get('tool_call', {}).get('args', {}), indent=2)
        )
        if st.button("Submit Update"):
            try:
                parsed_args = json.loads(updated_args)
                st.session_state.show_update_form = False
                return {"action": "update", "data": updated_args}
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please check your input.")
    
    # Feedback form
    if st.session_state.get('show_feedback_form', False):
        st.subheader("Provide Feedback")
        feedback = st.text_area("Enter your feedback:")
        if st.button("Submit Feedback"):
            st.session_state.show_feedback_form = False
            return {"action": "feedback", "data": feedback}
    
    return None


async def process_user_input(user_input: str):
    """Process user input and get response"""
    if not await initialize_graph():
        return
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Create graph input
    graph_input = AgentState(
        messages=[HumanMessage(content=user_input)],
        yolo_mode=st.session_state.yolo_mode
    )
    
    # Get response
    with st.spinner("Ralph is thinking..."):
        response = await stream_response(
            graph_input, 
            st.session_state.graph, 
            st.session_state.config
        )
    
    # Add assistant response to chat
    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Check for interrupts
    thread_state = st.session_state.graph.get_state(config=st.session_state.config)
    if thread_state.interrupts:
        st.session_state.pending_interrupt = thread_state.interrupts[0].value


def main():
    st.set_page_config(
        page_title="Ralph - CRM Assistant",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Header
    st.title("🤖 Ralph - CRM Assistant")
    st.caption("Your customer service agent and marketing expert")
    
    # Sidebar with settings
    with st.sidebar:
        st.header("Settings")
        st.session_state.yolo_mode = st.checkbox(
            "YOLO Mode", 
            value=st.session_state.yolo_mode,
            help="Skip human approval for protected tool calls"
        )
        
        if st.button("🔄 Reset Conversation"):
            st.session_state.messages = []
            st.session_state.pending_interrupt = None
            st.rerun()
        
        if st.button("🏠 Initialize Ralph"):
            st.session_state.graph = None
            asyncio.run(initialize_graph())
            if st.session_state.graph:
                st.success("Ralph initialized successfully!")
            else:
                st.error("Failed to initialize Ralph")
    
    # Handle pending interrupts
    if st.session_state.pending_interrupt:
        approval_result = handle_interrupt(st.session_state.pending_interrupt)
        if approval_result:
            # Process approval
            with st.spinner("Processing approval..."):
                try:
                    asyncio.run(stream_response(
                        Command(resume=approval_result),
                        st.session_state.graph,
                        st.session_state.config
                    ))
                    st.session_state.pending_interrupt = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing approval: {str(e)}")
        return
    
    # Chat interface
    st.subheader("💬 Chat")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Initialize with greeting if no messages
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            greeting = "Hello! I'm Ralph, your customer service agent and marketing expert. I'm here to help you manage and optimize customer relationships. How can I assist you today?"
            st.markdown(greeting)
            st.session_state.messages.append({"role": "assistant", "content": greeting})
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and display response
        with st.chat_message("assistant"):
            with st.spinner("Ralph is thinking..."):
                try:
                    asyncio.run(process_user_input(prompt))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main() 
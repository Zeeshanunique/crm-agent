import streamlit as st
import asyncio
import sys
import os
import json
import re
import pandas as pd
from typing import Dict, Any, List
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


def parse_and_format_content(content: str) -> List[Dict[str, Any]]:
    """Parse content and return formatted components"""
    components = []
    
    # Split content by common patterns
    parts = re.split(r'(\*\*🔧 Tool Call:\*\* \w+|```json\s*{.*?}\s*```)', content, flags=re.DOTALL)
    
    for part in parts:
        if not part.strip():
            continue
            
        # Tool call header
        if part.startswith('**🔧 Tool Call:**'):
            tool_name = part.replace('**🔧 Tool Call:**', '').strip()
            components.append({
                'type': 'tool_call_header',
                'content': tool_name
            })
        
        # JSON code block
        elif part.startswith('```json') and part.endswith('```'):
            json_content = part.replace('```json', '').replace('```', '').strip()
            try:
                parsed_json = json.loads(json_content)
                components.append({
                    'type': 'json_data',
                    'content': parsed_json
                })
            except json.JSONDecodeError:
                components.append({
                    'type': 'code',
                    'content': json_content,
                    'language': 'json'
                })
        
        # Regular text
        else:
            # Check if it contains SQL
            if 'SELECT' in part.upper() or 'FROM' in part.upper():
                components.append({
                    'type': 'sql',
                    'content': part.strip()
                })
            else:
                components.append({
                    'type': 'text',
                    'content': part.strip()
                })
    
    return components


def render_formatted_content(content: str):
    """Render content with proper formatting"""
    # First, try to extract and format tool calls and responses better
    if '**🔧 Tool Call:**' in content:
        # Split by tool calls
        parts = content.split('**🔧 Tool Call:**')
        
        # Render first part (usually text before tool call)
        if parts[0].strip():
            st.markdown(parts[0].strip())
        
        # Process each tool call
        for i, part in enumerate(parts[1:], 1):
            lines = part.strip().split('\n')
            if lines:
                tool_name = lines[0].strip()
                
                # Tool call header
                st.markdown(f"### 🔧 Tool Call: {tool_name}")
                
                # Try to extract JSON from the rest
                remaining_content = '\n'.join(lines[1:])
                
                # Look for JSON patterns
                json_match = re.search(r'```json\s*({.*?})\s*```', remaining_content, re.DOTALL)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                        
                        # Special handling for SQL queries
                        if 'sql' in json_data:
                            st.markdown("**SQL Query:**")
                            st.code(json_data['sql'], language='sql')
                        else:
                            st.markdown("**Parameters:**")
                            st.json(json_data)
                    except json.JSONDecodeError:
                        st.code(json_match.group(1), language='json')
                
                # Look for response data (arrays of objects)
                response_match = re.search(r'\[(\{.*?\}(?:,\s*\{.*?\})*)\]', remaining_content, re.DOTALL)
                if response_match:
                    try:
                        # Clean up the JSON string
                        json_str = '[' + response_match.group(1) + ']'
                        response_data = json.loads(json_str)
                        
                        if response_data and isinstance(response_data, list) and len(response_data) > 0:
                            st.markdown("**Query Results:**")
                            df = pd.DataFrame(response_data)
                            st.dataframe(df, use_container_width=True)
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                # Render remaining text
                # Remove the JSON parts we already processed
                clean_text = remaining_content
                if json_match:
                    clean_text = clean_text.replace(json_match.group(0), '')
                if response_match:
                    clean_text = clean_text.replace(response_match.group(0), '')
                
                clean_text = clean_text.strip()
                if clean_text:
                    st.markdown(clean_text)
    else:
        # Regular content
        st.markdown(content)


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
                    response_content.append(f"\n\n**🔧 Tool Call:** {tool_name}\n\n")
                if args:
                    response_content.append(f"```json\n{args}\n```\n")
                    
    except Exception as e:
        response_content.append(f"Error: {str(e)}")
    
    return "".join(response_content)


def handle_interrupt(interrupt_data: Dict[str, Any]):
    """Handle approval workflow for interrupts"""
    st.markdown("---")
    st.subheader("🔍 Human Approval Required")
    
    # Display tool call information in a nice format
    tool_call = interrupt_data.get('tool_call', {})
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**Tool:** `{tool_call.get('name', 'Unknown')}`")
        if tool_call.get('args'):
            st.markdown("**Arguments:**")
            st.json(tool_call['args'])
    
    with col2:
        st.markdown("**Actions:**")
        
        if st.button("✅ Continue", key="continue_btn", use_container_width=True):
            return {"action": "continue", "data": None}
        
        if st.button("✏️ Update", key="update_btn", use_container_width=True):
            st.session_state.show_update_form = True
        
        if st.button("💬 Feedback", key="feedback_btn", use_container_width=True):
            st.session_state.show_feedback_form = True
    
    # Update form
    if st.session_state.get('show_update_form', False):
        st.markdown("---")
        st.subheader("Update Tool Arguments")
        updated_args = st.text_area(
            "Enter updated JSON arguments:",
            value=json.dumps(tool_call.get('args', {}), indent=2),
            height=200
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Update", use_container_width=True):
                try:
                    parsed_args = json.loads(updated_args)
                    st.session_state.show_update_form = False
                    return {"action": "update", "data": updated_args}
                except json.JSONDecodeError:
                    st.error("Invalid JSON format. Please check your input.")
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_update_form = False
                st.rerun()
    
    # Feedback form
    if st.session_state.get('show_feedback_form', False):
        st.markdown("---")
        st.subheader("Provide Feedback")
        feedback = st.text_area("Enter your feedback:", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Feedback", use_container_width=True):
                st.session_state.show_feedback_form = False
                return {"action": "feedback", "data": feedback}
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_feedback_form = False
                st.rerun()
    
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
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .stDataFrame {
            border: 1px solid #e0e0e0;
            border-radius: 0.5rem;
        }
        div[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
        .tool-call-header {
            background-color: #e3f2fd;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border-left: 4px solid #2196f3;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Sidebar with settings
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        
        # YOLO Mode toggle
        st.session_state.yolo_mode = st.toggle(
            "YOLO Mode", 
            value=st.session_state.yolo_mode,
            help="Skip human approval for protected tool calls"
        )
        
        st.markdown("---")
        
        # Control buttons
        if st.button("🔄 Reset Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_interrupt = None
            st.rerun()
        
        if st.button("🏠 Initialize Ralph", use_container_width=True):
            with st.spinner("Initializing Ralph..."):
                st.session_state.graph = None
                try:
                    success = asyncio.run(initialize_graph())
                    if success:
                        st.success("Ralph initialized successfully!")
                    else:
                        st.error("Failed to initialize Ralph")
                except Exception as e:
                    st.error(f"Error initializing Ralph: {str(e)}")
        
        st.markdown("---")
        st.markdown("### 📊 Session Info")
        st.metric("Messages", len(st.session_state.messages))
        st.metric("YOLO Mode", "ON" if st.session_state.yolo_mode else "OFF")
    
    # Main header
    st.title("🤖 Ralph - CRM Assistant")
    st.caption("Your customer service agent and marketing expert")
    
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
    st.markdown("---")
    
    # Chat container with better styling
    chat_container = st.container()
    
    # Initialize with greeting if no messages
    if not st.session_state.messages:
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown("""
                👋 **Hello! I'm Ralph, your CRM assistant.**
                
                I can help you with:
                - 📊 Analyzing customer data and behavior
                - 🎯 Creating targeted marketing campaigns  
                - 📧 Managing customer communications
                - 📈 Generating insights and reports
                
                What would you like to explore today?
                """)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Hello! I'm Ralph, your customer service agent and marketing expert. I'm here to help you manage and optimize customer relationships. How can I assist you today?"
        })
    
    # Display chat history with improved formatting
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    render_formatted_content(message["content"])
                else:
                    st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask Ralph anything about your customers..."):
        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Process and display response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Ralph is analyzing..."):
                    try:
                        asyncio.run(process_user_input(prompt))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main() 
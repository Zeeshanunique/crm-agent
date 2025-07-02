import streamlit as st
import asyncio
import sys
import os
import json
import re
import pandas as pd
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


def clean_sql_query(sql_text: str) -> str:
    """Clean up SQL query text by removing artifacts"""
    # Remove all the ``` ```json artifacts
    cleaned = re.sub(r'```\s*```json\s*', '', sql_text)
    cleaned = re.sub(r'```json\s*', '', cleaned)
    cleaned = re.sub(r'```\s*', '', cleaned)
    
    # Remove extra quotes and escape characters
    cleaned = re.sub(r'\\"', '"', cleaned)
    cleaned = re.sub(r'\\n', '\n', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def extract_json_arrays(text: str):
    """Extract JSON arrays from text"""
    json_arrays = []
    
    # Look for JSON array patterns
    array_pattern = r'\[\s*\{[^}]+\}(?:\s*,\s*\{[^}]+\})*\s*\]'
    matches = re.findall(array_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            # Clean up the JSON string
            clean_json = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', match)  # Add quotes to keys
            clean_json = re.sub(r':\s*([^",}\]]+)([,}\]])', r': "\1"\2', clean_json)  # Add quotes to values
            clean_json = re.sub(r'""(\d+\.?\d*)"', r'"\1"', clean_json)  # Fix double-quoted numbers
            
            parsed = json.loads(clean_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                json_arrays.append(parsed)
        except (json.JSONDecodeError, ValueError):
            continue
    
    return json_arrays


def render_enhanced_content(content: str):
    """Enhanced content renderer with better formatting"""
    
    # Split content into sections
    sections = content.split('**🔧 Tool Call:**')
    
    # Render content before first tool call
    if sections[0].strip():
        st.markdown(sections[0].strip())
    
    # Process each tool call section
    for i, section in enumerate(sections[1:], 1):
        lines = section.strip().split('\n', 1)
        if not lines:
            continue
            
        tool_name = lines[0].strip()
        remaining_content = lines[1] if len(lines) > 1 else ""
        
        # Tool call header with nice styling
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #2196f3; margin: 1rem 0;">
            <h4 style="margin: 0; color: #1976d2;">🔧 Tool Call: {tool_name}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Extract and display SQL query
        sql_match = re.search(r'"sql":\s*"([^"]*)"', remaining_content)
        if sql_match:
            sql_query = clean_sql_query(sql_match.group(1))
            if sql_query:
                st.markdown("**SQL Query:**")
                st.code(sql_query, language='sql')
        
        # Extract and display JSON data as tables
        json_arrays = extract_json_arrays(remaining_content)
        for json_array in json_arrays:
            try:
                df = pd.DataFrame(json_array)
                if len(df) > 0:
                    st.markdown("**Query Results:**")
                    
                    # Format numeric columns
                    for col in df.columns:
                        if df[col].dtype in ['float64', 'int64']:
                            if 'spending' in col.lower() or 'price' in col.lower() or 'amount' in col.lower():
                                df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                        elif col.lower() in ['email']:
                            # Keep email as is - Streamlit will auto-link them
                            pass
                    
                    # Display the table
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            col: st.column_config.TextColumn(
                                col.replace('_', ' ').title(),
                                width="medium"
                            ) for col in df.columns
                        }
                    )
            except Exception as e:
                st.write(f"Error displaying data: {e}")
        
        # Clean and display remaining text
        # Remove the JSON and SQL parts we already processed
        clean_text = remaining_content
        if sql_match:
            clean_text = clean_text.replace(sql_match.group(0), '')
        
        # Remove JSON arrays
        for json_array in json_arrays:
            clean_text = re.sub(r'\[\s*\{[^}]+\}(?:\s*,\s*\{[^}]+\})*\s*\]', '', clean_text)
        
        # Remove JSON artifacts
        clean_text = re.sub(r'```json[^`]*```', '', clean_text)
        clean_text = re.sub(r'\{[^}]*\}', '', clean_text)
        
        # Clean up and display
        clean_text = clean_text.strip()
        if clean_text:
            st.markdown(clean_text)


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
    
    # Enhanced interrupt display
    st.markdown("""
    <div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #ffc107; margin: 1rem 0;">
        <h4 style="margin: 0; color: #856404;">🔍 Human Approval Required</h4>
    </div>
    """, unsafe_allow_html=True)
    
    tool_call = interrupt_data.get('tool_call', {})
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"**Tool:** `{tool_call.get('name', 'Unknown')}`")
        if tool_call.get('args'):
            st.markdown("**Arguments:**")
            with st.expander("View Details", expanded=True):
                st.json(tool_call['args'])
    
    with col2:
        st.markdown("**Actions:**")
        
        if st.button("✅ Continue", key="continue_btn", use_container_width=True, type="primary"):
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
            if st.button("Submit Update", use_container_width=True, type="primary"):
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
            if st.button("Submit Feedback", use_container_width=True, type="primary"):
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
    
    # Enhanced CSS
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
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
        .metric-container {
            background-color: white;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border: 1px solid #e0e0e0;
            margin: 0.25rem 0;
        }
        .stButton > button {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Enhanced sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Control Panel")
        
        # Status indicators
        st.markdown("### 📊 Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", len(st.session_state.messages))
        with col2:
            st.metric("YOLO Mode", "ON" if st.session_state.yolo_mode else "OFF")
        
        st.markdown("---")
        
        # Settings
        st.markdown("### 🛠️ Settings")
        st.session_state.yolo_mode = st.toggle(
            "YOLO Mode", 
            value=st.session_state.yolo_mode,
            help="Skip human approval for protected tool calls"
        )
        
        st.markdown("---")
        
        # Actions
        st.markdown("### 🎮 Actions")
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
        st.markdown("""
        ### 💡 Tips
        - Ask about customer data analysis
        - Request marketing campaign ideas  
        - Explore RFM segmentation
        - Create targeted campaigns
        """)
    
    # Main header
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 0.5rem; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0;">🤖 Ralph - CRM Assistant</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Your intelligent customer relationship management companion</p>
    </div>
    """, unsafe_allow_html=True)
    
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
    chat_container = st.container()
    
    # Initialize with enhanced greeting
    if not st.session_state.messages:
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown("""
                ## 👋 Welcome to Ralph CRM!
                
                I'm your intelligent CRM assistant, ready to help you:
                
                **📊 Data Analysis**
                - Analyze customer spending patterns
                - Generate RFM segmentation insights
                - Create customer behavior reports
                
                **🎯 Marketing Campaigns**
                - Design targeted campaigns
                - Send personalized emails
                - Track campaign performance
                
                **💡 Strategic Insights**
                - Identify high-value customers
                - Spot at-risk segments
                - Recommend retention strategies
                
                **What would you like to explore first?**
                """)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Hello! I'm Ralph, your customer service agent and marketing expert. I'm here to help you manage and optimize customer relationships. How can I assist you today?"
        })
    
    # Display chat history with enhanced formatting
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    render_enhanced_content(message["content"])
                else:
                    st.markdown(message["content"])
    
    # Enhanced chat input
    if prompt := st.chat_input("💬 Ask Ralph about your customers, campaigns, or data insights..."):
        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Process and display response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("🧠 Ralph is analyzing your request..."):
                    try:
                        asyncio.run(process_user_input(prompt))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 
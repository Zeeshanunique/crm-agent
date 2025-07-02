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


def extract_clean_json_array(text: str) -> List[Dict]:
    """Extract and parse JSON arrays from text more reliably"""
    json_arrays = []
    
    # Look for array patterns more carefully
    array_patterns = [
        r'\[\s*\{[^}]+\}(?:\s*,\s*\{[^}]+\})*\s*\]',  # Standard array
        r'\[\s*\{[^]]+\}\s*\]',  # Simple single object array
    ]
    
    for pattern in array_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Try to parse as-is first
                parsed = json.loads(match)
                if isinstance(parsed, list) and len(parsed) > 0:
                    json_arrays.append(parsed)
                    continue
            except json.JSONDecodeError:
                pass
            
            try:
                # Clean up common issues
                clean_match = match
                # Fix unquoted keys
                clean_match = re.sub(r'(\{|\s|,)(\w+):', r'\1"\2":', clean_match)
                # Fix unquoted string values (but not numbers)
                clean_match = re.sub(r':\s*([^",\[\]{}0-9][^",\[\]{}]*?)(\s*[,}])', r': "\1"\2', clean_match)
                # Fix already quoted numbers
                clean_match = re.sub(r'"\s*(\d+\.?\d*)\s*"', r'\1', clean_match)
                
                parsed = json.loads(clean_match)
                if isinstance(parsed, list) and len(parsed) > 0:
                    json_arrays.append(parsed)
            except (json.JSONDecodeError, ValueError):
                continue
    
    return json_arrays


def clean_and_separate_content(content: str) -> Dict[str, Any]:
    """Clean content and separate into logical components"""
    result = {
        'tool_calls': [],
        'errors': [],
        'data_tables': [],
        'clean_text': []
    }
    
    # Extract errors first
    error_patterns = [
        r'Error:\s*[^.]+\.',
        r'ExceptionGroup\([^)]+\)[^.]*\.',
        r'McpError\([^)]+\)[^.]*\.',
    ]
    
    for pattern in error_patterns:
        errors = re.findall(pattern, content, re.IGNORECASE)
        result['errors'].extend(errors)
        # Remove errors from content
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # Split by tool calls
    tool_call_sections = re.split(r'\*\*🔧 Tool Call:\*\*\s*(\w+)', content)
    
    # First section (before any tool calls)
    if tool_call_sections[0].strip():
        clean_text = tool_call_sections[0].strip()
        # Remove any JSON artifacts
        clean_text = re.sub(r'\[,+\]', '', clean_text)
        clean_text = re.sub(r'\{[^}]*\}', '', clean_text)
        clean_text = re.sub(r'```json[^`]*```', '', clean_text)
        if clean_text.strip():
            result['clean_text'].append(clean_text.strip())
    
    # Process tool calls (pairs of tool_name and content)
    for i in range(1, len(tool_call_sections), 2):
        if i + 1 < len(tool_call_sections):
            tool_name = tool_call_sections[i].strip()
            tool_content = tool_call_sections[i + 1]
            
            tool_call = {
                'name': tool_name,
                'sql_query': None,
                'parameters': None,
                'data_tables': [],
                'clean_text': []
            }
            
            # Extract SQL query
            sql_match = re.search(r'"sql":\s*"([^"]*)"', tool_content)
            if sql_match:
                sql_query = sql_match.group(1)
                # Clean SQL
                sql_query = re.sub(r'\\n', '\n', sql_query)
                sql_query = re.sub(r'\\"', '"', sql_query)
                tool_call['sql_query'] = sql_query
                # Remove SQL from content
                tool_content = tool_content.replace(sql_match.group(0), '')
            
            # Extract JSON parameters
            param_match = re.search(r'```json\s*(\{[^}]*\})\s*```', tool_content)
            if param_match:
                try:
                    tool_call['parameters'] = json.loads(param_match.group(1))
                    # Remove parameters from content
                    tool_content = tool_content.replace(param_match.group(0), '')
                except json.JSONDecodeError:
                    pass
            
            # Extract data arrays
            data_arrays = extract_clean_json_array(tool_content)
            tool_call['data_tables'] = data_arrays
            
            # Clean remaining text
            clean_text = tool_content
            # Remove JSON arrays
            for array in data_arrays:
                # Remove the array from text (approximate)
                clean_text = re.sub(r'\[\s*\{[^]]+\}\s*\]', '', clean_text, count=1)
            
            # Remove other artifacts
            clean_text = re.sub(r'```json[^`]*```', '', clean_text)
            clean_text = re.sub(r'\{[^}]*\}', '', clean_text)
            clean_text = re.sub(r'\[,+\]', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            clean_text = clean_text.strip()
            
            if clean_text:
                tool_call['clean_text'].append(clean_text)
            
            result['tool_calls'].append(tool_call)
    
    return result


def render_super_clean_content(content: str):
    """Render content with superior cleaning and formatting"""
    parsed = clean_and_separate_content(content)
    
    # Display errors first if any
    if parsed['errors']:
        for error in parsed['errors']:
            st.error(f"⚠️ {error}")
    
    # Display initial text
    for text in parsed['clean_text']:
        if text:
            st.markdown(text)
    
    # Display tool calls
    for tool_call in parsed['tool_calls']:
        # Tool call header with enhanced styling
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 0.5rem; margin: 1.5rem 0; color: white;">
            <h4 style="margin: 0; color: white;">🔧 Tool Call: {tool_call['name']}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # SQL Query
        if tool_call['sql_query']:
            st.markdown("**📝 SQL Query:**")
            st.code(tool_call['sql_query'], language='sql')
        
        # Parameters
        if tool_call['parameters']:
            st.markdown("**⚙️ Parameters:**")
            with st.expander("View Parameters", expanded=False):
                st.json(tool_call['parameters'])
        
        # Data Tables
        for i, data_array in enumerate(tool_call['data_tables']):
            try:
                df = pd.DataFrame(data_array)
                if len(df) > 0:
                    st.markdown(f"**📊 Query Results {i+1 if len(tool_call['data_tables']) > 1 else ''}:**")
                    
                    # Format columns
                    display_df = df.copy()
                    for col in display_df.columns:
                        if display_df[col].dtype in ['float64', 'int64']:
                            # Check if it's a monetary column
                            if any(word in col.lower() for word in ['spending', 'price', 'amount', 'cost', 'revenue', 'total']):
                                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                            # Check if it's a count column
                            elif any(word in col.lower() for word in ['count', 'number', 'qty', 'quantity']):
                                display_df[col] = display_df[col].apply(lambda x: f"{x:,}" if pd.notnull(x) else "")
                    
                    # Display with better formatting
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            col: st.column_config.TextColumn(
                                col.replace('_', ' ').replace('customercount', 'Customer Count').title(),
                                width="medium"
                            ) for col in display_df.columns
                        }
                    )
                    
                    # Add download button for data
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{tool_call['name']}_results.csv",
                        mime="text/csv",
                        key=f"download_{tool_call['name']}_{i}"
                    )
            except Exception as e:
                st.warning(f"Could not display data table: {str(e)}")
        
        # Clean text from tool call
        for text in tool_call['clean_text']:
            if text:
                st.markdown(text)


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
    <div style="background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); 
                padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; color: white;">
        <h4 style="margin: 0; color: white;">🔍 Human Approval Required</h4>
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
            if st.button("Cancel Update", use_container_width=True):
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
            if st.button("Cancel Feedback", use_container_width=True):
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
    
    # Enhanced CSS with better styling
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        .stChatMessage {
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stDataFrame {
            border: 1px solid #e0e0e0;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
        }
        .stButton > button {
            width: 100%;
            border-radius: 0.5rem;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Enhanced sidebar
    with st.sidebar:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 0.5rem; margin-bottom: 2rem; color: white; text-align: center;">
            <h3 style="margin: 0; color: white;">⚙️ Control Panel</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Status indicators
        st.markdown("### 📊 Session Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", len(st.session_state.messages))
        with col2:
            st.metric("YOLO Mode", "ON" if st.session_state.yolo_mode else "OFF")
        
        # Graph status
        graph_status = "🟢 Ready" if st.session_state.graph else "🔴 Not Initialized"
        st.metric("Ralph Status", graph_status)
        
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
        st.markdown("### 🎮 Quick Actions")
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
                        st.success("✅ Ralph initialized successfully!")
                    else:
                        st.error("❌ Failed to initialize Ralph")
                except Exception as e:
                    st.error(f"❌ Error initializing Ralph: {str(e)}")
        
        if st.button("🔍 Test Connection", use_container_width=True):
            if st.session_state.graph:
                st.success("✅ Ralph is ready!")
            else:
                st.warning("⚠️ Please initialize Ralph first")
        
        st.markdown("---")
        st.markdown("""
        ### 💡 Pro Tips
        - 📊 **Data Analysis**: "Show me RFM segments"
        - 🎯 **Campaigns**: "Create a loyalty campaign"  
        - 📈 **Insights**: "Find at-risk customers"
        - 💰 **Revenue**: "Top spending customers"
        """)
    
    # Main header with gradient
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 1rem; margin-bottom: 2rem; color: white; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <h1 style="margin: 0; color: white; font-size: 2.5rem;">🤖 Ralph CRM Assistant</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.2rem;">
            Your intelligent customer relationship management companion
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Handle pending interrupts
    if st.session_state.pending_interrupt:
        approval_result = handle_interrupt(st.session_state.pending_interrupt)
        if approval_result:
            # Process approval
            with st.spinner("🔄 Processing approval..."):
                try:
                    asyncio.run(stream_response(
                        Command(resume=approval_result),
                        st.session_state.graph,
                        st.session_state.config
                    ))
                    st.session_state.pending_interrupt = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error processing approval: {str(e)}")
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
                
                ### 📊 **Data Analysis**
                - Analyze customer spending patterns
                - Generate RFM segmentation insights  
                - Create customer behavior reports
                
                ### 🎯 **Marketing Campaigns**
                - Design targeted campaigns
                - Send personalized emails
                - Track campaign performance
                
                ### 💡 **Strategic Insights**
                - Identify high-value customers
                - Spot at-risk segments
                - Recommend retention strategies
                
                **Ready to explore your customer data? Ask me anything!** 🚀
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
                    render_super_clean_content(message["content"])
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
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


def ultra_clean_content(content: str) -> Dict[str, Any]:
    """Ultra-clean content parser that properly separates everything"""
    
    # Initialize result structure
    result = {
        'errors': [],
        'tool_calls': [],
        'clean_text': [],
        'data_tables': []
    }
    
    # Step 1: Extract and remove errors completely  
    error_patterns = [
        r'Error:\s*[^.!?]*[.!?]',
        r'ExceptionGroup\([^)]+\)[^.!?]*[.!?]',
        r'McpError\([^)]+\)[^.!?]*[.!?]',
        r'column [^\s]+ does not exist[^.!?]*[.!?]',
        r'unhandled errors in a TaskGroup[^.!?]*[.!?]'
    ]
    
    for pattern in error_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        result['errors'].extend(matches)
        content = re.sub(pattern, ' ', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Step 2: Split content by tool call markers
    # Look for various tool call patterns
    tool_patterns = [
        r'\*\*🔧 Tool Call:\*\*\s*(\w+)',
        r'Tool Call:\s*(\w+)',
        r'< TOOL CALL:\s*(\w+)\s*>',
    ]
    
    sections = [content]  # Start with full content
    
    for pattern in tool_patterns:
        new_sections = []
        for section in sections:
            split_parts = re.split(f'({pattern})', section)
            new_sections.extend(split_parts)
        sections = new_sections
        if len(sections) > 1:
            break  # Found tool calls, use this split
    
    # Step 3: Process sections
    current_text = ""
    current_tool = None
    
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
            
        # Check if this section is a tool name
        tool_match = None
        for pattern in tool_patterns:
            tool_match = re.match(pattern, section)
            if tool_match:
                break
        
        if tool_match:
            # Save previous text if any
            if current_text.strip():
                result['clean_text'].append(current_text.strip())
                current_text = ""
            
            # Start new tool call
            current_tool = {
                'name': tool_match.group(1),
                'sql_query': None,
                'data_tables': [],
                'clean_text': []
            }
            continue
        
        # Process section content
        section_data = process_section_content(section)
        
        if current_tool:
            # Add to current tool call
            if section_data['sql_query']:
                current_tool['sql_query'] = section_data['sql_query']
            current_tool['data_tables'].extend(section_data['data_tables'])
            if section_data['clean_text']:
                current_tool['clean_text'].extend(section_data['clean_text'])
            
            # If this seems to be the end of the tool call, save it
            if section_data['data_tables'] or i == len(sections) - 1:
                result['tool_calls'].append(current_tool)
                current_tool = None
        else:
            # Add to general content
            if section_data['sql_query']:
                # SQL without tool context
                result['clean_text'].append(f"**SQL Query:**\n```sql\n{section_data['sql_query']}\n```")
            result['data_tables'].extend(section_data['data_tables'])
            if section_data['clean_text']:
                current_text += " " + " ".join(section_data['clean_text'])
    
    # Add any remaining text
    if current_text.strip():
        result['clean_text'].append(current_text.strip())
    
    # Clean up final text items
    cleaned_texts = []
    for text in result['clean_text']:
        text = clean_final_text(text)
        if text and len(text) > 10:  # Only keep substantial text
            cleaned_texts.append(text)
    result['clean_text'] = cleaned_texts
    
    return result


def process_section_content(content: str) -> Dict[str, Any]:
    """Process a section and extract SQL, data, and clean text"""
    result = {
        'sql_query': None,
        'data_tables': [],
        'clean_text': []
    }
    
    # Extract SQL queries
    sql_patterns = [
        r'"sql":\s*"([^"]+)"',
        r'```sql\n([^`]+)\n```',
        r'SQL Query:\s*([^`\n]+)',
    ]
    
    for pattern in sql_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
            # Clean SQL
            sql = re.sub(r'\\n', '\n', sql)
            sql = re.sub(r'\\"', '"', sql)
            sql = sql.strip()
            if sql:
                result['sql_query'] = sql
            # Remove from content
            content = content.replace(match.group(0), ' ')
            break
    
    # Extract JSON data arrays
    result['data_tables'] = extract_json_data_arrays(content)
    
    # Remove JSON arrays from content
    json_patterns = [
        r'\[\s*\{[^}]+\}(?:\s*,\s*\{[^}]+\})*\s*\]',
        r'```json[^`]*```',
        r'\{[^}]*\}',
    ]
    
    for pattern in json_patterns:
        content = re.sub(pattern, ' ', content, flags=re.DOTALL)
    
    # Clean remaining text
    clean_text = clean_final_text(content)
    if clean_text:
        result['clean_text'].append(clean_text)
    
    return result


def extract_json_data_arrays(text: str) -> List[List[Dict]]:
    """Extract JSON arrays that look like data tables"""
    arrays = []
    
    # Look for array patterns
    array_pattern = r'\[\s*\{[^}]*"[^"]*"[^}]*\}(?:\s*,\s*\{[^}]*"[^"]*"[^}]*\})*\s*\]'
    matches = re.findall(array_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            # Clean the match
            clean_match = match
            # Fix common JSON issues
            clean_match = re.sub(r'(\w+):', r'"\1":', clean_match)  # Quote keys
            clean_match = re.sub(r':\s*([^",\[\]{}0-9][^",\[\]{}]*?)(\s*[,}])', r': "\1"\2', clean_match)  # Quote string values
            clean_match = re.sub(r'"\s*(\d+\.?\d*)\s*"', r'\1', clean_match)  # Unquote numbers
            
            parsed = json.loads(clean_match)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                # Only keep if it looks like tabular data
                if len(parsed[0]) > 1:  # More than one column
                    arrays.append(parsed)
        except (json.JSONDecodeError, ValueError):
            continue
    
    return arrays


def clean_final_text(text: str) -> str:
    """Final text cleaning"""
    if not text:
        return ""
    
    # Remove artifacts
    text = re.sub(r'\[,+\]', '', text)
    text = re.sub(r'^\s*,+\s*', '', text)
    text = re.sub(r'\s*,+\s*$', '', text)
    text = re.sub(r'^\s*\.\s*', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove very short or artifact-like text
    if len(text) < 5 or text in [',', '.', '...', '[', ']', '{', '}']:
        return ""
    
    return text


def render_ultra_clean_content(content: str):
    """Render content with ultra-clean formatting"""
    parsed = ultra_clean_content(content)
    
    # Display errors first
    for error in parsed['errors']:
        st.error(f"⚠️ {error.strip()}")
    
    # Display initial clean text
    for text in parsed['clean_text']:
        if text.strip():
            st.markdown(text.strip())
    
    # Display tool calls
    for tool_call in parsed['tool_calls']:
        # Tool call header
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
        
        # Data Tables
        for i, data_array in enumerate(tool_call['data_tables']):
            try:
                df = pd.DataFrame(data_array)
                if len(df) > 0:
                    st.markdown(f"**📊 Results:**")
                    
                    # Format monetary columns
                    display_df = df.copy()
                    for col in display_df.columns:
                        if display_df[col].dtype in ['float64', 'int64']:
                            if any(word in col.lower() for word in ['spending', 'price', 'amount', 'cost', 'revenue', 'total']):
                                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
            except Exception as e:
                st.warning(f"Could not display data: {str(e)}")
        
        # Tool call text
        for text in tool_call['clean_text']:
            if text.strip():
                st.markdown(text.strip())
    
    # Display standalone data tables
    for i, data_array in enumerate(parsed['data_tables']):
        if data_array not in [tc_data for tc in parsed['tool_calls'] for tc_data in tc['data_tables']]:
            try:
                df = pd.DataFrame(data_array)
                if len(df) > 0:
                    st.markdown("**📊 Data:**")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception:
                pass


async def stream_response(input_data: Dict[str, Any], graph, config: Dict[str, Any]):
    """Stream response from the graph"""
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
                    response_content.append(f"{args}\n")
                    
    except Exception as e:
        response_content.append(f"Error: {str(e)}")
    
    return "".join(response_content)


async def process_user_input(user_input: str):
    """Process user input and get response"""
    if not await initialize_graph():
        return
    
    # Add user message
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
    
    # Add response
    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Check for interrupts
    thread_state = st.session_state.graph.get_state(config=st.session_state.config)
    if thread_state.interrupts:
        st.session_state.pending_interrupt = thread_state.interrupts[0].value


def main():
    st.set_page_config(
        page_title="Ralph - Ultra Clean CRM",
        page_icon="🤖",
        layout="wide"
    )
    
    # Enhanced CSS
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1200px;
        }
        .stChatMessage {
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 1.5rem;
        }
        .stDataFrame {
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 1rem; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; color: white;">🤖 Ralph CRM - Ultra Clean</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            Clean, error-free customer relationship management
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        st.session_state.yolo_mode = st.toggle("YOLO Mode", st.session_state.yolo_mode)
        
        if st.button("🔄 Reset Chat"):
            st.session_state.messages = []
            st.rerun()
        
        if st.button("🚀 Initialize Ralph"):
            with st.spinner("Initializing..."):
                try:
                    st.session_state.graph = None
                    success = asyncio.run(initialize_graph())
                    if success:
                        st.success("✅ Ready!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Chat interface
    chat_container = st.container()
    
    # Initialize with greeting
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hello! I'm Ralph, your CRM assistant. How can I help you analyze your customer data today?"
        })
    
    # Display messages
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    render_ultra_clean_content(message["content"])
                else:
                    st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask Ralph about your customers..."):
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("🧠 Analyzing..."):
                    try:
                        asyncio.run(process_user_input(prompt))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 
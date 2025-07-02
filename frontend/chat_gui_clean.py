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


def extract_and_clean_content(content: str) -> Dict[str, Any]:
    """Extract and clean content, separating errors from useful information"""
    
    result = {
        'errors': [],
        'tool_calls': [],
        'clean_text': [],
        'data_tables': []
    }
    
    # Remove error messages first and collect them separately
    error_patterns = [
        r'Error:\s*ExceptionGroup[^.]*\.',
        r'Error:\s*[^.]*column [^\s]+ does not exist[^.]*\.',
        r'McpError[^.]*\.',
        r'unhandled errors in a TaskGroup[^.]*\.'
    ]
    
    for pattern in error_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        result['errors'].extend([match.strip() for match in matches])
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Split by tool calls
    tool_call_pattern = r'\*\*🔧 Tool Call:\*\*\s*(\w+)'
    parts = re.split(tool_call_pattern, content)
    
    # First part is before any tool calls
    if parts[0].strip():
        clean_part = clean_text_section(parts[0])
        if clean_part:
            result['clean_text'].append(clean_part)
    
    # Process tool call pairs
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            tool_name = parts[i]
            tool_content = parts[i + 1]
            
            tool_result = process_tool_content(tool_name, tool_content)
            result['tool_calls'].append(tool_result)
    
    return result


def clean_text_section(text: str) -> str:
    """Clean a text section removing artifacts"""
    if not text:
        return ""
    
    # Remove JSON artifacts
    text = re.sub(r'\[,+\]', '', text)
    text = re.sub(r'```json[^`]*```', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Only return if it has meaningful content
    if len(text) > 10 and not text.isspace():
        return text
    
    return ""


def process_tool_content(tool_name: str, content: str) -> Dict[str, Any]:
    """Process content for a specific tool call"""
    
    result = {
        'name': tool_name,
        'sql_query': None,
        'data_tables': [],
        'clean_text': []
    }
    
    # Extract SQL query
    sql_match = re.search(r'"sql":\s*"([^"]*)"', content)
    if sql_match:
        sql = sql_match.group(1)
        sql = re.sub(r'\\n', '\n', sql)
        sql = re.sub(r'\\"', '"', sql)
        result['sql_query'] = sql.strip()
        # Remove SQL from content
        content = content.replace(sql_match.group(0), '')
    
    # Extract JSON data arrays
    json_arrays = extract_json_tables(content)
    result['data_tables'] = json_arrays
    
    # Remove JSON from content
    content = re.sub(r'\[\s*\{[^\]]*\}\s*\]', '', content)
    content = re.sub(r'```json[^`]*```', '', content)
    
    # Clean remaining text
    clean_text = clean_text_section(content)
    if clean_text:
        result['clean_text'].append(clean_text)
    
    return result


def extract_json_tables(content: str) -> List[List[Dict]]:
    """Extract JSON arrays that represent data tables"""
    tables = []
    
    # Look for array patterns
    array_pattern = r'\[\s*\{[^}]*"[^"]*"[^}]*\}(?:\s*,\s*\{[^}]*"[^"]*"[^}]*\})*\s*\]'
    matches = re.findall(array_pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            # Clean JSON syntax issues
            clean_match = match
            clean_match = re.sub(r'(\w+):', r'"\1":', clean_match)  # Quote keys
            clean_match = re.sub(r':\s*([^",\[\]{}0-9][^",\[\]{}]*?)(\s*[,}])', r': "\1"\2', clean_match)
            clean_match = re.sub(r'"\s*(\d+\.?\d*)\s*"', r'\1', clean_match)  # Unquote numbers
            
            parsed = json.loads(clean_match)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                tables.append(parsed)
        except (json.JSONDecodeError, ValueError):
            continue
    
    return tables


def render_cleaned_content(content: str):
    """Render content with proper cleaning and formatting"""
    parsed = extract_and_clean_content(content)
    
    # Display errors in error boxes
    for error in parsed['errors']:
        st.error(f"⚠️ {error}")
    
    # Display clean text first
    for text in parsed['clean_text']:
        st.markdown(text)
    
    # Display tool calls with better formatting
    for tool_call in parsed['tool_calls']:
        # Tool header
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; color: white;">
            <h4 style="margin: 0; color: white;">🔧 Tool Call: {tool_call['name']}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # SQL Query
        if tool_call['sql_query']:
            st.markdown("**📝 SQL Query:**")
            st.code(tool_call['sql_query'], language='sql')
        
        # Data Tables
        for i, table_data in enumerate(tool_call['data_tables']):
            if table_data:
                st.markdown("**📊 Query Results:**")
                try:
                    df = pd.DataFrame(table_data)
                    
                    # Format monetary columns
                    display_df = df.copy()
                    for col in display_df.columns:
                        if display_df[col].dtype in ['float64', 'int64']:
                            if any(word in col.lower() for word in ['spending', 'total', 'amount', 'price', 'cost']):
                                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"{tool_call['name']}_results.csv",
                        mime="text/csv",
                        key=f"download_{tool_call['name']}_{i}"
                    )
                except Exception as e:
                    st.warning(f"Could not display table: {str(e)}")
        
        # Tool call text
        for text in tool_call['clean_text']:
            st.markdown(text)


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
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    graph_input = AgentState(
        messages=[HumanMessage(content=user_input)],
        yolo_mode=st.session_state.yolo_mode
    )
    
    response = await stream_response(
        graph_input, 
        st.session_state.graph, 
        st.session_state.config
    )
    
    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Check for interrupts
    thread_state = st.session_state.graph.get_state(config=st.session_state.config)
    if thread_state.interrupts:
        st.session_state.pending_interrupt = thread_state.interrupts[0].value


def main():
    st.set_page_config(
        page_title="Ralph CRM - Clean Interface",
        page_icon="🤖",
        layout="wide"
    )
    
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1200px;
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
        <h1 style="margin: 0; color: white;">🤖 Ralph CRM - Clean Interface</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            No more formatting artifacts - clean data presentation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        st.session_state.yolo_mode = st.toggle("YOLO Mode", st.session_state.yolo_mode)
        
        if st.button("🔄 Reset Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        if st.button("🚀 Initialize Ralph", use_container_width=True):
            with st.spinner("Initializing Ralph..."):
                try:
                    st.session_state.graph = None
                    success = asyncio.run(initialize_graph())
                    if success:
                        st.success("✅ Ralph is ready!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        st.markdown("---")
        st.markdown("### 💡 Sample Queries")
        st.markdown("""
        - "Show me our top 5 customers by total spending"
        - "What are our customer segments?"
        - "Who are our at-risk customers?"
        """)
    
    # Chat interface
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hello! I'm Ralph, your CRM assistant. I'll provide clean, well-formatted responses to help you analyze your customer data. What would you like to know?"
        })
    
    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_cleaned_content(message["content"])
            else:
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask Ralph about your customers..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("🧠 Ralph is analyzing your request..."):
                try:
                    asyncio.run(process_user_input(prompt))
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 
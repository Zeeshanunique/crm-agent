from pydantic import BaseModel
from typing import Annotated, List, Generator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessageChunk
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from ralph.mymcp.config import mcp_config
from ralph.prompts import ralph_system_prompt
import asyncio
import nest_asyncio
nest_asyncio.apply()


class  AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = []


async def build_graph():
    """
    Build the LangGraph application.
    """

    client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
    tools = await client.get_tools()

    llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14",
        temperature=0.1
    ).bind_tools(tools)

    def assistant_node(state: AgentState) -> AgentState:
        response = llm.invoke(
            [SystemMessage(content=ralph_system_prompt)] +
            state.messages
            )
        state.messages = state.messages + [response]
        return state

    def router(state: AgentState) -> str:
        last_message = state.messages[-1]
        if not last_message.tool_calls:
            return END
        else:
            return "tools"

    builder = StateGraph(AgentState)

    builder.add_node(assistant_node)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant_node")
    builder.add_conditional_edges("assistant_node", router, ["tools", END])
    builder.add_edge("tools", "assistant_node")

    return builder.compile(checkpointer=MemorySaver())


def inspect_graph(graph):
    """
    Visualize the graph using the mermaid.ink API.
    """
    from IPython.display import display, Image
    display(Image(graph.get_graph(xray=True).draw_mermaid_png()))

from ralph.graph import build_graph
from langchain_core.messages import AIMessageChunk, HumanMessage
from typing import AsyncGenerator
from langgraph.graph import StateGraph


async def stream_graph_responses(message: str, graph: StateGraph, **kwargs) -> AsyncGenerator[str, None]:
    """Asynchronously stream the results of the graph run.

    Args:
        message: The user message.

    Returns:
        str: The final LLM response or tool call response
    """
    async for message_chunk, metadata in graph.astream(
        input={"messages": [HumanMessage(content=message)]},
        stream_mode="messages",
        **kwargs
        ):
        if isinstance(message_chunk, AIMessageChunk):
            if message_chunk.response_metadata:
                finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                if finish_reason == "tool_calls":
                    yield "\n\n"

            if message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]

                tool_name = tool_chunk.get("name", "")
                args = tool_chunk.get("args", "")

                if tool_name:
                    tool_call_str = f"\n\n< TOOL CALL: {tool_name} >\n\n"
                if args:
                    tool_call_str = args

                yield tool_call_str
            else:
                yield message_chunk.content
            continue


async def main():
    try:
        graph = await build_graph()
        # A config is required for memory. All graph checkpoints are saved to a thread_id.
        config = {
            "configurable": {
                "thread_id": "1"
            }
        }

        # Stream responses
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            print(f"\n---- User ---- \n\n{user_input}\n")

            print(f"---- Assistant ---- \n")
            # Get the response using our simplified get_stream function
            async for response in stream_graph_responses(user_input, graph, config=config):
                print(response, end="", flush=True)

            # thread_state = agent.runnable.get_state(config=config)

            # if "chart_json" in thread_state.values:
            #     chart_json = thread_state.values["chart_json"]
            #     if chart_json:
            #         import plotly.io as pio
            #         fig = pio.from_json(chart_json)
            #         fig.show()
            # print("")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    print(f"\nGreetings!\n\nTry asking Ralph to show you a preview of the data.\n\n{40*"="}\n\n")

    asyncio.run(main())

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# ----------------------------
# DB Session
# ----------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(url=os.getenv("SUPABASE_URI"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ----------------------------
# MCP Server
# ----------------------------

mcp = FastMCP("db")


@mcp.tool()
async def query_db(sql: str) -> str:
    """Run a read-only SQL query.
    
    Args:
        sql: A valid PostgreSQL query to run.

    Returns:
        The query results
    """
    with SessionLocal() as session:
        result = session.execute(text(sql))
        
    return pd.DataFrame(result.all(), columns=result.keys()).to_json(orient="records", indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
import sqlite3
import logging
from contextlib import closing
from pathlib import Path    
import asyncio
from datetime import datetime
from typing import Optional
from pydantic import AnyUrl
from typing import Any

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from .db_utils import LogDatabase
from . import DEFAULT_DB_PATH

# Initialize database connection
db = LogDatabase(DEFAULT_DB_PATH)

server = Server("mcp-variance-log")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="log-query",
            description="""
                Conversation Variation analysis
                Continuously monitor our conversation and automatically log unusual or noteworthy interactions based on the following criteria:

                1. Probability Classifications:
                HIGH (Not Logged):
                - Common questions and responses
                - Standard technical inquiries
                - Regular clarifications
                - Normal conversation flow

                MEDIUM (Logged):
                - Unexpected but plausible technical issues
                - Unusual patterns in user behavior
                - Noteworthy insights or connections
                - Edge cases in normal usage
                - Uncommon but valid use cases

                LOW (Logged with Priority):
                - Highly unusual technical phenomena
                - Potentially problematic patterns
                - Critical edge cases
                - Unexpected system behaviors
                - Novel or unique use cases
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": """Unique identifier for the chat session.
                            Format: <date>_<user>_<sequence>
                            Example: 20240124_u1_001

                            Components:
                            - date: YYYYMMDD
                            - user: 'u' + user number
                            - sequence: 3-digit sequential number

                            Valid examples:
                            - 20240124_u1_001
                            - 20240124_u1_002
                            - 20240125_u2_001""",
                        "pattern": "^\\d{8}_u\\d+_\\d{3}$"  # Regex pattern to validate format
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Identifier for the user"
                    },
                    "interaction_type": {
                        "type": "string",
                        "description": "Type of interaction being monitored"
                    },
                    "probability_class": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                        "description": "Classification of interaction probability"
                    },
                    "message_content": {
                        "type": "string",
                        "description": "The user's message content"
                    },
                    "response_content": {
                        "type": "string",
                        "description": "The system's response content"
                    },
                    "context_summary": {
                        "type": "string",
                        "description": "Summary of interaction context"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation for the probability classification"
                    }
                },
                "required": [
                    "session_id",
                    "user_id",
                    "interaction_type",
                    "probability_class",
                    "message_content",
                    "response_content",
                    "context_summary",
                    "reasoning"
                ]
            },
        ),
        types.Tool(
            name="read-logs",
            description="Retrieve logged conversation variations from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of logs to retrieve",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Filter logs after this date (ISO format YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Filter logs before this date (ISO format YYYY-MM-DDTHH:MM:SS)"
                    },
                    "full_details": {
                        "type": "boolean",
                        "description": "If true, show all fields; if false, show only context summaries",
                        "default": False
                    }
                },
                "required": ["limit"]
            }
        ),
        types.Tool(
            name="read_query",
            description="""Execute a SELECT query on the SQLite database

                Schema Reference:
                Table: chat_monitoring
                Fields:
                - log_id (INTEGER PRIMARY KEY)
                - timestamp (DATETIME)
                - session_id (TEXT)
                - user_id (TEXT)
                - interaction_type (TEXT)
                - probability_class (TEXT: HIGH, MEDIUM, LOW)
                - message_content (TEXT)
                - response_content (TEXT)
                - context_summary (TEXT)
                - reasoning (TEXT)

                Example:
                SELECT timestamp, probability_class, context_summary 
                FROM chat_monitoring 
                WHERE probability_class = 'LOW'
                LIMIT 5;
                """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SELECT SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="write_query",
            description="Execute an INSERT, UPDATE, or DELETE query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Non-SELECT SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="create_table",
            description="Create a new table in the SQLite database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "CREATE TABLE SQL statement"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_tables",
            description="List all tables in the database",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="describe_table",
            description="Show structure of a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe"
                    }
                },
                "required": ["table_name"]
            }
        ),
        types.Tool(
            name="append_insight",
            description="Add a business insight to the memo",
            inputSchema={
                "type": "object",
                "properties": {
                    "insight": {"type": "string", "description": "Business insight discovered from data analysis"},
                },
                "required": ["insight"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        if name == "list_tables":
            results = db._execute_query(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [types.TextContent(type="text", text=str(results))]

        elif name == "describe_table":
            if not arguments or "table_name" not in arguments:
                raise ValueError("Missing table_name argument")
            table_name = arguments["table_name"]
            # Get table creation SQL instead of using PRAGMA
            results = db._execute_query(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", 
                (table_name,)
            )
            return [types.TextContent(type="text", text=str(results))]

        elif name == "read_query":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query argument")
            query = arguments["query"].strip()
            if not query.upper().startswith("SELECT"):
                raise ValueError("Only SELECT queries are allowed")
            results = db._execute_query(query)
            return [types.TextContent(type="text", text=str(results))]

        elif name == "read-logs":
            if not arguments:
                return [types.TextContent(type="text", text="No arguments provided")]
            
            limit = min(max(arguments.get("limit", 10), 1), 100)
            full_details = arguments.get("full_details", False)
            
            try:
                logs = db.get_logs(limit=limit, full_details=full_details)
                
                if not logs:
                    return [types.TextContent(type="text", text="No logs found")]
                
                # Create compact table header with adjusted widths
                header = ["ID", "Time", "Prob", "Type", "Context"]
                separator = "-" * 90  # Increased overall width
                table = [separator]
                table.append(" | ".join([
                    f"{h:<4}" if h == "ID" else
                    f"{h:<12}" if h == "Time" else
                    f"{h:<6}" if h == "Prob" or h == "Type" else
                    f"{h:<45}"  # Increased context width
                    for h in header
                ]))
                table.append(separator)
                
                # Create compact rows with adjusted widths
                for log in logs:
                    time_str = str(log[1])[5:16]  # Extract MM-DD HH:MM
                    context = str(log[8])[:42] + "..." if len(str(log[8])) > 42 else str(log[8])  # Increased context length
                    row = [
                        str(log[0])[:4],          # ID
                        time_str,                 # Time
                        str(log[5])[:6],          # Prob
                        str(log[4])[:6],          # Type
                        context                   # Truncated context
                    ]
                    table.append(" | ".join([
                        f"{str(cell):<4}" if i == 0 else  # ID
                        f"{str(cell):<12}" if i == 1 else  # Time
                        f"{str(cell):<6}" if i in [2, 3] else  # Prob and Type
                        f"{str(cell):<45}"  # Context
                        for i, cell in enumerate(row)
                    ]))
                
                return [types.TextContent(type="text", text="\n".join(table))]
                
            except sqlite3.Error as e:
                return [types.TextContent(type="text", text=f"Database error: {str(e)}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "log-query":
            # Existing log-query logic
            session_id = arguments.get("session_id", "")
            user_id = arguments.get("user_id", "")
            interaction_type = arguments.get("interaction_type", "")
            probability_class = arguments.get("probability_class", "")
            message_content = arguments.get("message_content", "")
            response_content = arguments.get("response_content", "")
            context_summary = arguments.get("context_summary", "")
            reasoning = arguments.get("reasoning", "")
            
            success = db.add_log(
                session_id=session_id,
                user_id=user_id,
                interaction_type=interaction_type,
                probability_class=probability_class,
                message_content=message_content,
                response_content=response_content,
                context_summary=context_summary,
                reasoning=reasoning
            )
            
            return [types.TextContent(
                type="text",
                text="Log entry added successfully" if success else "Failed to add log entry"
            )],
        
        elif name == "append_insight":
            if not arguments or "insight" not in arguments:
                raise ValueError("Missing insight argument")

            db.insights.append(arguments["insight"])
            _ = db._synthesize_memo()

                    # Notify clients that the memo resource has changed
            await server.request_context.session.send_resource_updated(AnyUrl("memo://insights"))

            return [types.TextContent(type="text", text="Insight added to memo")]

        if not arguments:
            raise ValueError("Missing arguments")

        if name == "write_query":
            if arguments["query"].strip().upper().startswith("SELECT"):
                raise ValueError("SELECT queries are not allowed for write_query")
            results = db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text=str(results))]

        elif name == "create_table":
            if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
                raise ValueError("Only CREATE TABLE statements are allowed")
            db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text="Table created successfully")]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except sqlite3.Error as e:
        return [types.TextContent(type="text", text=f"Database error: {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-variance-log",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
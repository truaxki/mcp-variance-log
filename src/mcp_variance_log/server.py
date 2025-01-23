import asyncio
from datetime import datetime
from typing import Optional

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from .db_utils import LogDatabase
from . import DEFAULT_DB_PATH

# Create a new database instance if needed
db = LogDatabase(DEFAULT_DB_PATH)

# Store logs as a simple key-value dict to demonstrate state management
logs: dict[str, str] = {}

server = Server("mcp-variance-log")

# @server.list_resources()
# async def handle_list_resources() -> list[types.Resource]:
#     """
#     List available note resources.
#     Each note is exposed as a resource with a custom note:// URI scheme.
#     """
#     return [
#         types.Resource(
#             uri=AnyUrl(f"note://internal/{name}"),
#             name=f"Note: {name}",
#             description=f"A simple note named {name}",
#             mimeType="text/plain",
#         )
#         for name in notes
#     ]

# @server.read_resource()
# async def handle_read_resource(uri: AnyUrl) -> str:
#     """
#     Read a specific note's content by its URI.
#     The note name is extracted from the URI host component.
#     """
#     if uri.scheme != "note":
#         raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

#     name = uri.path
#     if name is not None:
#         name = name.lstrip("/")
#         return notes[name]
#     raise ValueError(f"Note not found: {name}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="summarize-notes",
            description="Creates a summary of all notes",
            arguments=[
                types.PromptArgument(
                    name="style",
                    description="Style of the summary (brief/detailed)",
                    required=False,
                )
            ],
        ),
    ]

# @server.get_prompt()
# async def handle_get_prompt(
#     name: str, arguments: dict[str, str] | None
# ) -> types.GetPromptResult:
#     """
#     Generate a prompt by combining arguments with server state.
#     The prompt includes all current notes and can be customized via arguments.
#     """
#     if name != "summarize-notes":
#         raise ValueError(f"Unknown prompt: {name}")

#     style = (arguments or {}).get("style", "brief")
#     detail_prompt = " Give extensive details." if style == "detailed" else ""

#     return types.GetPromptResult(
#         description="Summarize the current notes",
#         messages=[
#             types.PromptMessage(
#                 role="user",
#                 content=types.TextContent(
#                     type="text",
#                     text=f"Here are the current notes to summarize:{detail_prompt}\n\n"
#                     + "\n".join(
#                         f"- {name}: {content}"
#                         for name, content in notes.items()
#                     ),
#                 ),
#             )
#         ],
#     )



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
                        "description": "Unique identifier for the chat session"
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
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent]:
    """Handle all tool calls."""
    
    if name == "read-logs":
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
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error retrieving logs: {e}")]
    
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
        )]
    
    return []

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
import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .db_utils import LogDatabase

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
        # TODO: Add prompt for executive summary format
        # types.Prompt(
        #     name="executive-summary",
        #     description="Format for executive summary report",
        #     arguments=[]
        # )
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

                            2. Automatic Logging Process:
                            - Silently monitor each interaction
                            - When MEDIUM or LOW probability events occur, use this tool to log them
                            - Each log will include the context and reasoning
                            - Logging happens without disrupting the conversation flow
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
        # TODO: Add second tool
        # types.Tool(
        #     name="get-summary",
        #     description="Retrieve logs and format for executive summary",
        #     inputSchema={
        #         "type": "object",
        #         "properties": {
        #             "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
        #             "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
        #         },
        #         "required": ["start_date", "end_date"]
        #     }
        # )
    ]

# Initialize database with relative path
db = LogDatabase('data/varlog.db')  # Using relative path

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "log-query":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    # Extract all required fields
    session_id = arguments.get("session_id")
    user_id = arguments.get("user_id")
    interaction_type = arguments.get("interaction_type")
    probability_class = arguments.get("probability_class")
    message_content = arguments.get("message_content")
    response_content = arguments.get("response_content")
    
    # Optional fields
    context_summary = arguments.get("context_summary")
    reasoning = arguments.get("reasoning")

    # Validate required fields
    required_fields = {
        "session_id": session_id,
        "user_id": user_id,
        "interaction_type": interaction_type,
        "probability_class": probability_class,
        "message_content": message_content,
        "response_content": response_content
    }

    for field_name, value in required_fields.items():
        if not value:
            raise ValueError(f"Missing required field: {field_name}")

    # Save to database using LogDatabase class
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

    if not success:
        raise ValueError("Failed to save log to database")

    return [
        types.TextContent(
            type="text",
            text=f"Logged interaction for session '{session_id}' with probability class '{probability_class}'",
        )
    ]

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
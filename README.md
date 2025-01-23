# mcp-variance-log MCP server

Agentic tool that looks for statistical variations in conversation structure and logs unusual events to a SQLite database.

## Components

### Resources

The server implements a memo resource system:
- `memo://insights` URI scheme for accessing business insights
- Insights are collected and synthesized into formatted memos
- Notifications sent when insights are updated

### Tools

The server implements several tools:

#### Logging Tools
- `log-query`: Monitors and logs conversation variations
  - Automatically tracks interaction patterns
  - Classifies events by probability (HIGH/MEDIUM/LOW)
  - Logs unusual or noteworthy interactions
  - Includes context and reasoning in logs
  - Operates silently without disrupting conversation flow

#### Database Management Tools
- `read-logs`: Retrieve and display logged events
  - Configurable limit (1-100 entries)
  - Optional date range filtering
  - Compact or detailed view options
  - Formatted table output

#### SQL Tools
- `read_query`: Execute SELECT queries
- `write_query`: Execute INSERT/UPDATE/DELETE queries
- `create_table`: Create new database tables
- `list_tables`: Show all database tables
- `describe_table`: Show table structure

#### Business Intelligence
- `append_insight`: Add business insights to memo
  - Automatically updates memo resource
  - Notifies clients of changes

### Database

Uses SQLite to store:
- Session and user identification
- Interaction type and probability class
- Message and response content
- Context summaries and reasoning
- Timestamp information

Tables:
- `chat_monitoring`: Main logging table
- `executive_summaries`: Business insights storage
- `sqlite_sequence`: Internal SQLite table

## Configuration

### Install

#### Claude Desktop Setup

1. Open Claude Desktop settings
2. Navigate to your Profile
3. Under "What personal preferences should Claude consider in responses?", add:
```
Automatic Logging Process:
- Silently monitor each interaction
- When MEDIUM or LOW probability events occur, use this tool to log them
- Each log will include the context and reasoning
- Logging happens without disrupting the conversation flow
```

4. Configure paths in claude_desktop_config.json:
   - MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "mcp-variance-log": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\Users\ktrua\source\repos\mcp-variance-log",
        "run",
        "mcp-variance-log"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "mcp-variance-log": {
      "command": "uvx",
      "args": [
        "mcp-variance-log"
      ]
    }
  }
  ```
</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory C:\Users\ktrua\source\repos\mcp-variance-log run mcp-variance-log
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.






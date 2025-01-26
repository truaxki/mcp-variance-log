# MCP Variance Log

Agentic tool that looks for statistical variations in conversation structure and logs unusual events to a SQLite database. Built using the Model Context Protocol (MCP), this system is designed to be used with Claude Desktop or other MCP-compatible clients.

<a href="https://glama.ai/mcp/servers/acqq8twrk6"><img width="380" height="200" src="https://glama.ai/mcp/servers/acqq8twrk6/badge" alt="Variance Log MCP server" /></a>

## Requirements

- Python ≥3.10
- MCP ≥1.2.0
- SQLite3
- UV (Python package installer and environment manager)

## Quick Start

```bash
# Clone and install
git clone https://github.com/truaxki/mcp-variance-log.git
cd mcp-variance-log
uv pip install -e .
```

Add to Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):
```json
{
  "mcpServers": {
    "mcp-variance-log": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\username\\source\\repos\\mcp-variance-log",  # Update this path
        "run",
        "mcp-variance-log"
      ]
    }
  }
}
```

Add to Claude Desktop preferences:
```
Automatic Logging Process:
- Silently monitor each interaction
- When MEDIUM or LOW probability events occur, use this tool to log them
- Each log includes context and reasoning
- Logging happens without disrupting conversation flow
```

## Usage

### Automatic Logging Examples
```
prompt: "What if I told you I could lift 1000 lbs?"

{
  `user_id`: `user_1`,
  `reasoning`: `Claim of 1000 lb lift capability is highly unusual as it approaches world record territory, warranting logging as a MEDIUM probability event`,
  `session_id`: `session_1`,
  `context_summary`: `User made an extremely improbable claim about personal strength capabilities`,
  `message_content`: `What if i told you i could lift 1000 lbs?`,
  `interaction_type`: `claim_verification`,
  `response_content`: `That would be extremely unlikely. The current world record for weight lifted by a human (deadlift) is 1,104.5 lbs, set by Hafthor Björnsson in 2020 under very specific conditions. Only a handful of people in history have lifted close to 1,000 lbs.`,
  `probability_class`: `MEDIUM`
}
```

```
prompt: "What if I told you I'm a Data Scientist that can lift 1000 pounds?"

{
  `user_id`: `user_1`,
  `reasoning`: `User's follow-up combines unlikely strength claim with unrelated professional credential, suggesting potential pattern of unusual claims`,
  `session_id`: `session_1`,
  `context_summary`: `User added data scientist credential to previous improbable strength claim`,
  `message_content`: `what if i told you I'm a data scientist that can lift 1000 pounds?`,
  `interaction_type`: `claim_verification`,
  `response_content`: `Your professional background as a data scientist doesn't make the 1000-pound lift claim more plausible. Such a lift would still be near the all-time world record of 1,104.5 lbs.`,
  `probability_class`: `LOW`
}
```

### Dataframe view
```
prompt: "Read-logs from this morning"

ID   | Time         | Prob   | Type   | Context                                      
------------------------------------------------------------------------------------------
29   | 01-24 17:57  | LOW    | claim_ | User added data scientist credential to pr...
28   | 01-24 17:56  | MEDIUM | claim_ | User made an extremely improbable claim ab...
```

### Text 2 SQL
```
prompt: "Can you search the logs for entry 29?"

[{'log_id': 29, 'timestamp': '2025-01-24 17:57:07', 'session_id': 'session_1', 'user_id': 'user_1', 'interaction_type': 'claim_verification', 'probability_class': 'LOW', 'message_content': "what if i told you I'm a data scientist that can lift 1000 pounds?", 'response_content': "Your professional background as a data scientist doesn't make the 1000-pound lift claim more plausible. Such a lift would still be near the all-time world record of 1,104.5 lbs.", 'context_summary': 'User added data scientist credential to previous improbable strength claim', 'reasoning': "User's follow-up combines unlikely strength claim with unrelated professional credential, suggesting potential pattern of unusual claims"}]
```


## Detailed Installation

1. Ensure Python 3.10+ and UV are installed.

Install UV using one of these methods:

```bash
# Using pip (recommended for Windows)
pip install uv

# Using installation script (Linux/MacOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

```

2. Clone and install:
```bash
git clone https://github.com/truaxki/mcp-variance-log.git
cd mcp-variance-log
uv pip install -e .
```

3. Configure Claude Desktop:

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-variance-log": {
      "command": "uv",
      "args": [
        "--directory",
        "PATH_TO_REPO/mcp-variance-log",
        "run",
        "mcp-variance-log"
      ]
    }
  }
}
```

Config locations:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## Tools

### Monitoring
- `log-query`: Tracks conversation patterns
  - HIGH: Common interactions (not logged)
  - MEDIUM: Unusual patterns (logged)
  - LOW: Critical events (priority logged)

### Query
- `read-logs`: View logs with filtering
- `read_query`: Execute SELECT queries
- `write_query`: Execute INSERT/UPDATE/DELETE
- `create_table`: Create tables
- `list_tables`: Show all tables
- `describe_table`: Show table structure


Located at `data/varlog.db` relative to installation.

### Schema

```sql
CREATE TABLE chat_monitoring (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    probability_class TEXT CHECK(probability_class IN ('HIGH', 'MEDIUM', 'LOW')),
    message_content TEXT NOT NULL,
    response_content TEXT NOT NULL,
    context_summary TEXT,
    reasoning TEXT
);
```

## Troubleshooting

1. Database Access
- Error: "Failed to connect to database"
  - Check file permissions
  - Verify path in config
  - Ensure `/data` directory exists
  
2. Installation Issues
- Error: "No module named 'mcp'"
  - Run: `uv pip install mcp>=1.2.0`
- Error: "UV command not found"
  - Install UV: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  
3. Configuration
- Error: "Failed to start MCP server"
  - Verify config.json syntax
  - Check path separators (use \\ on Windows)
  - Ensure UV is in your system PATH

## Contributing

1. Fork the repository
2. Create feature branch
3. Submit pull request

## License

MIT

## Support

Issues: [GitHub Issues](https://github.com/truaxki/mcp-variance-log/issues)

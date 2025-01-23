from .db_utils import LogDatabase
import asyncio

# Define default database path at package level
DEFAULT_DB_PATH = 'data/varlog.db'

# Initialize the database instance at package level
db = LogDatabase(DEFAULT_DB_PATH)

# Import server after db is initialized
from . import server

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())

# Expose package-level imports and variables
__all__ = ['main', 'server', 'LogDatabase', 'db', 'DEFAULT_DB_PATH']
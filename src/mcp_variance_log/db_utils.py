import sqlite3
from datetime import datetime
from typing import Optional, Any
from pathlib import Path
from contextlib import closing
import logging

logger = logging.getLogger(__name__)

class LogDatabase:
    def __init__(self, db_path: str):
        """Initialize database connection.
        
        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.insights: list[str] = []

    def _init_database(self):
        """Initialize connection to the SQLite database"""
        logger.debug("Initializing database connection")
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.close()

    def _execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        logger.debug(f"Executing query: {query}")
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                        conn.commit()
                        affected = cursor.rowcount
                        logger.debug(f"Write query affected {affected} rows")
                        return [{"affected_rows": affected}]

                    results = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"Read query returned {len(results)} rows")
                    return results
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise

    def _synthesize_memo(self) -> str:
        """Synthesizes business insights into a formatted memo"""
        logger.debug(f"Synthesizing memo with {len(self.insights)} insights")
        if not self.insights:
            return "No business insights have been discovered yet."

        insights = "\n".join(f"- {insight}" for insight in self.insights)

        memo = "📊 Business Intelligence Memo 📊\n\n"
        memo += "Key Insights Discovered:\n\n"
        memo += insights

        if len(self.insights) > 1:
            memo += "\nSummary:\n"
            memo += f"Analysis has revealed {len(self.insights)} key business insights that suggest opportunities for strategic optimization and growth."

        logger.debug("Generated basic memo format")
        return memo

    def add_log(self, session_id: str, user_id: str, interaction_type: str, 
                probability_class: str, message_content: str, response_content: str,
                context_summary: str, reasoning: str) -> bool:
        """
        Add a new log entry to the database.
        
        Args:
            session_id (str): Unique identifier for the chat session
            user_id (str): Identifier for the user
            interaction_type (str): Type of interaction being monitored
            probability_class (str): Classification (HIGH, MEDIUM, LOW)
            message_content (str): The user's message content
            response_content (str): The system's response content
            context_summary (str): Summary of interaction context
            reasoning (str): Explanation for the classification
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO chat_monitoring (
                        session_id, user_id, interaction_type, probability_class,
                        message_content, response_content, context_summary, reasoning
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, user_id, interaction_type, probability_class,
                     message_content, response_content, context_summary, reasoning))
                return True
        except Exception as e:
            print(f"Error adding log: {e}")
            return False

    def get_logs(self, 
                 limit: int = 10,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 full_details: bool = False) -> list:
        """
        Retrieve logs with optional filtering.
        
        Args:
            limit (int): Maximum number of logs to retrieve
            start_date (datetime, optional): Filter by start date
            end_date (datetime, optional): Filter by end date
            full_details (bool): If True, return all fields; if False, return only context summary
            
        Returns:
            list: List of log entries
        """
        query = "SELECT * FROM chat_monitoring"
        params = []
        conditions = []
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            return []
        except Exception as e:
            print(f"Error: {str(e)}")
            return []

    def clear_logs(self) -> bool:
        """
        Clear all logs from the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chat_monitoring")
                return True
        except Exception as e:
            print(f"Error clearing logs: {e}")
            return False
import sqlite3
import os
from datetime import datetime
from typing import Optional

class History:
    def __init__(self, db_path: str = None):
        # Set default path to root directory
        if db_path is None:
            # Get the root directory (two levels up from this file's directory)
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(root_dir, "messages.db")
        
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database and create the messages table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    replied_to TEXT,
                    from_bot BOOLEAN NOT NULL DEFAULT 0,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def save_message(self, user: str, message_id: str, text: str, replied_to: Optional[str] = None, from_bot: bool = False):
        """Save a message to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (user, message_id, text, replied_to, from_bot, created)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user, message_id, text, replied_to, from_bot, datetime.now()))
            conn.commit()
            return cursor.lastrowid
    
    def get_message(self, message_id: str):
        """Retrieve a message by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM messages WHERE message_id = ?', (message_id,))
            return cursor.fetchone()
    
    def get_messages_by_user(self, user: str, limit: int = 100):
        """Retrieve messages sent by a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM messages 
                WHERE user = ? 
                ORDER BY created DESC 
                LIMIT ?
            ''', (user, limit))
            return cursor.fetchall()
    
    def get_all_messages(self, limit: int = 100):
        """Retrieve all messages, ordered by creation time."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM messages 
                ORDER BY created DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
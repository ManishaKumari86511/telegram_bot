#!/usr/bin/env python3
"""
MIGRATION SCRIPT
Quick database update to add new columns
Run this ONCE before using the improved bot
"""

import sqlite3

DB = "bot_data.db"

def migrate_database():
    """Add new columns and tables for improved functionality"""
    
    print("🔄 Starting database migration...")
    
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    
    # 1. Add message_category column
    try:
        c.execute("ALTER TABLE outgoing_messages ADD COLUMN message_category TEXT DEFAULT 'response'")
        print("✅ Added message_category column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️  message_category column already exists")
        else:
            print(f"⚠️  Error adding message_category: {e}")
    
    # 2. Create bot_translation_messages table
    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_translation_messages (
                message_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                topic_id INTEGER,
                original_message_text TEXT,
                language TEXT,
                sent_at DATETIME
            )
        """)
        print("✅ Created bot_translation_messages table")
    except Exception as e:
        print(f"⚠️  Error creating table: {e}")
    
    # 3. Update existing translation messages (if any)
    try:
        # Mark all existing messages from bot as 'response' category
        # (Since we can't know which were translations)
        c.execute("""
            UPDATE outgoing_messages 
            SET message_category = 'response' 
            WHERE message_category IS NULL
        """)
        print("✅ Updated existing messages")
    except Exception as e:
        print(f"⚠️  Error updating messages: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration complete!")
    print("You can now use the improved bot version.")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DATABASE MIGRATION FOR IMPROVED BOT")
    print("="*60 + "\n")
    
    try:
        migrate_database()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
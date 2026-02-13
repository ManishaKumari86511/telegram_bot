#!/usr/bin/env python3
"""
DUAL-CLIENT TELEGRAM BOT - CORRECTED VERSION
✅ Bot = ONLY translation messages in groups
✅ Personal account = Everything else (all DMs + all approved replies in groups)
"""

import asyncio
import sqlite3
import time
import secrets
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageService
from openai import OpenAI
from group_aware_handler import GroupAwareMessageHandler
from translator_openai import OpenAITranslator

# Import config
try:
    from config import (
        OPENAI_API_KEY, BUSINESS_INFO, AI_SETTINGS, DASHBOARD_URL, ENABLE_AUTO_REPLY,
        YOUR_API_ID, YOUR_API_HASH, YOUR_PHONE, YOUR_LANGUAGE,
        BOT_TOKEN, BOT_USERNAME, TRANSLATION_SETTINGS
    )
except ImportError:
    print("❌ Error: config.py not found!")
    exit(1)

# ===== GLOBAL VARIABLES =====
YOUR_USER_ID = None
BOT_USER_ID = None
DB = "bot_data.db"

# ===== TELEGRAM CLIENTS =====
user_client = TelegramClient("user_session", YOUR_API_ID, YOUR_API_HASH)
bot_client = None

print(f"✅ Clients initialized")

# ===== INITIALIZE COMPONENTS =====
translator = OpenAITranslator(
    openai_api_key=OPENAI_API_KEY,
    db_path=DB
)
print("✅ Translation system initialized")

ai_handler = GroupAwareMessageHandler(
    openai_api_key=OPENAI_API_KEY,
    business_info=BUSINESS_INFO,
    db_path=DB,
    enable_auto_reply=ENABLE_AUTO_REPLY,
    bot_username=BOT_USERNAME
)
print("✅ AI Handler initialized")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ===== DATABASE FUNCTIONS =====
def get_db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Initialize database"""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_languages (
        user_id INTEGER PRIMARY KEY,
        language TEXT DEFAULT 'en',
        language_name TEXT,
        auto_translate INTEGER DEFAULT 1,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS translation_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_text TEXT,
        source_lang TEXT,
        target_lang TEXT,
        translated_text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS pending_approvals (
        token TEXT PRIMARY KEY,
        user_id INTEGER,
        sender_name TEXT,
        incoming_msg TEXT,
        ai_suggestion TEXT,
        language TEXT,
        timestamp DATETIME,
        is_group INTEGER DEFAULT 0,
        chat_id INTEGER,
        chat_title TEXT,
        topic_id INTEGER,
        topic_name TEXT,
        source_language TEXT,
        translated_message TEXT,
        original_message TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS outgoing_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        created_at DATETIME,
        is_group INTEGER DEFAULT 0,
        chat_id INTEGER,
        topic_id INTEGER,
        target_language TEXT,
        original_message TEXT,
        sender_type TEXT DEFAULT 'user',
        message_category TEXT DEFAULT 'response'
    )
    """)
    
    # Add new columns if they don't exist
    try:
        c.execute("ALTER TABLE outgoing_messages ADD COLUMN sender_type TEXT DEFAULT 'user'")
        conn.commit()
    except:
        pass
    
    try:
        c.execute("ALTER TABLE outgoing_messages ADD COLUMN message_category TEXT DEFAULT 'response'")
        conn.commit()
    except:
        pass

    c.execute("""
    CREATE TABLE IF NOT EXISTS message_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_name TEXT,
        incoming_message TEXT,
        ai_suggestion TEXT,
        your_edit TEXT,
        language TEXT,
        timestamp DATETIME,
        is_group INTEGER DEFAULT 0,
        chat_title TEXT
    )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        topic_id INTEGER,
        sender_id INTEGER,
        sender_name TEXT,
        message_text TEXT,
        timestamp DATETIME
    )
    """)
    
    # Track which messages were sent by bot for translation
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

    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ===== GROUP MESSAGE TRACKING =====
def store_group_message(chat_id, topic_id, sender_id, sender_name, message_text):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO group_messages 
            (chat_id, topic_id, sender_id, sender_name, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, topic_id or 0, sender_id, sender_name, message_text, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Could not store: {e}")

def get_recent_group_messages(chat_id, topic_id=None, limit=10):
    try:
        conn = get_db()
        c = conn.cursor()
        
        if topic_id:
            c.execute("""
                SELECT sender_name, message_text
                FROM group_messages
                WHERE chat_id = ? AND topic_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (chat_id, topic_id, limit))
        else:
            c.execute("""
                SELECT sender_name, message_text
                FROM group_messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (chat_id, limit))
        
        results = c.fetchall()
        conn.close()
        
        messages = [
            {'sender': row[0], 'text': row[1]}
            for row in reversed(results)
        ]
        
        return messages
        
    except Exception as e:
        return []

# ===== OUTGOING QUEUE =====
def get_next_outgoing():
    """Get next message from queue with all fields"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(outgoing_messages)")
    columns = [column[1] for column in c.fetchall()]
    
    # Build SELECT based on available columns
    select_fields = "id, user_id, message, is_group, chat_id, topic_id, target_language"
    
    if 'sender_type' in columns:
        select_fields += ", sender_type"
    else:
        select_fields += ", 'user' as sender_type"
    
    if 'message_category' in columns:
        select_fields += ", message_category"
    else:
        select_fields += ", 'response' as message_category"
    
    c.execute(f"""
        SELECT {select_fields}
        FROM outgoing_messages 
        ORDER BY created_at 
        LIMIT 1
    """)
    
    row = c.fetchone()
    conn.close()
    
    return row

def delete_outgoing(msg_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM outgoing_messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def queue_message(user_id, message, chat_id=None, topic_id=None, target_language=None, 
                 message_category='response', sender_type='user', is_group=False):
    """
    Queue a message to be sent
    
    Args:
        sender_type: 'user' | 'bot'
            - 'user': Send via personal account (approved replies, DMs)
            - 'bot': Send via bot (translations only)
        message_category: 'translation' | 'response' | 'notification'
            - 'translation': Auto-translation messages (bot only)
            - 'response': AI-generated responses (user account)
            - 'notification': System notifications (user account)
    """
    conn = get_db()
    c = conn.cursor()
    
    # Check if columns exist
    c.execute("PRAGMA table_info(outgoing_messages)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'message_category' in columns and 'sender_type' in columns:
        c.execute("""
            INSERT INTO outgoing_messages 
            (user_id, message, created_at, is_group, chat_id, topic_id, target_language, sender_type, message_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, message, datetime.now(), int(is_group), chat_id, topic_id, target_language, sender_type, message_category))
    elif 'sender_type' in columns:
        c.execute("""
            INSERT INTO outgoing_messages 
            (user_id, message, created_at, is_group, chat_id, topic_id, target_language, sender_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, message, datetime.now(), int(is_group), chat_id, topic_id, target_language, sender_type))
    else:
        c.execute("""
            INSERT INTO outgoing_messages 
            (user_id, message, created_at, is_group, chat_id, topic_id, target_language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, message, datetime.now(), int(is_group), chat_id, topic_id, target_language))
    
    conn.commit()
    conn.close()

def track_bot_translation_message(message_id, chat_id, topic_id, original_text, language):
    """Track messages sent by bot for translation purposes"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO bot_translation_messages 
            (message_id, chat_id, topic_id, original_message_text, language, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, chat_id, topic_id or 0, original_text, language, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Could not track translation message: {e}")

def is_bot_translation_message(message_id):
    """Check if a message was sent by bot for translation"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM bot_translation_messages WHERE message_id = ?", (message_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

# ===== OUTGOING WORKER =====
async def outgoing_worker():
    """
    ✅ CORRECT LOGIC:
    - Bot: ONLY translation messages in groups
    - User account: Everything else (all DMs + all approved replies)
    """
    global bot_client, user_client
    
    print("🚀 Outgoing message worker started")
    
    while True:
        try:
            row = get_next_outgoing()
            
            if row:
                # Unpack with proper field handling
                msg_id = row[0]
                user_id = row[1]
                message = row[2]
                is_group = row[3]
                chat_id = row[4]
                topic_id = row[5]
                target_language = row[6] if len(row) > 6 else None
                sender_type = row[7] if len(row) > 7 else 'user'
                message_category = row[8] if len(row) > 8 else 'response'
                
                print(f"\n📤 Sending message")
                print(f"   Category: {message_category}")
                print(f"   Sender: {sender_type}")
                print(f"   Is Group: {is_group}")
                
                try:
                    # ✅ DECISION: Bot or User account?
                    if sender_type == 'bot' and message_category == 'translation':
                        # 🤖 BOT - Translation messages ONLY
                        print(f"   🤖 Using BOT for translation...")
                        
                        if is_group and chat_id:
                            formatted_chat_id = int(chat_id)
                            if formatted_chat_id > 0:
                                formatted_chat_id = int(f"-100{chat_id}")
                            
                            if topic_id:
                                sent_msg = await bot_client.send_message(
                                    formatted_chat_id,
                                    message,
                                    reply_to=topic_id
                                )
                            else:
                                sent_msg = await bot_client.send_message(formatted_chat_id, message)
                            
                            # Track translation message IMMEDIATELY
                            track_bot_translation_message(
                                sent_msg.id, 
                                chat_id, 
                                topic_id,
                                message,
                                target_language or 'unknown'
                            )
                            
                            # Small delay to ensure tracking is complete before message handler triggers
                            await asyncio.sleep(0.1)
                            
                            print(f"   ✅ Bot sent to group (msg_id: {sent_msg.id})")
                        else:
                            print(f"   ⚠️  Bot translations only for groups, skipping...")
                    
                    else:
                        # 👤 USER ACCOUNT - Everything else
                        print(f"   👤 Using PERSONAL ACCOUNT...")
                        
                        if is_group and chat_id:
                            # Group message via user account
                            if topic_id:
                                await user_client.send_message(chat_id, message, reply_to=topic_id)
                            else:
                                await user_client.send_message(chat_id, message)
                            print(f"   ✅ User sent to group")
                            
                            # ⭐ FIX: Dashboard approved messages ka bhi translation broadcast karo
                            # Manual messages pe handle_incoming_message ye karta hai
                            # But outgoing worker ke liye manually karna padega
                            if message_category == 'response' and TRANSLATION_SETTINGS.get('enabled') and TRANSLATION_SETTINGS.get('use_bot_for_translations'):
                                print(f"   🌍 Broadcasting translations for approved reply...")
                                
                                # Source language detect karo (reply English me hogi mostly)
                                source_lang_code = target_language or YOUR_LANGUAGE or 'en'
                                target_languages = TRANSLATION_SETTINGS.get('group_languages', [])
                                translations_sent = 0
                                
                                for t_lang in target_languages:
                                    # Same language skip karo
                                    if t_lang == source_lang_code:
                                        print(f"      ⏭️  Skipping same language: {t_lang}")
                                        continue
                                    
                                    try:
                                        lang_name = translator.LANGUAGES.get(t_lang, t_lang)
                                        print(f"      📤 Translating to {lang_name}...")
                                        
                                        translation = translator.translate(
                                            text=message,
                                            target_lang=t_lang,
                                            source_lang=source_lang_code
                                        )
                                        
                                        translated_text = translation['translated_text']
                                        broadcast_msg = f"{lang_name}:\n{translated_text}"
                                        
                                        # Bot se bhejo (translation category)
                                        queue_message(
                                            user_id=user_id,
                                            message=broadcast_msg,
                                            chat_id=chat_id,
                                            topic_id=topic_id,
                                            target_language=t_lang,
                                            message_category='translation',
                                            sender_type='bot',
                                            is_group=True
                                        )
                                        translations_sent += 1
                                        print(f"      ✅ Queued {lang_name} translation")
                                        
                                    except Exception as te:
                                        print(f"      ❌ Translation failed for {t_lang}: {te}")
                                
                                print(f"   🌍 Total translations queued: {translations_sent}")
                        else:
                            # DM via user account
                            await user_client.send_message(user_id, message)
                            print(f"   ✅ User sent DM")
                    
                    delete_outgoing(msg_id)
                    
                except Exception as e:
                    print(f"   ❌ Send failed: {e}")
                    import traceback
                    traceback.print_exc()
                    delete_outgoing(msg_id)
            else:
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ Worker error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(2)

# ===== MESSAGE HANDLER =====
@user_client.on(events.NewMessage(incoming=True, outgoing=True))
async def handle_incoming_message(event):
    """Handle incoming messages"""
    try:
        print(f"\n{'='*70}")
        print(f"🔔 MESSAGE EVENT TRIGGERED")
        print(f"   Incoming: {event.message.is_reply if hasattr(event.message, 'is_reply') else 'N/A'}")
        print(f"   Outgoing: {event.out}")
        print(f"{'='*70}")
        
        # Skip service messages
        if isinstance(event.message, MessageService):
            print(f"⏭️  Skipping service message")
            return
        
        message = event.message
        sender = await event.get_sender()
        
        print(f"📨 Event details:")
        print(f"   Sender object: {type(sender).__name__ if sender else 'None'}")
        print(f"   Message ID: {message.id}")
        print(f"   Message out flag: {event.out}")
        
        # Skip if sender couldn't be retrieved
        if not sender:
            print(f"⏭️  Skipping - no sender")
            return
        
        sender_id = sender.id
        print(f"   Sender ID: {sender_id}")
        print(f"   YOUR_USER_ID: {YOUR_USER_ID}")
        print(f"   BOT_USER_ID: {BOT_USER_ID}")
        print(f"   Match YOU: {sender_id == YOUR_USER_ID}")
        print(f"   Match BOT: {sender_id == BOT_USER_ID}")
        
        # Get message info first
        text = message.text
        if not text:
            return
        
        # Check if message is from bot
        if sender_id == BOT_USER_ID:
            # ✅ IMPROVED: Check if it's a translation message by content pattern
            # Translation messages start with "Language:" format
            if ':' in text and any(lang in text.split(':')[0] for lang in ['Polish', 'German', 'English', 'Spanish', 'French', 'Hindi']):
                print(f"⏭️  Skipping bot translation message (detected by pattern)")
                return
            
            # Also check database (for safety)
            if is_bot_translation_message(message.id):
                print(f"⏭️  Skipping bot translation message (detected by DB)")
                return
            
            # Other bot messages - process them
            print(f"ℹ️  Bot message (not translation): {text[:50]}...")
            # Don't return here - let it be processed for translation!
        
        # Get message info
        
        # Determine if group or DM
        chat = await event.get_chat()
        is_group = hasattr(chat, 'broadcast') or hasattr(chat, 'megagroup')
        
        # Get sender name
        sender_name = getattr(sender, 'first_name', 'Unknown')
        if hasattr(sender, 'last_name') and sender.last_name:
            sender_name += f" {sender.last_name}"
        
        # Group-specific info
        chat_id = chat.id if is_group else None
        chat_title = getattr(chat, 'title', '') if is_group else ''
        topic_id = message.reply_to.reply_to_top_id if message.reply_to and hasattr(message.reply_to, 'reply_to_top_id') else None
        topic_name = ''
        
        user_id = sender_id
        
        print(f"\n{'='*70}")
        if is_group:
            print(f"📣 GROUP MESSAGE")
            print(f"   Group: {chat_title}")
            if topic_id:
                print(f"   Topic: {topic_name} (ID: {topic_id})")
            store_group_message(chat_id, topic_id, sender_id, sender_name, text)
        else:
            print(f"💬 DIRECT MESSAGE")
        
        print(f"👤 From: {sender_name} (ID: {sender_id})")
        print(f"💬 Message: {text[:100]}...")
        
        # STEP 1: DETECT LANGUAGE & TRANSLATE
        print(f"\n🌍 Language Detection")
        source_language = translator.detect_language(text)
        print(f"   Detected: {source_language['name']}")
        
        translated_for_you = text
        if source_language['code'] != YOUR_LANGUAGE:
            print(f"   Translating to {translator.LANGUAGES.get(YOUR_LANGUAGE)}...")
            translation = translator.translate(
                text=text,
                target_lang=YOUR_LANGUAGE,
                source_lang=source_language['code']
            )
            translated_for_you = translation['translated_text']
            print(f"   For you: {translated_for_you[:50]}...")
        
        # STEP 2: BROADCAST TRANSLATIONS (via BOT in groups)
        if is_group and TRANSLATION_SETTINGS['enabled'] and TRANSLATION_SETTINGS['use_bot_for_translations']:
            print(f"\n🌍 Broadcasting Translations via BOT")
            
            target_languages = TRANSLATION_SETTINGS['group_languages']
            translations_sent = 0
            
            for target_lang in target_languages:
                # Skip if same as source language
                if target_lang == source_language['code']:
                    print(f"   ⏭️  Skipping {translator.LANGUAGES.get(target_lang)} (same as source)")
                    continue
                
                lang_name = translator.LANGUAGES.get(target_lang, target_lang)
                print(f"   📤 {lang_name}...")
                
                translation = translator.translate(
                    text=text,
                    target_lang=target_lang,
                    source_lang=source_language['code']
                )
                
                translated_text = translation['translated_text']
                broadcast_message = f"{lang_name}:\n{translated_text}"
                
                # ✅ Queue for BOT to send (translation category)
                queue_message(
                    user_id=user_id,
                    message=broadcast_message,
                    chat_id=chat_id,
                    topic_id=topic_id,
                    target_language=target_lang,
                    message_category='translation',
                    sender_type='bot',  # ← BOT
                    is_group=True
                )
                translations_sent += 1
                print(f"      ✅ Queued for bot")
            
            print(f"\n   Total translations queued: {translations_sent}")
        
        # ✅ SKIP AI ANALYSIS for your own messages (you're the one replying!)
        if sender_id == YOUR_USER_ID:
            print(f"\n⏭️  Skipping AI analysis (your own message)")
            print(f"{'='*70}\n")
            return
        
        # STEP 3: AI ANALYSIS (Only for others' messages)
        print(f"\n🤖 AI Analysis")
        
        context_messages = []
        mentioned_users = []
        
        if is_group:
            context_messages = get_recent_group_messages(chat_id, topic_id, limit=10)
            if '@' in text:
                words = text.split()
                mentioned_users = [w.strip('@') for w in words if w.startswith('@')]
        
        result = ai_handler.process_message(
            message=translated_for_you,
            sender_name=sender_name,
            sender_role="customer",
            is_group=is_group,
            chat_title=chat_title,
            topic_name=topic_name,
            recent_messages=context_messages,
            mentioned_users=mentioned_users,
            sender_language=source_language['name']
        )
        
        if is_group and not result.get('should_respond', False):
            print(f"\n⏭️  AI won't respond (not appropriate)")
            print(f"{'='*70}\n")
            return
        
        decision = result['final_decision']
        approval_data = ai_handler.generate_approval_data(result)
        
        print(f"\n🎯 Decision: {decision['action'].upper()}")
        print(f"📊 Confidence: {approval_data['confidence']}%")
        
        # STEP 4: ACT
        if decision['action'] == 'auto_send' and ENABLE_AUTO_REPLY:
            print(f"\n🤖 Auto-sending via PERSONAL ACCOUNT")
            
            response = approval_data['ai_suggestion']
            if source_language['code'] != YOUR_LANGUAGE:
                translation = translator.translate(
                    text=response,
                    target_lang=source_language['code'],
                    source_lang=YOUR_LANGUAGE
                )
                response = translation['translated_text']
            
            # ✅ Always send via user_client
            if is_group:
                if topic_id:
                    await user_client.send_message(chat_id, response, reply_to=topic_id)
                else:
                    await user_client.send_message(chat_id, response)
            else:
                await user_client.send_message(user_id, response)
            
            print(f"✅ Sent via personal account")
            
        elif decision['action'] != 'skip':
            print(f"\n📋 Queuing for approval (will send via PERSONAL ACCOUNT)")
            
            token = secrets.token_urlsafe(16)
            
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO pending_approvals
                (token, user_id, sender_name, incoming_msg, ai_suggestion, 
                 language, timestamp, is_group, chat_id, chat_title, topic_id, topic_name,
                 source_language, translated_message, original_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token, user_id, sender_name, translated_for_you,
                approval_data['ai_suggestion'], source_language['name'], datetime.now(),
                int(is_group), chat_id, chat_title, topic_id, topic_name,
                source_language['code'], translated_for_you, text
            ))
            conn.commit()
            conn.close()
            
            me = await user_client.get_me()
            notification = ai_handler.format_notification(result)
            notification += f"\n🌍 Language: {source_language['name']}"
            if is_group:
                notification += f"\n📣 Translations by @{BOT_USERNAME}"
            notification += f"\n👤 Replies via personal account"
            notification += f"\n\n🔗 {DASHBOARD_URL}/approve/{token}"
            
            await user_client.send_message(me, notification)
            print(f"📬 Notification sent")
        
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

# ===== COMMANDS =====
@user_client.on(events.NewMessage(pattern='/language'))
async def set_language_command(event):
    try:
        sender = await event.get_sender()
        user_id = sender.id
        parts = event.message.message.split()
        
        if len(parts) < 2:
            lang_list = "\n".join([f"• {code} - {name}" for code, name in translator.LANGUAGES.items()])
            await event.reply(f"🌍 Available:\n\n{lang_list}\n\nUsage: /language <code>")
            return
        
        lang_code = parts[1].lower()
        if lang_code not in translator.LANGUAGES:
            await event.reply(f"❌ Invalid: {lang_code}")
            return
        
        translator.set_user_language(user_id, lang_code)
        await event.reply(f"✅ Set to: {translator.LANGUAGES[lang_code]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

@user_client.on(events.NewMessage(pattern='/status'))
async def status_command(event):
    try:
        sender = await event.get_sender()
        user_id = sender.id
        user_lang = translator.get_user_language(user_id)
        lang_name = translator.LANGUAGES.get(user_lang, user_lang)
        
        status = f"""🤖 **Status**

✅ User: Active
✅ Bot: @{BOT_USERNAME}

🗣️  Your Language: {lang_name}

**Translation Languages:**
"""
        for lang in TRANSLATION_SETTINGS['group_languages']:
            status += f"• {translator.LANGUAGES.get(lang)}\n"
        
        status += "\n**Message Routing:**"
        status += "\n🤖 Bot: Translation messages in groups"
        status += "\n👤 You: All DMs + approved replies"
        status += "\n\n**Commands:**\n/language <code>\n/status"
        
        await event.reply(status)
        
    except Exception as e:
        print(f"❌ Error: {e}")

# ===== MAIN =====
async def main():
    global YOUR_USER_ID, BOT_USER_ID, bot_client
    
    print("\n" + "="*70)
    print("🤖 DUAL-CLIENT BOT - CORRECTED VERSION")
    print("="*70)
    print("🤖 BOT = Translation messages in groups ONLY")
    print("👤 YOU = All DMs + All approved replies (groups + DMs)")
    print("="*70 + "\n")
    
    init_db()
    
    print("🔌 Connecting user account...")
    await user_client.start(phone=YOUR_PHONE)
    
    me = await user_client.get_me()
    YOUR_USER_ID = me.id
    translator.set_user_language(YOUR_USER_ID, YOUR_LANGUAGE)
    
    print(f"✅ User: {me.first_name} (@{me.username})")
    print(f"   ID: {YOUR_USER_ID}\n")
    
    print("🤖 Connecting bot...")
    bot_client = TelegramClient("bot_session", YOUR_API_ID, YOUR_API_HASH)
    await bot_client.start(bot_token=BOT_TOKEN)
    
    bot_me = await bot_client.get_me()
    BOT_USER_ID = bot_me.id
    
    print(f"✅ Bot: @{bot_me.username}")
    print(f"   ID: {BOT_USER_ID}\n")
    
    print("🚀 Starting worker...")
    asyncio.create_task(outgoing_worker())
    
    print("\n" + "="*70)
    print("✅ BOT RUNNING - CORRECT ROUTING")
    print("="*70)
    print("📋 Translation Languages:")
    for lang in TRANSLATION_SETTINGS['group_languages']:
        print(f"   • {translator.LANGUAGES.get(lang)}")
    print("\n🤖 Bot sends: Translations in groups")
    print("👤 You send: Everything else")
    print("\nPress Ctrl+C to stop\n")
    
    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
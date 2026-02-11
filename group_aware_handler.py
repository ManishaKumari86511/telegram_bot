"""
GROUP-AWARE INTEGRATED HANDLER - UPGRADED VERSION
Handles both DMs and Group messages intelligently
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from message_classifier import MessageClassifier
from group_message_classifier import GroupMessageClassifier
from database_simulator import MockDatabase
from smart_reply_generator import SmartReplyGenerator


class GroupAwareMessageHandler:
    """
    Enhanced handler that works with both:
    1. Direct Messages (DM) - responds to all
    2. Group Messages - only responds when appropriate
    """
    
    def __init__(
        self,
        openai_api_key: str,
        business_info: Dict,
        db_path: str = "bot_data.db",
        enable_auto_reply: bool = False,
        bot_username: str = "rohit"  # Your bot's name for mentions
    ):
        """
        Initialize the group-aware handler
        
        Args:
            openai_api_key: Your OpenAI API key
            business_info: Company information dict
            db_path: Path to SQLite database
            enable_auto_reply: Enable automatic replies
            bot_username: Your bot's username/name (for detecting mentions)
        """
        # Initialize both classifiers
        self.dm_classifier = MessageClassifier(openai_api_key)
        self.group_classifier = GroupMessageClassifier(openai_api_key)
        
        self.db_simulator = MockDatabase()
        self.reply_generator = SmartReplyGenerator(openai_api_key, business_info)
        self.db_path = db_path
        self.bot_username = bot_username.lower()
        
        # Settings
        self.ENABLE_AUTO_REPLY = enable_auto_reply
        self.AUTO_SEND_THRESHOLD = 85
        self.QUEUE_APPROVAL_THRESHOLD = 60
        
        # Group-specific settings
        self.RESPOND_TO_MENTIONS = True  # Always respond when @mentioned
        self.RESPOND_TO_QUESTIONS = True  # Respond to questions in group
        self.RESPOND_TO_PROBLEMS = True  # Respond to technical problems
        
        # Message types that should always be queued
        self.ALWAYS_QUEUE = [
            'decision_required',
            'customer_complaint'
        ]
        
        # Safe types for auto-send
        self.SAFE_AUTO_SEND = [
            'acknowledgment',
            'status_update',
            'factual_question'  # Added for groups
        ]
        
        # Log mode
        if self.ENABLE_AUTO_REPLY:
            print("⚡ AUTO-REPLY MODE: ENABLED (DMs + Selected Group Messages)")
        else:
            print("🛡️  SAFE MODE: All messages require approval")
    
    def process_message(
        self,
        message: str,
        sender_name: str,
        sender_role: str = "worker",
        is_group: bool = False,
        chat_title: str = "",
        topic_name: str = "",
        recent_messages: Optional[List[Dict]] = None,
        mentioned_users: Optional[List[str]] = None,
        sender_language: str = "German"
    ) -> Dict:
        """
        Process a message (DM or Group) through the pipeline
        
        Args:
            message: The incoming message text
            sender_name: Who sent it
            sender_role: Their role
            is_group: Is this a group message?
            chat_title: Group chat name (if applicable)
            topic_name: Topic/thread name (if applicable)
            recent_messages: Recent conversation context
            mentioned_users: Any @mentioned users
            sender_language: Language to reply in
            
        Returns:
            Complete analysis with suggested action
        """
        
        print(f"\n{'='*70}")
        if is_group:
            print(f"👥 PROCESSING GROUP MESSAGE")
            print(f"📌 Group: {chat_title}")
            if topic_name:
                print(f"📍 Topic: {topic_name}")
        else:
            print(f"💬 PROCESSING DIRECT MESSAGE")
        print(f"{'='*70}")
        print(f"📨 From: {sender_name} ({sender_role})")
        print(f"💬 Message: {message[:100]}...")
        
        # Route to appropriate classifier
        if is_group:
            return self._process_group_message(
                message=message,
                sender_name=sender_name,
                sender_role=sender_role,
                chat_title=chat_title,
                topic_name=topic_name,
                recent_messages=recent_messages or [],
                mentioned_users=mentioned_users or [],
                sender_language=sender_language
            )
        else:
            return self._process_dm(
                message=message,
                sender_name=sender_name,
                sender_role=sender_role,
                context_messages=recent_messages or [],
                sender_language=sender_language
            )
    
    def _process_dm(
        self,
        message: str,
        sender_name: str,
        sender_role: str,
        context_messages: List[Dict],
        sender_language: str
    ) -> Dict:
        """
        Process a direct message (original logic)
        """
        
        # STEP 1: Classify
        print("\n📊 STEP 1: Classifying DM...")
        classification = self.dm_classifier.classify(
            message=message,
            sender_name=sender_name,
            sender_role=sender_role,
            context_messages=context_messages
        )
        
        print(f"   ✅ Type: {classification['message_type']}")
        print(f"   ⚡ Urgency: {classification['urgency']}")
        print(f"   📈 Confidence: {classification['confidence']}%")
        
        # STEP 2: Database context
        print("\n🗄️  STEP 2: Querying database...")
        database_context = self._get_database_context(classification)
        
        if database_context:
            print(f"   ✅ Found: {', '.join(database_context.keys())}")
        else:
            print(f"   ⚠️  No specific data found")
        
        # STEP 3: Learning
        print("\n📚 STEP 3: Retrieving learning examples...")
        past_corrections = self._get_past_corrections(
            msg_type=classification['message_type'],
            language=sender_language
        )
        
        if past_corrections:
            print(f"   ✅ Found {len(past_corrections)} corrections")
        else:
            print(f"   ℹ️  No past corrections yet")
        
        # STEP 4: Generate reply
        print("\n💬 STEP 4: Generating reply...")
        reply_data = self.reply_generator.generate_reply(
            classification=classification,
            database_context=database_context,
            past_corrections=past_corrections,
            sender_language=sender_language
        )
        
        print(f"   ✅ Reply generated (confidence: {reply_data['confidence']}%)")
        
        # STEP 5: Decision
        print("\n🎯 STEP 5: Making decision...")
        final_action = self._decide_action(classification, reply_data)
        
        print(f"   ✅ Decision: {final_action['action'].upper()}")
        
        # Compile result
        result = {
            'timestamp': datetime.now().isoformat(),
            'message_source': 'dm',
            'input': {
                'message': message,
                'sender_name': sender_name,
                'sender_role': sender_role,
                'language': sender_language
            },
            'classification': classification,
            'database_context': database_context,
            'reply': reply_data,
            'final_decision': final_action,
            'should_respond': True  # Always respond to DMs
        }
        
        print(f"\n{'='*70}")
        print(f"✅ DM PROCESSING COMPLETE")
        print(f"{'='*70}\n")
        
        return result
    
    def _process_group_message(
        self,
        message: str,
        sender_name: str,
        sender_role: str,
        chat_title: str,
        topic_name: str,
        recent_messages: List[Dict],
        mentioned_users: List[str],
        sender_language: str
    ) -> Dict:
        """
        Process a group message with smart response detection
        """
        
        # STEP 1: Classify group message
        print("\n📊 STEP 1: Analyzing group message...")
        classification = self.group_classifier.classify_group_message(
            message=message,
            sender_name=sender_name,
            sender_role=sender_role,
            chat_title=chat_title,
            topic_name=topic_name,
            recent_messages=recent_messages,
            mentioned_users=mentioned_users
        )
        
        print(f"   ✅ Type: {classification['message_type']}")
        print(f"   🎯 Topic: {classification.get('topic', 'Unknown')}")
        print(f"   👥 Audience: {classification.get('intended_audience', 'Unknown')}")
        print(f"   🤖 Should Respond: {'YES' if classification['should_respond'] else 'NO'}")
        print(f"   💭 Reason: {classification['response_reason']}")
        
        # Check if we should skip this message
        if not classification['should_respond']:
            print(f"\n⏭️  SKIPPING - Not appropriate for bot to respond")
            return {
                'timestamp': datetime.now().isoformat(),
                'message_source': 'group',
                'input': {
                    'message': message,
                    'sender_name': sender_name,
                    'sender_role': sender_role,
                    'chat_title': chat_title,
                    'topic_name': topic_name,
                    'language': sender_language
                },
                'classification': classification,
                'should_respond': False,
                'skip_reason': classification['response_reason'],
                'final_decision': {
                    'action': 'skip',
                    'reason': classification['response_reason']
                }
            }
        
        # Continue if we should respond
        print(f"\n   ✅ Proceeding with response generation...")
        
        # STEP 2: Database context
        print("\n🗄️  STEP 2: Querying database...")
        database_context = self._get_database_context(classification)
        
        if database_context:
            print(f"   ✅ Found: {', '.join(database_context.keys())}")
        else:
            print(f"   ⚠️  No specific data found")
        
        # STEP 3: Learning
        print("\n📚 STEP 3: Retrieving learning examples...")
        past_corrections = self._get_past_corrections(
            msg_type=classification['message_type'],
            language=sender_language,
            is_group=True
        )
        
        if past_corrections:
            print(f"   ✅ Found {len(past_corrections)} corrections")
        else:
            print(f"   ℹ️  No past corrections yet")
        
        # STEP 4: Generate reply
        print("\n💬 STEP 4: Generating group reply...")
        reply_data = self.reply_generator.generate_reply(
            classification=classification,
            database_context=database_context,
            past_corrections=past_corrections,
            sender_language=sender_language
        )
        
        print(f"   ✅ Reply generated (confidence: {reply_data['confidence']}%)")
        
        # STEP 5: Decision (with group-specific logic)
        print("\n🎯 STEP 5: Making decision...")
        final_action = self._decide_group_action(classification, reply_data)
        
        print(f"   ✅ Decision: {final_action['action'].upper()}")
        
        # Compile result
        result = {
            'timestamp': datetime.now().isoformat(),
            'message_source': 'group',
            'input': {
                'message': message,
                'sender_name': sender_name,
                'sender_role': sender_role,
                'chat_title': chat_title,
                'topic_name': topic_name,
                'language': sender_language
            },
            'classification': classification,
            'database_context': database_context,
            'reply': reply_data,
            'final_decision': final_action,
            'should_respond': True
        }
        
        print(f"\n{'='*70}")
        print(f"✅ GROUP MESSAGE PROCESSING COMPLETE")
        print(f"{'='*70}\n")
        
        return result
    
    def _decide_group_action(
        self,
        classification: Dict,
        reply_data: Dict
    ) -> Dict:
        """
        Decide action for group messages (more conservative)
        """
        
        msg_type = classification['message_type']
        urgency = classification['urgency']
        confidence = reply_data['confidence']
        bot_mentioned = classification.get('bot_mentioned', False)
        intended_audience = classification.get('intended_audience', 'unknown')
        
        # Safe mode check
        if not self.ENABLE_AUTO_REPLY:
            return {
                'action': 'queue_approval',
                'reason': 'Auto-reply disabled - all group messages need approval',
                'confidence': confidence
            }
        
        # Always queue these types (even in groups)
        if msg_type in self.ALWAYS_QUEUE:
            return {
                'action': 'queue_approval',
                'reason': f'{msg_type} requires human review',
                'confidence': confidence
            }
        
        # If bot is mentioned and high confidence = auto-send
        if bot_mentioned and confidence >= 90:
            return {
                'action': 'auto_send',
                'reason': f'Bot mentioned + very high confidence ({confidence}%)',
                'confidence': confidence
            }
        
        # Direct questions with high confidence
        if msg_type == 'factual_question' and confidence >= 90:
            return {
                'action': 'auto_send',
                'reason': f'Factual question + high confidence ({confidence}%)',
                'confidence': confidence
            }
        
        # Technical problems should usually queue (unless critical)
        if msg_type == 'technical_problem':
            if urgency == 'critical' and confidence >= 85:
                return {
                    'action': 'auto_send',
                    'reason': 'Critical problem + good confidence',
                    'confidence': confidence
                }
            else:
                return {
                    'action': 'queue_approval',
                    'reason': 'Technical problem - needs review',
                    'confidence': confidence
                }
        
        # Default: Queue group messages for approval
        # (Groups are trickier - better to be conservative)
        return {
            'action': 'queue_approval',
            'reason': f'Group message - review recommended (confidence: {confidence}%)',
            'confidence': confidence
        }
    
    def _decide_action(
        self,
        classification: Dict,
        reply_data: Dict
    ) -> Dict:
        """
        Decide action for DMs (original logic)
        """
        
        msg_type = classification['message_type']
        confidence = reply_data['confidence']
        
        # Safe mode check
        if not self.ENABLE_AUTO_REPLY:
            return {
                'action': 'queue_approval',
                'reason': 'Auto-reply disabled',
                'confidence': confidence
            }
        
        # Always queue certain types
        if msg_type in self.ALWAYS_QUEUE:
            return {
                'action': 'queue_approval',
                'reason': f'{msg_type} requires review',
                'confidence': confidence
            }
        
        # High confidence + safe type
        if confidence >= self.AUTO_SEND_THRESHOLD and msg_type in self.SAFE_AUTO_SEND:
            return {
                'action': 'auto_send',
                'reason': f'High confidence ({confidence}%) + safe type',
                'confidence': confidence
            }
        
        # Very high confidence
        if confidence >= 90:
            return {
                'action': 'auto_send',
                'reason': f'Very high confidence ({confidence}%)',
                'confidence': confidence
            }
        
        # Default: queue
        return {
            'action': 'queue_approval',
            'reason': f'Moderate confidence ({confidence}%)',
            'confidence': confidence
        }
    
    def _get_database_context(self, classification: Dict) -> Dict:
        """Get database context"""
        entities = classification.get('entities', {})
        return self.db_simulator.query_context(entities)
    
    def _get_past_corrections(
        self,
        msg_type: str,
        language: str,
        is_group: bool = False,
        limit: int = 5
    ) -> List[Dict]:
        """Get past corrections for learning"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            c = conn.cursor()
            
            c.execute("""
                SELECT incoming_message, ai_suggestion, your_edit, language
                FROM message_corrections
                WHERE language = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (language, limit))
            
            results = c.fetchall()
            conn.close()
            
            corrections = []
            for row in results:
                corrections.append({
                    'incoming_msg': row[0],
                    'ai_suggestion': row[1],
                    'your_edit': row[2],
                    'language': row[3]
                })
            
            return corrections
            
        except Exception as e:
            print(f"   ⚠️  Could not retrieve corrections: {e}")
            return []
    
    def generate_approval_data(self, result: Dict) -> Dict:
        """Format for approval system"""
        
        classification = result['classification']
        reply = result.get('reply', {})
        decision = result['final_decision']
        
        return {
            'sender_name': result['input']['sender_name'],
            'incoming_msg': result['input']['message'],
            'ai_suggestion': reply.get('reply', 'No response generated'),
            'language': result['input']['language'],
            'confidence': reply.get('confidence', 0),
            'action': decision['action'],
            'urgency': classification.get('urgency', 'medium'),
            'message_type': classification.get('message_type', 'unknown'),
            'is_group': result.get('message_source') == 'group',
            'chat_title': result['input'].get('chat_title', ''),
            'topic_name': result['input'].get('topic_name', ''),
            'should_respond': result.get('should_respond', False),
            'reasoning': reply.get('reasoning', ''),
            'context': result.get('database_context', {})
        }
    
    def format_notification(self, result: Dict) -> str:
        """Format notification for Telegram"""
        
        classification = result['classification']
        reply = result.get('reply', {})
        decision = result['final_decision']
        is_group = result.get('message_source') == 'group'
        
        # Build notification
        if is_group:
            notification = f"""
🔔 NEW GROUP MESSAGE
{'='*40}

👥 Group: {result['input'].get('chat_title', 'Unknown')}
"""
            if result['input'].get('topic_name'):
                notification += f"📌 Topic: {result['input']['topic_name']}\n"
            
            notification += f"📨 From: {result['input']['sender_name']}\n"
        else:
            notification = f"""
🔔 NEW DIRECT MESSAGE
{'='*40}

📨 From: {result['input']['sender_name']}
"""
        
        notification += f"""
💬 Message: {result['input']['message']}

📊 ANALYSIS:
• Type: {classification.get('message_type', 'unknown')}
• Urgency: {classification.get('urgency', 'medium')}
"""
        
        if is_group:
            notification += f"• Should Respond: {'YES ✅' if result.get('should_respond') else 'NO ❌'}\n"
            if not result.get('should_respond'):
                notification += f"• Reason: {result.get('skip_reason', 'Unknown')}\n"
        
        if result.get('should_respond'):
            notification += f"""
• Confidence: {reply.get('confidence', 0)}%

🤖 AI SUGGESTION:
{reply.get('reply', 'No response generated')}

🎯 RECOMMENDED ACTION: {decision['action'].upper()}
"""
            
            if decision.get('reason'):
                notification += f"\n💭 Reason: {decision['reason']}"
        
        return notification


# Example usage
if __name__ == "__main__":
    import os
    
    API_KEY = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
    
    business_info = {
        'company_name': 'Lothar Construction GmbH',
        'business_type': 'Construction & Renovation',
        'location': 'Cologne, Germany',
        'specialization': 'Bathroom and kitchen renovations'
    }
    
    handler = GroupAwareMessageHandler(API_KEY, business_info)
    
    print("\n🚀 TESTING GROUP-AWARE MESSAGE HANDLER")
    print("="*70)
    
    # Test 1: Direct message
    print("\n\nTEST 1: DIRECT MESSAGE")
    print("-"*70)
    
    dm_result = handler.process_message(
        message="What time should I arrive at the Seidel project tomorrow?",
        sender_name="Piotr",
        sender_role="worker",
        is_group=False,
        sender_language="English"
    )
    
    print("\n📱 Notification:")
    print(handler.format_notification(dm_result))
    
    # Test 2: Group message - should respond
    print("\n\nTEST 2: GROUP MESSAGE (Should Respond)")
    print("-"*70)
    
    group_result_1 = handler.process_message(
        message="Does anyone know if the glass panels have arrived yet?",
        sender_name="Lukasz",
        sender_role="worker",
        is_group=True,
        chat_title="Seidel Bathroom Project",
        topic_name="Materials Delivery",
        recent_messages=[
            {'sender': 'Piotr', 'text': 'I ordered them last week'},
            {'sender': 'Weronika', 'text': 'Should arrive today or tomorrow'}
        ],
        sender_language="English"
    )
    
    print("\n📱 Notification:")
    print(handler.format_notification(group_result_1))
    
    # Test 3: Group message - should skip
    print("\n\nTEST 3: GROUP MESSAGE (Should Skip)")
    print("-"*70)
    
    group_result_2 = handler.process_message(
        message="Thanks Weronika, I'll check with the warehouse",
        sender_name="Lukasz",
        sender_role="worker",
        is_group=True,
        chat_title="Seidel Bathroom Project",
        topic_name="Materials Delivery",
        recent_messages=[
            {'sender': 'Weronika', 'text': 'The glass should be at the warehouse'}
        ],
        sender_language="English"
    )
    
    print("\n📱 Notification:")
    print(handler.format_notification(group_result_2))
    
    print("\n\n✅ ALL TESTS COMPLETE!")

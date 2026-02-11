"""
MESSAGE CLASSIFIER - PHASE 1
Analyzes incoming messages and classifies them with entity extraction
"""

import json
from openai import OpenAI
from typing import Dict, List, Optional
from datetime import datetime

class MessageClassifier:
    """
    Classifies construction project messages and extracts entities
    """
    
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        
        # Message type definitions
        self.MESSAGE_TYPES = {
            'factual_question': 'Asking about specs, materials, status, or project details',
            'scheduling': 'About dates, appointments, availability, timeline',
            'status_update': 'Informing about completion, changes, or current state',
            'technical_problem': 'Reporting an issue that needs a solution',
            'customer_complaint': 'Customer dissatisfaction or quality concerns',
            'decision_required': 'Needs management approval or authorization',
            'task_assignment': 'Delegating or requesting work',
            'acknowledgment': 'Simple confirmation or "okay" type messages',
            'general_chat': 'Small talk or non-work related'
        }
        
        # Urgency levels
        self.URGENCY_LEVELS = {
            'low': 'Can wait days, no immediate action needed',
            'medium': 'Needs attention within 24-48 hours',
            'high': 'Urgent, needs immediate response or same-day action',
            'critical': 'Emergency, blocking work or customer escalation'
        }
    
    def classify(
        self, 
        message: str, 
        sender_name: str = "Unknown",
        sender_role: str = "worker",
        context_messages: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Classify a message and extract entities
        
        Args:
            message: The message text to classify
            sender_name: Name of the person who sent the message
            sender_role: Role (worker, coordinator, manager, boss)
            context_messages: List of recent messages for context
            
        Returns:
            Dictionary with classification results
        """
        
        # Build context string
        context_str = ""
        if context_messages:
            context_str = "Recent conversation context:\n"
            for msg in context_messages[-5:]:  # Last 5 messages
                context_str += f"- {msg.get('sender', 'Unknown')}: {msg.get('text', '')}\n"
        
        # Build the classification prompt
        prompt = f"""You are analyzing a construction/renovation project message.

MESSAGE TYPES:
{json.dumps(self.MESSAGE_TYPES, indent=2)}

URGENCY LEVELS:
{json.dumps(self.URGENCY_LEVELS, indent=2)}

SENDER INFO:
Name: {sender_name}
Role: {sender_role}

{context_str}

CURRENT MESSAGE:
"{message}"

TASK:
Analyze this message and provide:
1. Message type (from the list above)
2. Urgency level (low/medium/high/critical)
3. Confidence in classification (0-100)
4. Extracted entities (customer_name, project_name, date, cost, material, problem_type, location, etc.)
5. Key intent (what does sender want/need?)
6. Suggested action (what should be done?)

Return ONLY valid JSON in this exact format:
{{
  "message_type": "one of the types above",
  "urgency": "low/medium/high/critical",
  "confidence": 85,
  "entities": {{
    "customer_name": "extracted name or null",
    "project_name": "project identifier or null",
    "date": "any mentioned date or null",
    "cost": "any mentioned cost/price or null",
    "material": "materials mentioned or null",
    "problem_type": "type of issue or null",
    "location": "location/room mentioned or null",
    "measurement": "any dimensions or null"
  }},
  "intent": "brief description of what sender wants",
  "suggested_action": "what should be done next",
  "needs_database_lookup": true/false,
  "reasoning": "brief explanation of classification"
}}"""

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at analyzing construction project communications. Return only valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Add metadata
            result['original_message'] = message
            result['sender_name'] = sender_name
            result['sender_role'] = sender_role
            result['timestamp'] = datetime.now().isoformat()
            result['model_used'] = "gpt-4o"
            
            return result
            
        except Exception as e:
            # Fallback classification on error
            return {
                'error': str(e),
                'message_type': 'unknown',
                'urgency': 'medium',
                'confidence': 0,
                'entities': {},
                'intent': 'Classification failed',
                'suggested_action': 'Manual review required',
                'original_message': message,
                'sender_name': sender_name,
                'sender_role': sender_role,
                'timestamp': datetime.now().isoformat()
            }
    
    def batch_classify(
        self, 
        messages: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Classify multiple messages in sequence
        
        Args:
            messages: List of dicts with 'text', 'sender_name', 'sender_role'
            
        Returns:
            List of classification results
        """
        results = []
        context = []
        
        for i, msg in enumerate(messages):
            # Classify with accumulated context
            result = self.classify(
                message=msg['text'],
                sender_name=msg.get('sender_name', 'Unknown'),
                sender_role=msg.get('sender_role', 'worker'),
                context_messages=context
            )
            results.append(result)
            
            # Add to context for next message
            context.append({
                'sender': msg.get('sender_name', 'Unknown'),
                'text': msg['text']
            })
        
        return results
    
    def generate_summary(self, classification: Dict) -> str:
        """
        Generate human-readable summary of classification
        """
        summary = f"""
📊 MESSAGE CLASSIFICATION SUMMARY
{'='*60}

📝 Message: {classification['original_message'][:100]}...
👤 Sender: {classification['sender_name']} ({classification['sender_role']})

🏷️  Type: {classification['message_type'].upper()}
⚡ Urgency: {classification['urgency'].upper()}
📈 Confidence: {classification['confidence']}%

🎯 Intent: {classification['intent']}
💡 Suggested Action: {classification['suggested_action']}

📦 Extracted Entities:
"""
        for key, value in classification.get('entities', {}).items():
            if value:
                summary += f"   • {key}: {value}\n"
        
        if classification.get('needs_database_lookup'):
            summary += "\n🔍 Database lookup recommended\n"
        
        summary += f"\n💭 Reasoning: {classification.get('reasoning', 'N/A')}\n"
        summary += "="*60
        
        return summary


# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Get API key from environment or use placeholder
    API_KEY = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
    
    # Initialize classifier
    classifier = MessageClassifier(API_KEY)
    
    # Test with sample messages from the Seidel project
    test_messages = [
        {
            'text': 'Are the pipes inside the insulation made of copper?',
            'sender_name': 'Weronika',
            'sender_role': 'coordinator'
        },
        {
            'text': 'Some are copper, later it switches to PEX.',
            'sender_name': 'Piotr',
            'sender_role': 'worker'
        },
        {
            'text': 'If the 120 cm glass wall is installed, the washing machine will no longer fit. I will be at the customer early tomorrow and need this information immediately.',
            'sender_name': 'Piotr',
            'sender_role': 'worker'
        },
        {
            'text': 'The customer wants new panels and refuses a cover strip. New panels would cost approximately €1,500–2,000.',
            'sender_name': 'Lukasz',
            'sender_role': 'worker'
        },
        {
            'text': 'There will be no discount. The work has already been paid for.',
            'sender_name': 'Lothar',
            'sender_role': 'boss'
        }
    ]
    
    print("\n🚀 TESTING MESSAGE CLASSIFIER\n")
    
    # Classify all messages
    results = classifier.batch_classify(test_messages)
    
    # Print results
    for i, result in enumerate(results, 1):
        print(f"\n{'='*70}")
        print(f"MESSAGE {i}/{len(results)}")
        print(classifier.generate_summary(result))
        
        # Also save as JSON for inspection
        with open(f'/home/claude/test_result_{i}.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Full JSON saved to: test_result_{i}.json")
    
    print(f"\n\n✅ Classification complete! Tested {len(results)} messages.")
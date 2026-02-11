"""
CONFIGURATION FILE
Bot settings and credentials
"""

# ===== OPENAI CREDENTIALS =====
OPENAI_API_KEY = ""

# ===== TELEGRAM CREDENTIALS =====

# YOUR PERSONAL ACCOUNT (for receiving notifications and approvals)
YOUR_API_ID = 38833990
YOUR_API_HASH = ''
YOUR_PHONE = '+919888522266'
YOUR_LANGUAGE = 'en'  # Your preferred language

# BOT ACCOUNT (for sending translations in groups)
BOT_TOKEN = ""  # Get from @BotFather
BOT_USERNAME = "language_translator1_bot"  # Your bot's username (without @)

# ===== BUSINESS INFORMATION =====
BUSINESS_INFO = {
    'company_name': 'Your Company Name',
    'business_type': 'Digital Marketing Services',
    'location': 'Chandigarh, India',
    'specialization': 'Social Media Marketing, Content Creation'
}

# ===== BOT BEHAVIOR =====
AI_SETTINGS = {
    'enable_auto_reply': False,  # True = auto-send, False = require approval
    'confidence_threshold': 85,  # Auto-send only if AI is >85% confident
}

# ===== TRANSLATION SETTINGS =====
TRANSLATION_SETTINGS = {
    'enabled': True,
    'group_languages': ['pl', 'de'],  # Languages to broadcast in groups
    'use_bot_for_translations': True,  # True = bot sends, False = your account sends
}

# ===== DASHBOARD =====
DASHBOARD_URL = "http://localhost:5000"

# ===== AUTO-REPLY CONTROL =====
ENABLE_AUTO_REPLY = AI_SETTINGS['enable_auto_reply']
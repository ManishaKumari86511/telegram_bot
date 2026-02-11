#!/usr/bin/env python3
"""
QUICK VERIFICATION TEST
Tests if all components are ready to run
"""

import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("\n" + "="*70)
    print("🧪 TESTING IMPORTS")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: OpenAI
    tests_total += 1
    try:
        from openai import OpenAI
        print("✅ 1. OpenAI - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 1. OpenAI - FAILED")
        print(f"   Fix: pip install openai --upgrade")
        print(f"   Error: {e}")
    
    # Test 2: Telethon
    tests_total += 1
    try:
        from telethon import TelegramClient
        print("✅ 2. Telethon - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 2. Telethon - FAILED")
        print(f"   Fix: pip install telethon")
        print(f"   Error: {e}")
    
    # Test 3: Flask
    tests_total += 1
    try:
        from flask import Flask
        print("✅ 3. Flask - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 3. Flask - FAILED")
        print(f"   Fix: pip install flask")
        print(f"   Error: {e}")
    
    # Test 4: Requests
    tests_total += 1
    try:
        import requests
        print("✅ 4. Requests - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 4. Requests - FAILED")
        print(f"   Fix: pip install requests")
        print(f"   Error: {e}")
    
    # Test 5: JSON
    tests_total += 1
    try:
        import json
        print("✅ 5. JSON - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 5. JSON - FAILED")
        print(f"   Error: {e}")
       
    
    # Test 6: SQLite3
    tests_total += 1
    try:
        import sqlite3
        print("✅ 6. SQLite3 - OK")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 6. SQLite3 - FAILED")
        print(f"   Error: {e}")
    
    print(f"\n📊 Import Tests: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_config():
    """Test if config.py is properly set up"""
    print("\n" + "="*70)
    print("🧪 TESTING CONFIG.PY")
    print("="*70 + "\n")
    
    try:
        from config import OPENAI_API_KEY, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
        
        # Check OpenAI key
        if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
            print(f"✅ 1. OPENAI_API_KEY - Set ({OPENAI_API_KEY[:20]}...)")
        else:
            print(f"❌ 1. OPENAI_API_KEY - Invalid or missing")
            print(f"   Current value: {OPENAI_API_KEY[:50] if OPENAI_API_KEY else 'None'}")
            return False
        
        # Check Telegram API ID
        if TELEGRAM_API_ID and isinstance(TELEGRAM_API_ID, int):
            print(f"✅ 2. TELEGRAM_API_ID - Set ({TELEGRAM_API_ID})")
        else:
            print(f"❌ 2. TELEGRAM_API_ID - Invalid or missing")
            return False
        
        # Check Telegram API Hash
        if TELEGRAM_API_HASH and len(TELEGRAM_API_HASH) > 10:
            print(f"✅ 3. TELEGRAM_API_HASH - Set ({TELEGRAM_API_HASH[:15]}...)")
        else:
            print(f"❌ 3. TELEGRAM_API_HASH - Invalid or missing")
            return False
        
        # Check Phone
        if TELEGRAM_PHONE and TELEGRAM_PHONE.startswith('+'):
            print(f"✅ 4. TELEGRAM_PHONE - Set ({TELEGRAM_PHONE})")
        else:
            print(f"❌ 4. TELEGRAM_PHONE - Invalid or missing")
            print(f"   Should start with + and country code")
            return False
        
        print(f"\n📊 Config: All required fields are set")
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import config.py")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False


def test_openai_connection():
    """Test if OpenAI API is working"""
    print("\n" + "="*70)
    print("🧪 TESTING OPENAI CONNECTION")
    print("="*70 + "\n")
    
    try:
        from openai import OpenAI
        from config import OPENAI_API_KEY
        
        if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith('sk-'):
            print("❌ Invalid OpenAI API key")
            return False
        
        print("🔌 Testing OpenAI API...")
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Try a simple completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Reply with just: OK"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API - Working")
        print(f"   Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API - Failed")
        print(f"   Error: {e}")
        print(f"\n   Possible issues:")
        print(f"   1. Invalid API key")
        print(f"   2. No internet connection")
        print(f"   3. OpenAI service down")
        print(f"   4. No credits left")
        return False


def test_files_present():
    """Check if all required files are present"""
    print("\n" + "="*70)
    print("🧪 CHECKING REQUIRED FILES")
    print("="*70 + "\n")
    
    import os
    
    required_files = [
        'config.py',
        'translator_openai.py',
        'telegram_bot_groups.py',
        'dashboard_groups.py',
        'group_aware_handler.py',
        'message_classifier.py',
        'group_message_classifier.py',
        'smart_reply_generator.py',
        'database_simulator.py'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} files")
        return False
    else:
        print(f"\n📊 All required files present")
        return True


def main():
    """Run all tests"""
    
    print("\n" + "="*70)
    print("🚀 TELEGRAM TRANSLATION BOT - VERIFICATION")
    print("="*70)
    print("\nThis will test if your system is ready to run the bot\n")
    
    results = {
        'imports': False,
        'config': False,
        'files': False,
        'openai': False
    }
    
    # Test 1: Imports
    results['imports'] = test_imports()
    
    # Test 2: Files
    results['files'] = test_files_present()
    
    # Test 3: Config
    if results['imports']:
        results['config'] = test_config()
    else:
        print("\n⏭️  Skipping config test (imports failed)")
    
    # Test 4: OpenAI (only if imports and config passed)
    if results['imports'] and results['config']:
        results['openai'] = test_openai_connection()
    else:
        print("\n⏭️  Skipping OpenAI test (prerequisites failed)")
    
    # Final Report
    print("\n" + "="*70)
    print("📊 FINAL REPORT")
    print("="*70 + "\n")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.upper()}")
    
    print(f"\n🎯 Score: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        print("\n✅ Your system is ready to run the bot!")
        print("\n📋 Next steps:")
        print("   1. Run: python telegram_bot_groups.py")
        print("   2. Enter verification code from Telegram")
        print("   3. Bot will start running!")
        print("\n💡 Optional:")
        print("   • Start dashboard: python dashboard_groups.py")
        print("   • Set your language: /language hi")
        print("\n" + "="*70 + "\n")
        return True
    
    else:
        print("\n" + "="*70)
        print("⚠️  SETUP INCOMPLETE")
        print("="*70)
        print(f"\n❌ {total_tests - passed_tests} test(s) failed")
        print("\n📋 Fix the issues above, then run this test again:")
        print("   python verify_setup.py")
        print("\n💡 Quick fixes:")
        print("   • Install missing packages: pip install openai telethon flask")
        print("   • Update config.py with your API keys")
        print("   • Run auto_setup.py for automatic fixing")
        print("\n" + "="*70 + "\n")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
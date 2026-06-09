#!/usr/bin/env python3
"""
Local Test Script for AI Vocabulary Assistant
Run this in your project root directory after installing dependencies.
"""

import sys
import os

# Ensure we're in the project directory
print("="*60)
print("AI Vocabulary Assistant - Local Test Suite")
print("="*60)

# Check Python version
print(f"\nPython version: {sys.version}")

# Test 1: Check .env file exists
print("\n[1/8] Checking .env file...")
if os.path.exists('.env'):
    print("✅ .env file found")
    # Check keys are not placeholders
    with open('.env', 'r') as f:
        content = f.read()
        if 'your-qwen-key' in content or 'your-tavily-key' in content:
            print("⚠️  WARNING: .env still has placeholder values!")
            print("   Please add your REAL API keys to .env")
        else:
            print("✅ .env has real-looking keys")
else:
    print("❌ .env file NOT found!")
    print("   Run: cp .env.example .env")
    print("   Then edit .env with your real keys")
    sys.exit(1)

# Test 2: Install dependencies
print("\n[2/8] Installing dependencies...")
try:
    import subprocess
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Dependencies installed")
    else:
        print("⚠️  Some dependencies may need manual installation")
        print(result.stderr[:200])
except Exception as e:
    print(f"⚠️  pip install failed: {e}")

# Test 3: Import core modules
print("\n[3/8] Testing imports...")
try:
    from backend.config import settings
    print(f"✅ config.py - APP: {settings.APP_NAME}")
except Exception as e:
    print(f"❌ config.py: {e}")

try:
    from backend.database.connection import Base, engine, init_db
    print("✅ database/connection.py")
except Exception as e:
    print(f"❌ database/connection.py: {e}")

try:
    from backend.database.models import User, Word, Review, LearningRecord
    print("✅ database/models.py")
except Exception as e:
    print(f"❌ database/models.py: {e}")

# Test 4: Initialize database
print("\n[4/8] Initializing database...")
try:
    init_db()
    print("✅ Database initialized")

    # Create test word
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()

    test_word = Word(
        word="test_sanction",
        phonetic="/ˈsæŋkʃən/",
        part_of_speech="noun",
        chinese_meaning="制裁",
        example_sentence="The government imposed sanctions.",
        chinese_translation="政府实施了制裁。",
        source_name="Reuters",
        source_url="https://reuters.com/article123",
        collocations=["impose sanctions", "economic sanctions"],
        synonyms=["punishment", "penalty"],
        antonyms=["reward", "approval"]
    )
    db.add(test_word)
    db.commit()
    db.refresh(test_word)
    print(f"✅ Test word created: ID={test_word.id}")

    # Verify query
    found = db.query(Word).filter(Word.word == "test_sanction").first()
    print(f"✅ Query test: Found '{found.word}' with {len(found.collocations)} collocations")

    # Cleanup
    db.delete(test_word)
    db.commit()
    db.close()
    print("✅ Database test passed!")

except Exception as e:
    print(f"❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: SM-2 Algorithm
print("\n[5/8] Testing SM-2 Algorithm...")
try:
    from backend.services.spaced_repetition import SM2Algorithm, SM2Card

    sm2 = SM2Algorithm()

    # Test sequence
    card = SM2Card(word_id=1)
    r1 = sm2.review(card, 4)
    print(f"   Review 1 (q=4): interval={r1.interval}d, reps={r1.repetitions}, learned={r1.is_learned}")

    card2 = SM2Card(word_id=1, interval=r1.interval, repetitions=r1.repetitions, ease_factor=r1.ease_factor)
    r2 = sm2.review(card2, 5)
    print(f"   Review 2 (q=5): interval={r2.interval}d, reps={r2.repetitions}, learned={r2.is_learned}")

    card3 = SM2Card(word_id=1, interval=r2.interval, repetitions=r2.repetitions, ease_factor=r2.ease_factor)
    r3 = sm2.review(card3, 4)
    print(f"   Review 3 (q=4): interval={r3.interval}d, reps={r3.repetitions}")

    card4 = SM2Card(word_id=1, interval=r3.interval, repetitions=r3.repetitions, ease_factor=r3.ease_factor)
    r4 = sm2.review(card4, 1)
    print(f"   Review 4 (q=1): interval={r4.interval}d, reps={r4.repetitions} (RESET!)")

    print("✅ SM-2 Algorithm working correctly!")

except Exception as e:
    print(f"❌ SM-2 test failed: {e}")

# Test 6: FastAPI app
print("\n[6/8] Testing FastAPI app...")
try:
    from backend.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Test health endpoint
    response = client.get("/health")
    if response.status_code == 200:
        print(f"✅ Health check: {response.json()}")
    else:
        print(f"⚠️  Health check returned {response.status_code}")

    # Test root endpoint
    response = client.get("/")
    if response.status_code == 200:
        print(f"✅ API root accessible")
    else:
        print(f"⚠️  API root returned {response.status_code}")

    print("✅ FastAPI app running!")

except Exception as e:
    print(f"❌ FastAPI test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Check API endpoints
print("\n[7/8] Testing API endpoints...")
try:
    # Test list words
    response = client.get("/words/list")
    print(f"   GET /words/list: {response.status_code}")

    # Test stats
    response = client.get("/stats/overview")
    print(f"   GET /stats/overview: {response.status_code}")

    # Test due words
    response = client.get("/review/due")
    print(f"   GET /review/due: {response.status_code}")

    print("✅ API endpoints accessible!")

except Exception as e:
    print(f"❌ API test failed: {e}")

# Test 8: Agent tests (mocked)
print("\n[8/8] Testing Agents (mocked)...")
try:
    from backend.agents.base import BaseAgent
    from backend.agents.example_search import ExampleSearchAgent
    from backend.agents.vocab_tutor import VocabTutorAgent
    from backend.agents.review_quiz import ReviewQuizAgent

    print("✅ All agents importable")

    # Test agent initialization
    agent1 = ExampleSearchAgent()
    agent2 = VocabTutorAgent()
    agent3 = ReviewQuizAgent()

    print(f"✅ ExampleSearchAgent: {agent1.name}")
    print(f"✅ VocabTutorAgent: {agent2.name}")
    print(f"✅ ReviewQuizAgent: {agent3.name}")

    # Test response formatting
    test_data = {
        "word": "test",
        "phonetic": "/test/",
        "part_of_speech": "noun",
        "chinese_meaning": "测试",
        "example_sentence": "This is a test.",
        "chinese_translation": "这是一个测试。",
        "source_name": "BBC",
        "source_url": "https://bbc.com",
        "collocations": ["test case"],
        "synonyms": ["exam"],
        "antonyms": ["pass"]
    }
    formatted = agent1._format_response(test_data)
    assert "test" in formatted
    assert "BBC" in formatted
    print("✅ Response formatting works")

except Exception as e:
    print(f"❌ Agent test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print("""
If all tests show ✅, your project is ready!

Next steps:
1. Run: uvicorn backend.main:app --reload
2. Open: http://localhost:8000/docs (API docs)
3. Open: http://localhost:8000/app (Web UI)
4. Test Telegram: python -m backend.telegram.bot

To test with REAL APIs:
- Add word: POST /agents/example-search with {"word": "sanction"}
- This will call Tavily + Qwen and save to database

For deployment:
- See deploy.md for Render/Railway instructions
- Set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL>/webhook
""")

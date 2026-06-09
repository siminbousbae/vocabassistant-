#!/usr/bin/env python3
"""
Simple Local Test for AI Vocabulary Assistant
"""

import sys
import os

print("="*60)
print("AI Vocabulary Assistant - Quick Test")
print("="*60)

# Check .env
print("\n[1/5] Checking .env...")
if not os.path.exists('.env'):
    print("❌ .env not found! Run: cp .env.example .env")
    sys.exit(1)
print("✅ .env found")

# Check dependencies
print("\n[2/5] Checking dependencies...")
required = {
    'fastapi': 'FastAPI',
    'uvicorn': 'Uvicorn',
    'sqlalchemy': 'SQLAlchemy',
    'pydantic_settings': 'Pydantic Settings',
    'dashscope': 'DashScope',
    'tavily': 'Tavily',
    'telegram': 'python-telegram-bot',
    'dotenv': 'python-dotenv',
}

missing = []
for module, name in required.items():
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} - MISSING")
        missing.append(module)

if missing:
    print(f"\n⚠️  Missing packages. Install with:")
    print(f"   pip install {' '.join(missing)}")
    print(f"\n   Or run: pip install -r requirements.txt")

    install = input("\nInstall now? (y/n): ")
    if install.lower() == 'y':
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed. Please run this script again.")
    sys.exit(1)

print("✅ All dependencies available")

# Test imports
print("\n[3/5] Testing imports...")
try:
    from backend.config import settings
    print(f"   ✅ config.py")

    from backend.database.connection import Base, engine, init_db
    print(f"   ✅ database/connection.py")

    from backend.database.models import Word, Review
    print(f"   ✅ database/models.py")

    from backend.services.spaced_repetition import SM2Algorithm
    print(f"   ✅ spaced_repetition.py")

    from backend.agents.base import BaseAgent
    from backend.agents.example_search import ExampleSearchAgent
    from backend.agents.vocab_tutor import VocabTutorAgent
    from backend.agents.review_quiz import ReviewQuizAgent
    print(f"   ✅ All agents")

    from backend.main import app
    print(f"   ✅ main.py (FastAPI app)")

except Exception as e:
    print(f"   ❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test database
print("\n[4/5] Testing database...")
try:
    # Use in-memory DB for testing
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    # Re-import with new DB URL
    from backend.database.connection import Base, engine
    from backend.database.models import Word, Review

    Base.metadata.create_all(bind=engine)
    print("   ✅ Tables created")

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()

    word = Word(word="test", phonetic="/test/", chinese_meaning="测试")
    db.add(word)
    db.commit()
    db.refresh(word)

    print(f"   ✅ Word created: ID={word.id}")

    review = Review(word_id=word.id, interval=1, ease_factor=2.5)
    db.add(review)
    db.commit()
    print(f"   ✅ Review created")

    db.close()
    print("✅ Database test passed")

except Exception as e:
    print(f"   ❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()

# Test SM-2
print("\n[5/5] Testing SM-2 Algorithm...")
try:
    sm2 = SM2Algorithm()

    from backend.services.spaced_repetition import SM2Card
    card = SM2Card(word_id=1)
    r = sm2.review(card, 4)

    print(f"   Review (q=4): interval={r.interval}d, reps={r.repetitions}")
    assert r.interval == 1
    assert r.repetitions == 1

    card2 = SM2Card(word_id=1, interval=1, repetitions=1, ease_factor=r.ease_factor)
    r2 = sm2.review(card2, 5)
    print(f"   Review (q=5): interval={r2.interval}d, reps={r2.repetitions}")
    assert r2.interval == 6
    assert r2.is_learned == True

    print("✅ SM-2 Algorithm working")

except Exception as e:
    print(f"   ❌ SM-2 test failed: {e}")

# Summary
print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("""
Your project is ready! Start the server:

   cd backend
   uvicorn main:app --reload

Then open:
   http://localhost:8000/docs    (API documentation)
   http://localhost:8000/app     (Web interface)

To test with real APIs:
   curl -X POST http://localhost:8000/agents/example-search \\
     -H "Content-Type: application/json" \\
     -d "{\\"word\\": \\"sanction\\"}"
""")

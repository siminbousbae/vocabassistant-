# OpenClaw Skill: AI Vocabulary Assistant

## Overview

This skill connects the AI Vocabulary Assistant backend to Telegram via OpenClaw, enabling users to learn vocabulary through an AI Agent workflow with real news examples.

**Skill Name:** `vocab-assistant`  
**Version:** `1.0.0`  
**Platform:** `telegram`  
**Author:** Student Project  
**Required APIs:** Tavily Search, Qwen (DashScope)

---

## Agent Architecture

```
User (Telegram)
    ↓
OpenClaw Gateway
    ↓
Telegram Bot Handler
    ↓
Agent Router
    ├── ExampleSearchAgent (Tavily + Qwen)
    ├── VocabTutorAgent (Qwen)
    └── ReviewQuizAgent (SM-2 + Qwen)
    ↓
FastAPI Backend (/api/agents/*)
    ↓
Database (SQLite)
```

---

## Configuration

```yaml
name: vocab-assistant
version: 1.0.0
platform: telegram
endpoint: http://localhost:8000/api/agents
webhook: /webhook
timeout: 30

# API Keys (from environment)
env:
  DASHSCOPE_API_KEY: "${DASHSCOPE_API_KEY}"
  TAVILY_API_KEY: "${TAVILY_API_KEY}"
  TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN}"

# Trusted news domains for Tavily
trusted_domains:
  - reuters.com
  - bbc.com
  - apnews.com
  - theguardian.com
  - npr.org
  - nytimes.com
  - economist.com
  - cnn.com
  - washingtonpost.com
  - ft.com
```

---

## Commands

All interactions use **inline keyboard buttons** (no slash commands required).

### Main Menu Commands

| Button | Callback | Description | Agent |
|--------|----------|-------------|-------|
| `➕ Add Word` | `menu_add` | Start add word flow | - |
| `📚 My Words` | `menu_words` | List vocabulary | - |
| `🔄 Review` | `menu_review` | Start SM-2 review | ReviewQuizAgent |
| `🎯 Quiz` | `menu_quiz` | Generate quiz | ReviewQuizAgent |
| `📊 Statistics` | `menu_stats` | Show stats | ReviewQuizAgent |
| `❓ Help` | `menu_help` | Show help | - |

### Add Word Flow

| Button | Callback | Description | Agent |
|--------|----------|-------------|-------|
| `🔍 Search Real Examples` | `add_search` | Search news for examples | ExampleSearchAgent |
| `🤖 Auto Generate` | `add_auto` | Auto-generate info | VocabTutorAgent |

### Review Flow (SM-2)

| Button | Callback | Description |
|--------|----------|-------------|
| `😵 0` | `review_{id}_0` | Complete blackout |
| `😟 1` | `review_{id}_1` | Incorrect, easy to recall |
| `😐 2` | `review_{id}_2` | Incorrect, remembered |
| `🙂 3` | `review_{id}_3` | Correct with difficulty |
| `😊 4` | `review_{id}_4` | Correct after hesitation |
| `🤩 5` | `review_{id}_5` | Perfect response |
| `⏭️ Skip` | `review_{id}_skip` | Skip this word |

### Quiz Flow

| Button | Callback | Description |
|--------|----------|-------------|
| Options A-D | `quiz_{id}_{sel}_{cor}` | Select answer |

---

## Agent Workflows

### Example Search Agent (CORE - 30 points)

**Trigger:** User types word after clicking "🔍 Search Real Examples"

**Workflow:**
```
1. User Input: "sanction"
   ↓
2. Tavily Search
   Query: "sanction" news article
   include_domains: [reuters.com, bbc.com, ...]
   search_depth: advanced
   max_results: 5
   ↓
3. URL Extract (Tavily.extract)
   Get full article text
   ↓
4. Sentence Extraction
   Find sentences containing "sanction"
   Filter: length 20-300 chars
   ↓
5. LLM Filtering (Qwen)
   Select best example sentence
   Criteria: natural usage, clear context
   ↓
6. LLM Translation (Qwen)
   Translate to Chinese
   Generate phonetic, POS, meaning
   Generate collocations, synonyms, antonyms
   ↓
7. Database Storage
   INSERT INTO words
   INSERT INTO reviews (SM-2 initial)
   INSERT INTO learning_records
   ↓
8. Return Result to User
   Formatted message with all details
```

**Input:**
```json
{
  "word": "sanction",
  "user_id": 12345
}
```

**Output:**
```json
{
  "success": true,
  "word": {
    "word": "sanction",
    "phonetic": "/ˈsæŋkʃən/",
    "part_of_speech": "noun, verb",
    "chinese_meaning": "制裁；处罚",
    "example_sentence": "The government imposed new sanctions on several companies.",
    "chinese_translation": "政府对多家公司实施了新的制裁。",
    "source_name": "Reuters",
    "source_url": "https://reuters.com/...",
    "collocations": ["impose sanctions", "economic sanctions", "lift sanctions"],
    "synonyms": ["punishment", "penalty", "embargo"],
    "antonyms": ["reward", "approval", "encouragement"]
  }
}
```

### Vocab Tutor Agent

**Trigger:** User clicks "🤖 Auto Generate" or `/tutor <word>`

**Workflow:**
```
1. User Input: "abandon"
   ↓
2. Qwen LLM
   Generate: phonetic, POS, meaning, collocations, synonyms, antonyms
   ↓
3. Database Storage (optional)
   ↓
4. Return formatted vocabulary card
```

### Review & Quiz Agent

**Trigger:** User clicks "🔄 Review" or "🎯 Quiz"

**SM-2 Algorithm:**
```
if quality >= 3:
    if repetitions == 0: interval = 1
    elif repetitions == 1: interval = 6
    else: interval = interval * ease_factor
    repetitions += 1
else:
    interval = 1
    repetitions = 0

ease_factor = ease_factor + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02))
ease_factor = max(1.3, ease_factor)

next_review = now + interval days
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/example-search` | Trigger Example Search Agent |
| POST | `/agents/vocab-tutor` | Trigger Vocab Tutor Agent |
| POST | `/agents/review` | Submit review |
| GET | `/agents/due-words` | Get due words |
| GET | `/agents/quiz` | Generate quiz |
| POST | `/webhook` | Telegram webhook |

---

## Database Schema

See `backend/database/schema.sql` for full schema.

Key tables:
- `words` - Vocabulary entries
- `reviews` - SM-2 spaced repetition data
- `learning_records` - Activity tracking
- `daily_stats` - Statistics aggregation

---

## Deployment

### 1. Install OpenClaw
```bash
npm install -g openclaw
```

### 2. Configure Environment
```bash
export DASHSCOPE_API_KEY=sk-xxx
export TAVILY_API_KEY=tvly-xxx
export TELEGRAM_BOT_TOKEN=xxx
```

### 3. Start OpenClaw Gateway
```bash
openclaw gateway --config openclaw/config.md
```

### 4. Connect Telegram Bot
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook"   -d "url=<YOUR_URL>/webhook"
```

### 5. Start Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Testing

### Test Example Search Agent
```bash
curl -X POST http://localhost:8000/agents/example-search   -H "Content-Type: application/json"   -d '{"word": "sanction"}'
```

### Test Review
```bash
curl -X POST http://localhost:8000/agents/review   -H "Content-Type: application/json"   -d '{"word_id": 1, "quality": 4}'
```

### Test Quiz
```bash
curl http://localhost:8000/agents/quiz
```

---

## Project Requirements Checklist

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| OpenClaw Integration | Telegram bot via OpenClaw gateway | ✅ |
| Example Search Agent | Tavily + Qwen workflow | ✅ |
| LLM Utilization | Qwen for translation, enrichment, quiz | ✅ |
| IM Platform | Telegram with inline buttons | ✅ |
| Cloud Deployment | Render/Railway ready | ✅ |
| Web Interface | HTML/JS with cards, review, stats | ✅ |
| Spaced Repetition | SM-2 algorithm | ✅ |
| Audio | Browser TTS (Qwen TTS ready) | ✅ |
| Real Examples | Reuters, BBC, Guardian, etc. | ✅ |
| Multi-device | Responsive web + Telegram | ✅ |

---

## Files Structure

```
vocab-assistant/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── agents/
│   │   ├── example_search.py   # CORE Agent
│   │   ├── vocab_tutor.py      # Tutor Agent
│   │   └── review_quiz.py      # Review Agent
│   ├── services/
│   │   ├── qwen_client.py      # Qwen API
│   │   └── tavily_client.py    # Tavily API
│   ├── api/
│   │   ├── agents.py           # Agent endpoints
│   │   ├── words.py            # CRUD endpoints
│   │   ├── review.py           # Review endpoints
│   │   └── stats.py            # Stats endpoints
│   └── telegram/
│       └── bot.py              # Telegram bot
├── frontend/
│   ├── index.html              # Web UI
│   ├── style.css               # Styles
│   └── app.js                  # Frontend logic
└── openclaw/
    ├── SKILL.md                # This file
    └── config.md               # Gateway config
```

---

## Innovation Features

1. **Real News Examples** - Authentic sentences from Reuters, BBC, etc.
2. **SM-2 Spaced Repetition** - Optimal review scheduling
3. **Auto-enrichment** - Qwen generates collocations, synonyms, antonyms
4. **Quiz Generation** - AI-generated multiple choice questions
5. **Learning Statistics** - Streak tracking, mastery levels
6. **Audio Support** - TTS for pronunciation
7. **Responsive Design** - Works on mobile and desktop
8. **Multi-platform** - Web + Telegram

---

## Troubleshooting

### Agent not responding
- Check API keys in `.env`
- Verify backend is running: `curl http://localhost:8000/health`
- Check OpenClaw gateway logs

### Tavily search returns no results
- Verify Tavily API key
- Check internet connection
- Try different word

### Qwen translation fails
- Verify DashScope API key
- Check Qwen model availability
- Check API quota

### Telegram bot not working
- Verify bot token
- Check webhook URL is correct
- Ensure HTTPS for webhook

---

## License

Student Project - Educational Use Only

# OpenClaw Gateway Configuration

## Basic Setup

```yaml
# Gateway settings
gateway:
  port: 18789
  host: "0.0.0.0"

# Security
auth:
  token: "${OPENCLAW_GATEWAY_TOKEN}"

# Logging
logging:
  level: "info"
  format: "json"
```

## Telegram Platform Configuration

```yaml
platform: telegram

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  webhook_url: "${WEBHOOK_URL}/webhook"
  webhook_secret: "${WEBHOOK_SECRET}"

  # Message handling
  parse_mode: "Markdown"
  disable_web_page_preview: true

  # Button configuration
  inline_keyboard: true
  reply_keyboard: false
```

## Skill Routing

```yaml
skills:
  vocab-assistant:
    endpoint: "http://localhost:8000"
    routes:
      - path: "/agents/example-search"
        method: "POST"
        handler: "ExampleSearchAgent"

      - path: "/agents/vocab-tutor"
        method: "POST"
        handler: "VocabTutorAgent"

      - path: "/agents/review"
        method: "POST"
        handler: "ReviewQuizAgent"

      - path: "/agents/due-words"
        method: "GET"
        handler: "ReviewQuizAgent"

      - path: "/agents/quiz"
        method: "GET"
        handler: "ReviewQuizAgent"

      - path: "/webhook"
        method: "POST"
        handler: "TelegramWebhook"
```

## Agent Configuration

```yaml
agents:
  ExampleSearchAgent:
    timeout: 30
    retries: 2

    # External services
    services:
      - name: "tavily"
        type: "search"
        api_key: "${TAVILY_API_KEY}"

      - name: "qwen"
        type: "llm"
        api_key: "${DASHSCOPE_API_KEY}"
        model: "qwen-max"

    # Workflow steps
    workflow:
      - step: "search"
        service: "tavily"
        action: "search_articles"
        input: "${word}"

      - step: "extract"
        service: "tavily"
        action: "extract_sentences"
        input: "${search_results}"

      - step: "filter"
        service: "qwen"
        action: "filter_best_example"
        input: "${sentences}"

      - step: "translate"
        service: "qwen"
        action: "translate_example"
        input: "${best_sentence}"

      - step: "enrich"
        service: "qwen"
        action: "get_word_info"
        input: "${word}"

      - step: "store"
        service: "database"
        action: "insert_word"
        input: "${word_data}"

  VocabTutorAgent:
    timeout: 15
    retries: 1

    services:
      - name: "qwen"
        type: "llm"
        api_key: "${DASHSCOPE_API_KEY}"

    workflow:
      - step: "generate"
        service: "qwen"
        action: "get_word_info"
        input: "${word}"

  ReviewQuizAgent:
    timeout: 20
    retries: 1

    services:
      - name: "qwen"
        type: "llm"
        api_key: "${DASHSCOPE_API_KEY}"

      - name: "database"
        type: "storage"

    workflow:
      - step: "get_due"
        service: "database"
        action: "query_due_words"

      - step: "generate_quiz"
        service: "qwen"
        action: "generate_quiz_question"
        input: "${due_words}"

      - step: "update_sm2"
        service: "database"
        action: "update_review"
        input: "${review_data}"
```

## Environment Variables

```bash
# Required
export DASHSCOPE_API_KEY="sk-your-qwen-key"
export TAVILY_API_KEY="tvly-your-tavily-key"
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"

# Optional
export OPENCLAW_GATEWAY_TOKEN="your-gateway-token"
export WEBHOOK_URL="https://your-app.com"
export WEBHOOK_SECRET="your-webhook-secret"
```

## Deployment Commands

```bash
# 1. Start OpenClaw Gateway
openclaw gateway --config openclaw/config.md

# 2. In another terminal, start the backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Set Telegram webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook"   -H "Content-Type: application/json"   -d '{
    "url": "https://your-app.com/webhook",
    "secret_token": "your-webhook-secret"
  }'
```

## Monitoring

```yaml
monitoring:
  metrics:
    enabled: true
    port: 9090

  health_check:
    enabled: true
    path: "/health"
    interval: 30

  alerts:
    - condition: "agent_error_rate > 0.1"
      action: "notify_admin"
    - condition: "response_time > 10s"
      action: "log_warning"
```

## Scaling

```yaml
scaling:
  # For high-traffic deployments
  workers: 4
  max_connections: 100

  # Rate limiting
  rate_limit:
    requests_per_minute: 60
    burst: 10
```

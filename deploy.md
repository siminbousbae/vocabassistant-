# 部署指南

## 1. 后端部署 (Render)

1. 在 [Render](https://render.com) 创建 Web Service
2. 选择 Python 环境
3. 设置 Build Command: `pip install -r requirements.txt`
4. 设置 Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 在 Environment 中添加所有 `.env` 变量

## 2. Telegram Bot 部署

1. 在 Telegram 中找 @BotFather 创建 Bot，获取 Token
2. 将 Token 填入环境变量 `TELEGRAM_BOT_TOKEN`
3. 部署后设置 Webhook:
   ```
   https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/webhook
   ```

## 3. OpenClaw 部署

1. 安装 OpenClaw: `npm install -g openclaw`
2. 配置 `openclaw/SKILL.md`
3. 启动 OpenClaw 网关
4. 连接 Telegram Bot

## 4. 前端部署

前端为纯静态文件，可部署到：
- Vercel
- Netlify
- GitHub Pages
- 或直接使用后端托管静态文件

## 环境变量清单

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| DASHSCOPE_API_KEY | Qwen API Key | [DashScope](https://dashscope.aliyun.com) |
| TAVILY_API_KEY | Tavily API Key | [Tavily](https://tavily.com) |
| TELEGRAM_BOT_TOKEN | Telegram Bot Token | @BotFather |
| DATABASE_URL | 数据库连接 | 默认 SQLite |

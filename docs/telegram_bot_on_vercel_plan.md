
# Technical Plan: Deploying a Single‑User Telegram Bot on Vercel

*Created: 2025-06-01*

## 1. Goal
Allow one user (you) to converse with an existing Python conversational agent through Telegram.  
The solution must be economical, simple, and require minimal maintenance.

## 2. Why Vercel?
| Feature | Hobby (Free) Tier | Notes |
|---------|------------------|-------|
| HTTPS & custom subdomain | ✔ | Webhook endpoint secured automatically. |
| Python Serverless Functions | ✔ | Works out of the box. |
| Cold‑start time | ~150‑300 ms typical | Acceptable for chat. |
| Max runtime | 60 s with Fluid Compute (free) [[1]](#refs) | Plenty for typical chat. |
| Cost | $0 for low traffic | Only pay if limits are exceeded. |

## 3. High‑Level Architecture
```
 Telegram App ⇄ Telegram Bot API ⇄ Vercel Serverless Function (/api/webhook)
                                         ⇂
                                 Python Conversational Core
```
The function is stateless so all context must be kept in memory per request or stored externally (SQLite, Redis, etc.).

## 4. Repository Layout
```
/
├── api/
│   └── webhook.py          <- FastAPI handler
├── agent/
│   └── core.py             <- your_agent.chat(text)
├── requirements.txt
└── vercel.json             <- route & function config
```

### 4.1 vercel.json
```json
{{
  "functions": {{
    "api/webhook.py": {{
      "runtime": "python3.11",
      "maxDuration": 60
    }}
  }},
  "routes": [
    {{ "src": "/webhook", "dest": "api/webhook.py" }}
  ]
}}
```

### 4.2 api/webhook.py
```python
from fastapi import FastAPI, Request
import httpx, os, agent.core as core

app = FastAPI()
TOKEN = os.environ["BOT_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

@app.post("/webhook")
async def telegram_webhook(req: Request):
    update = await req.json()
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    if not chat_id or not text:
        return {"ok": True}   # Ignore non‑text updates
    reply = await core.chat(text)
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage",
                          json={{"chat_id": chat_id, "text": reply}})
    return {"ok": True}
```

## 5. Deployment Steps

1. **Create the bot**  
   Talk to `@BotFather`, save the token as `BOT_TOKEN`.

2. **Repo & Vercel**  
   ```bash
   git init telegram-bot
   # add code
   vercel login
   vercel link     # first time
   vercel env add BOT_TOKEN
   vercel deploy --prod
   ```

3. **Set the Telegram webhook**  
   ```bash
   curl "https://api.telegram.org/bot<token>/setWebhook?url=https://<your-app>.vercel.app/webhook"
   ```

4. **Test**  
   Send any message to the bot. It should echo the response returned by your agent.

## 6. Environment Variables
| Name | Description |
|------|-------------|
| BOT_TOKEN | Telegram bot token from BotFather. |
| OPENAI_API_KEY (optional) | If your agent calls OpenAI. |
| AGENT_SECRET (optional) | HMAC key to verify Telegram updates. |

## 7. Scaling & Limits
* Hobby tier allows roughly 100 GB-hours and 500 000 invocations per month.  
* Telegram Bot API lets you send 30 messages per second overall and 1 message per second per chat [[2]](#refs).  
* For higher throughput upgrade to Vercel Pro or move to a long-running container host.

## 8. Security Hardening
1. Verify `X-Telegram-Bot-Api-Secret-Token` header (add secret via BotFather `setwebhook`).  
2. Restrict memory and duration in `vercel.json`.  
3. Run dependency scanner (`pip-audit`) in CI.

## 9. Cost Estimate
| Item | Quantity | Price | Monthly |
|------|----------|-------|---------|
| Vercel Hobby | up to 100 GB‑h | $0 | $0 |
| Telegram Bot | normal usage | $0 | $0 |
| **Total** |  |  | **$0** |

## 10. Possible Extensions
* Add `/reset` command to clear context.  
* Support images via `sendPhoto`.  
* Move context storage to an external KV (Supabase, Upstash) if persistence is needed.

---

## <a name="refs">References</a>
[1] Vercel Fluid Compute guide, free functions run up to 1 minute.  
[2] Telegram Bot FAQ, broadcast limit is 30 messages per second and 1 message per second per chat.

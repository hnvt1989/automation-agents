# Telegram Bot Setup Guide

This guide will help you deploy your multi-agent system as a Telegram bot on Vercel.

## Prerequisites

1. **Telegram Account**: You need a Telegram account to create and interact with the bot
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com) (free tier is sufficient)
3. **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)
4. **Node.js**: Required for Vercel CLI installation

## Step 1: Create Your Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a conversation** with BotFather
3. **Create a new bot**:
   ```
   /newbot
   ```
4. **Choose a name** for your bot (e.g., "My Personal Assistant")
5. **Choose a username** for your bot (must end with 'bot', e.g., `myassistant_bot`)
6. **Save the bot token** that BotFather provides (looks like: `1234567890:ABCDEF...`)

## Step 2: Get Your Telegram User ID

1. **Search for** `@userinfobot` on Telegram
2. **Start a conversation** with the bot
3. **The bot will reply** with your user information
4. **Save your User ID** (a numeric value like `123456789`)

## Step 3: Install Vercel CLI

```bash
npm install -g vercel
```

## Step 4: Deploy to Vercel

1. **Navigate to your project directory**:
   ```bash
   cd /path/to/automation-agents
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Link your project**:
   ```bash
   vercel link
   ```
   - Follow the prompts to create a new project or link to an existing one

4. **Set environment variables**:
   ```bash
   # Bot token from BotFather
   vercel env add BOT_TOKEN
   # Enter the token when prompted

   # Your Telegram user ID
   vercel env add ALLOWED_USER_ID
   # Enter your user ID when prompted

   # OpenAI API key
   vercel env add LLM_API_KEY
   # Enter your OpenAI API key when prompted

   # (Optional) Model choice - defaults to gpt-4o-mini
   vercel env add MODEL_CHOICE
   # Enter model name if you want to use a different model
   ```

5. **Deploy to production**:
   ```bash
   vercel deploy --prod
   ```

6. **Note your deployment URL** (e.g., `https://your-project.vercel.app`)

## Step 5: Register Webhook with Telegram

1. **Set the webhook URL**:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-project.vercel.app/webhook"}'
   ```
   Replace `<YOUR_BOT_TOKEN>` with your actual bot token and update the URL.

2. **Verify webhook is set**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

## Step 6: Test Your Bot

1. **Open Telegram** and search for your bot username
2. **Start a conversation** with `/start` or any message
3. **The bot should respond** to your messages

## Troubleshooting

### Bot Not Responding

1. **Check webhook status**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```
   Look for any errors in the response.

2. **Check Vercel logs**:
   ```bash
   vercel logs
   ```
   Look for any error messages or failed requests.

3. **Verify environment variables**:
   - Go to your Vercel dashboard
   - Navigate to Project Settings → Environment Variables
   - Ensure all required variables are set

### Authentication Issues

- Make sure your `ALLOWED_USER_ID` matches exactly what you got from `@userinfobot`
- The user ID should be numeric only (no quotes or extra characters)

### Webhook Errors

- Ensure your deployment URL is correct and uses HTTPS
- The webhook endpoint should be `/webhook` (not just the base URL)
- Check that the bot token is correct and hasn't been regenerated

## Usage Notes

### What the Telegram Bot Can Do

✅ **Available Features**:
- General conversation and Q&A
- Basic planning and scheduling advice
- Text analysis and processing
- Information synthesis
- Simple date/time calculations

❌ **Not Available** (compared to local version):
- Web search capabilities
- File system access
- GitHub/Slack integrations
- Image processing
- RAG/Knowledge base queries
- Rich markdown formatting

### Best Practices

1. **Use for quick queries** when you're away from your computer
2. **Keep sensitive information** to the local version
3. **Monitor usage** to control API costs
4. **Use the local version** (`python3 agents.py`) for complex tasks

## Updating Your Bot

To update your bot with new changes:

1. Make your code changes locally
2. Test locally if needed
3. Deploy to Vercel:
   ```bash
   vercel deploy --prod
   ```

The webhook will automatically use the new version.

## Cost Considerations

- **Vercel**: Free tier includes 100 GB-hours/month (more than enough for personal use)
- **Telegram API**: Free for all usage levels
- **OpenAI API**: Approximately $5-15/month for moderate personal use

## Security Notes

- Only the user ID specified in `ALLOWED_USER_ID` can use the bot
- The bot silently ignores messages from other users
- No sensitive system information is exposed in error messages
- API keys are securely stored in Vercel environment variables

## Local Testing (Optional)

To test the webhook locally before deploying:

1. Create a `local.env` file with test values:
   ```env
   BOT_TOKEN=your-bot-token
   ALLOWED_USER_ID=your-user-id
   LLM_API_KEY=your-openai-key
   MODEL_CHOICE=gpt-4o-mini
   ```

2. Run the webhook locally:
   ```bash
   cd api
   python webhook.py
   ```

3. Use a tool like [ngrok](https://ngrok.com) to expose your local server for testing.

## Getting Help

- **Vercel Issues**: Check the [Vercel documentation](https://vercel.com/docs)
- **Telegram Bot API**: See the [official documentation](https://core.telegram.org/bots/api)
- **Project Issues**: Review the implementation plan in `docs/final_plans.md`
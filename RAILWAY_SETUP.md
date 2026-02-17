# DateEveryNight Bot - Railway Deployment Guide

## Prerequisites
- Railway account (sign up at https://railway.app)
- GitHub account with the bot repository
- Telegram Bot Token (from BotFather)

## Step 1: Prepare Your Repository

1. Initialize a Git repository in your project (if not already done):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Push your code to GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/DateEveryNight.git
git branch -M main
git push -u origin main
```

## Step 2: Set Up PostgreSQL on Railway

1. Go to https://railway.app and log in
2. Click "New Project"
3. Select "Provision PostgreSQL"
4. Railway will create a PostgreSQL database automatically
5. Copy the `DATABASE_URL` from the PostgreSQL plugin variables

## Step 3: Deploy the Bot

1. In the same Railway project, click "New Service"
2. Select "GitHub Repo" and connect your GitHub account
3. Select your `DateEveryNight` repository
4. Railway will automatically detect the `Procfile` and deploy

## Step 4: Configure Environment Variables

In your Railway project dashboard:

1. Click on the Bot service
2. Go to "Variables" tab
3. Add the following environment variables:

```
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://user:password@host:port/database
ADMIN_ID=your_telegram_user_id
LOG_LEVEL=INFO
```

**Important:** 
- Get `BOT_TOKEN` from Telegram BotFather
- `DATABASE_URL` is automatically provided by the PostgreSQL plugin
- `ADMIN_ID` is your personal Telegram user ID

## Step 5: Verify Deployment

1. Check the "Deployments" tab to see if the bot is running
2. View logs in the "Logs" tab to confirm the bot started successfully
3. You should see: "Application started" in the logs

## Troubleshooting

### Bot not connecting to database
- Verify `DATABASE_URL` is correctly set in Railway variables
- Check that PostgreSQL service is running in the same project

### Bot not responding to commands
- Verify `BOT_TOKEN` is correct
- Check logs for any errors
- Ensure the bot is running (check deployment status)

### Port issues
- Railway automatically assigns ports; the bot doesn't need to listen on a specific port for Telegram webhooks

## Notes

- The bot uses polling (not webhooks), so it will work on Railway without port configuration
- PostgreSQL data persists across deployments
- The bot will automatically restart if it crashes
- Check Railway's pricing for free tier limits

## Support

For Railway-specific issues, visit: https://docs.railway.app

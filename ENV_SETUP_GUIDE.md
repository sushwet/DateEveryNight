# Environment Variables Setup Guide

## Overview
This guide explains how to properly set up all required environment variables for the DateEveryNight bot.

---

## Required Environment Variables

### 1. BOT_TOKEN (Required)
**What it is:** Your Telegram bot's authentication token

**How to get it:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/start`
4. Send `/newbot`
5. Follow the prompts to create a new bot
6. BotFather will give you a token like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

**Where to set it:**
- **Local development:** Add to `.env` file
- **Railway:** Set in Railway dashboard → Bot service → Variables

**Example:**
```
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

**Security:** 
- ⚠️ NEVER commit this to git
- ⚠️ NEVER share this publicly
- ⚠️ This token gives full control of your bot

---

### 2. DATABASE_URL (Required)
**What it is:** PostgreSQL database connection string

**How to get it:**
- **Local development:** Use your local PostgreSQL
  ```
  postgresql://dateeverynight_user:secure_password_change_me@localhost:5432/dateeverynight
  ```

- **Railway:** 
  1. Go to Railway dashboard
  2. Click on PostgreSQL plugin
  3. Go to "Variables" tab
  4. Copy the `DATABASE_URL` value

**Format:**
```
postgresql://username:password@host:port/database_name
```

**Example:**
```
DATABASE_URL=postgresql://dateeverynight_user:secure_password_change_me@localhost:5432/dateeverynight
```

**Security:**
- ⚠️ NEVER commit this to git
- ⚠️ NEVER share this publicly
- ⚠️ Contains database password

---

### 3. ADMIN_ID (Required)
**What it is:** Your Telegram user ID (for admin features)

**How to get it:**
1. Open Telegram
2. Search for `@userinfobot`
3. Send `/start`
4. It will show you your user ID (e.g., `123456789`)

**Where to set it:**
- **Local development:** Add to `.env` file
- **Railway:** Set in Railway dashboard → Bot service → Variables

**Example:**
```
ADMIN_ID=123456789
```

**Note:** This is just a number, not sensitive like BOT_TOKEN

---

### 4. LOG_LEVEL (Optional)
**What it is:** Logging verbosity level

**Default value:** `INFO`

**Possible values:**
- `DEBUG` - Very detailed logs (development)
- `INFO` - Standard logs (recommended)
- `WARNING` - Only warnings and errors
- `ERROR` - Only errors
- `CRITICAL` - Only critical errors

**Example:**
```
LOG_LEVEL=INFO
```

---

## Setting Up Environment Variables

### For Local Development

1. Create a `.env` file in the project root:
```bash
touch .env
```

2. Add all variables to `.env`:
```
BOT_TOKEN=your_real_token_here
DATABASE_URL=postgresql://user:password@localhost:5432/dateeverynight
ADMIN_ID=your_telegram_id
LOG_LEVEL=INFO
```

3. The bot will automatically load these when you run:
```bash
python main.py
```

**Important:** `.env` is in `.gitignore`, so it won't be committed to git ✅

---

### For Railway Deployment

1. Go to https://railway.app/dashboard
2. Select your DateEveryNight project
3. Click on the Bot service
4. Go to "Variables" tab
5. Add each variable:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | Your token from BotFather |
| `DATABASE_URL` | Copy from PostgreSQL plugin variables |
| `ADMIN_ID` | Your Telegram user ID |
| `LOG_LEVEL` | INFO |

6. Click "Save"
7. Railway will automatically redeploy with new variables

---

## Verification

### Check if variables are loaded correctly

**Local development:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'BOT_TOKEN: {os.getenv(\"BOT_TOKEN\")}')"
```

**Railway:**
1. Go to Railway dashboard
2. Click on Bot service
3. Go to "Logs" tab
4. Look for: `"Bot is now running and listening for messages..."`
5. If you see this, variables are loaded ✅

---

## Troubleshooting

### "BOT_TOKEN environment variable is not set"
**Solution:**
- Local: Add `BOT_TOKEN=...` to `.env` file
- Railway: Add `BOT_TOKEN` to Variables tab

### "DATABASE_URL environment variable is not set"
**Solution:**
- Local: Add `DATABASE_URL=...` to `.env` file
- Railway: Add `DATABASE_URL` to Variables tab (copy from PostgreSQL plugin)

### "Database connection failed"
**Solution:**
- Verify `DATABASE_URL` format is correct
- Verify PostgreSQL is running (Railway shows status)
- Check if password in DATABASE_URL is correct

### Bot doesn't respond to commands
**Solution:**
- Verify `BOT_TOKEN` is correct (from BotFather)
- Check Railway logs for errors
- Verify bot is running (check Deployments tab)

---

## Security Best Practices

1. **Never commit `.env` to git**
   - It's already in `.gitignore` ✅

2. **Never share BOT_TOKEN**
   - Anyone with this token can control your bot

3. **Never share DATABASE_URL**
   - Anyone with this can access your database

4. **Use strong database passwords**
   - Railway generates secure passwords automatically

5. **Rotate tokens if compromised**
   - Get new token from BotFather
   - Update in Railway immediately

6. **Use Railway's built-in secrets**
   - Don't store secrets in code
   - Always use environment variables

---

## Example .env File

```
# Telegram Bot Configuration
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Database Configuration
DATABASE_URL=postgresql://dateeverynight_user:secure_password_change_me@localhost:5432/dateeverynight

# Admin Configuration
ADMIN_ID=123456789

# Logging Configuration
LOG_LEVEL=INFO
```

---

## Summary

✅ **Required variables:** BOT_TOKEN, DATABASE_URL, ADMIN_ID
✅ **Optional variables:** LOG_LEVEL
✅ **Local setup:** Use `.env` file
✅ **Railway setup:** Use Variables tab in dashboard
✅ **Security:** Never commit sensitive data to git
✅ **Validation:** Bot checks variables on startup and fails with clear error if missing

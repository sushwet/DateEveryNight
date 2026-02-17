# DateEveryNight Bot - Database & Subscription Guide

## Database Overview

The bot uses **PostgreSQL** to store all user data, matches, messages, and subscription information. Here's what data you'll have access to:

---

## 1. User Information Table (`users`)

When a user signs up, the following information is stored:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | BIGINT | Telegram user ID (unique identifier) |
| `username` | VARCHAR | Telegram username |
| `age` | INT | User's age |
| `gender` | VARCHAR | User's gender (M/F/Other) |
| `preference` | VARCHAR | Dating preference (M/F/Both) |
| `city` | VARCHAR | City where user is located |
| `latitude` | FLOAT | Geographic latitude |
| `longitude` | FLOAT | Geographic longitude |
| `state` | VARCHAR | User state (NEW, ACTIVE, SEARCHING, etc.) |
| `free_matches_used` | INT | Count of free matches used |
| `is_premium` | BOOLEAN | Whether user has active premium |
| `premium_plan` | VARCHAR | Plan name (1 Week, 2 Weeks, 1 Month, 3 Months) |
| `premium_expires_at` | TIMESTAMP | When premium subscription expires |
| `is_blocked` | BOOLEAN | Whether user is blocked |
| `created_at` | TIMESTAMP | Account creation date |
| `updated_at` | TIMESTAMP | Last profile update |

**Example User Data:**
```
user_id: 123456789
username: john_doe
age: 28
gender: M
preference: F
city: Bengaluru
is_premium: TRUE
premium_plan: 1 Month
premium_expires_at: 2026-03-17 10:57:38
```

---

## 2. Premium Transactions Table (`premium_transactions`)

**This is the key table for tracking subscription purchases!**

Every time a user buys a premium subscription, a record is created here:

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | SERIAL | Unique transaction ID |
| `user_id` | BIGINT | Which user made the purchase |
| `plan_name` | VARCHAR | Which plan they bought (1 Week, 2 Weeks, 1 Month, 3 Months) |
| `stars_cost` | INT | How many Telegram Stars they paid |
| `duration_days` | INT | How many days the subscription lasts |
| `created_at` | TIMESTAMP | When the purchase was made |

**Example Transaction:**
```
transaction_id: 1
user_id: 123456789
plan_name: 1 Month
stars_cost: 250
duration_days: 30
created_at: 2026-02-17 10:57:38
```

---

## 3. Premium Plans & Pricing

Users can choose from 4 subscription tiers:

| Plan | Stars Cost | Duration | Features |
|------|-----------|----------|----------|
| 1 Week | 100⭐ | 7 days | Unlimited matches, priority access |
| 2 Weeks | 150⭐ | 14 days | Unlimited matches, priority access |
| 1 Month | 250⭐ | 30 days | Unlimited matches, priority access |
| 3 Months | 500⭐ | 90 days | Unlimited matches, priority access |

**Note:** Telegram Stars (⭐) are Telegram's in-app currency. Users pay with real money, and you receive revenue through Telegram's payment system.

---

## 4. How Subscription Tracking Works

### When a User Buys Premium:

1. **User clicks `/premium`** → Bot shows 4 subscription options
2. **User selects a plan** → Bot sends a Telegram invoice
3. **User pays with Telegram Stars** → Payment processed by Telegram
4. **Payment successful** → Two things happen:
   - **`users` table updated:**
     - `is_premium` = TRUE
     - `premium_plan` = Plan name
     - `premium_expires_at` = Current date + plan duration
   
   - **`premium_transactions` table updated:**
     - New transaction record created with all payment details

5. **User receives confirmation** with expiration date

### Example Timeline:

```
Feb 17, 2026 10:57:38 - User buys "1 Month" plan for 250⭐
  ↓
users table: is_premium = TRUE, premium_expires_at = Mar 17, 2026
premium_transactions table: New record created
  ↓
User receives: "🎉 Premium Activated! Expires: 17 Mar 2026"
```

---

## 5. Other Important Tables

### Matches (`matches`)
Tracks when two users are matched:
- `match_id` - Unique match ID
- `user1_id` - First user
- `user2_id` - Second user
- `started_at` - When match began
- `ended_at` - When match ended

### Messages (`messages`)
Stores all messages between matched users:
- `message_id` - Unique message ID
- `match_id` - Which match this belongs to
- `sender_id` - Who sent the message
- `content` - Message text
- `sent_at` - Timestamp

### Blocked Pairs (`blocked_pairs`)
Tracks users who blocked each other:
- `blocker_id` - User who blocked
- `blocked_id` - User who was blocked
- `reason` - Why they were blocked

### Reports (`reports`)
Tracks user reports for moderation:
- `reporter_id` - User who reported
- `reported_id` - User who was reported
- `reason` - Report reason

---

## 6. How to Check Subscription Data

### View All Premium Users:
```sql
SELECT user_id, username, premium_plan, premium_expires_at 
FROM users 
WHERE is_premium = TRUE;
```

### View All Transactions (Revenue):
```sql
SELECT user_id, plan_name, stars_cost, created_at 
FROM premium_transactions 
ORDER BY created_at DESC;
```

### Total Revenue:
```sql
SELECT SUM(stars_cost) as total_stars_earned 
FROM premium_transactions;
```

### Transactions This Month:
```sql
SELECT COUNT(*) as purchases, SUM(stars_cost) as revenue
FROM premium_transactions 
WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE);
```

### Users About to Expire (Next 7 Days):
```sql
SELECT user_id, username, premium_expires_at 
FROM users 
WHERE is_premium = TRUE 
AND premium_expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days';
```

---

## 7. Revenue Tracking

### How You Get Paid:

1. **Telegram Stars** - Users pay with Telegram Stars (real money)
2. **Your Revenue** - Telegram takes a commission, you get the rest
3. **Automatic** - Payments are processed through Telegram's system
4. **Tracking** - All transactions are logged in `premium_transactions` table

### Monitoring Revenue:

You can query the database anytime to see:
- Total stars earned
- Number of subscriptions sold
- Most popular plan
- Revenue by date/month
- User retention

---

## 8. What You'll Know About Users

✅ **You WILL know:**
- Their Telegram ID & username
- Age, gender, dating preference
- City/location
- When they bought premium
- Which plan they bought
- How much they paid (in stars)
- When their subscription expires
- All their matches & conversations
- If they reported or blocked someone

❌ **You WON'T know:**
- Their real name (unless they share it)
- Phone number
- Email address
- Payment method details (Telegram handles this)
- Personal info outside the app

---

## 9. Database Access on Railway

Once deployed on Railway:

1. **PostgreSQL Plugin** - Railway provides the database
2. **Connection String** - Automatically set as `DATABASE_URL` environment variable
3. **Data Persistence** - All data persists across deployments
4. **Backups** - Railway handles automatic backups

### To Access Database Directly:

You can use any PostgreSQL client (pgAdmin, DBeaver, etc.) with the `DATABASE_URL` from Railway:

```
postgresql://user:password@host:port/dateeverynight
```

---

## 10. Key Metrics to Monitor

Once your bot is live, track these metrics:

| Metric | Query | Importance |
|--------|-------|-----------|
| Total Users | `SELECT COUNT(*) FROM users;` | Growth tracking |
| Premium Users | `SELECT COUNT(*) FROM users WHERE is_premium = TRUE;` | Revenue potential |
| Total Revenue | `SELECT SUM(stars_cost) FROM premium_transactions;` | Business metric |
| Conversion Rate | Premium users / Total users | Marketing metric |
| Most Popular Plan | `SELECT plan_name, COUNT(*) FROM premium_transactions GROUP BY plan_name;` | Pricing strategy |
| Active Matches | `SELECT COUNT(*) FROM matches WHERE ended_at IS NULL;` | Engagement |

---

## Summary

✅ **Subscription Tracking:** Every purchase is automatically logged in `premium_transactions`
✅ **User Data:** All user info stored in `users` table with premium status
✅ **Revenue:** Track total stars earned and monitor by date/plan
✅ **Automatic:** No manual tracking needed - bot handles everything
✅ **Secure:** PostgreSQL ensures data integrity and security

You'll have complete visibility into all subscriptions, user data, and revenue!

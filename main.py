import logging
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler, PreCheckoutQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Database

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
try:
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
except ValueError:
    ADMIN_ID = 0

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set. Please set it before running the bot.")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please set it before running the bot.")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database(DATABASE_URL)

AGE, GENDER, PREFERENCE, CITY = range(4)

# Cities configuration (Tier 1-3 Indian cities)
CITIES = {
    'bengaluru': {'name': 'Bengaluru', 'lat': 12.9716, 'lon': 77.5946, 'tier': 1},
    'mumbai': {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777, 'tier': 1},
    'delhi': {'name': 'Delhi', 'lat': 28.7041, 'lon': 77.1025, 'tier': 1},
    'hyderabad': {'name': 'Hyderabad', 'lat': 17.3850, 'lon': 78.4867, 'tier': 1},
    'chennai': {'name': 'Chennai', 'lat': 13.0827, 'lon': 80.2707, 'tier': 1},
    'kolkata': {'name': 'Kolkata', 'lat': 22.5726, 'lon': 88.3639, 'tier': 1},
    'pune': {'name': 'Pune', 'lat': 18.5204, 'lon': 73.8567, 'tier': 1},
    'ahmedabad': {'name': 'Ahmedabad', 'lat': 23.0225, 'lon': 72.5714, 'tier': 1},
    'jaipur': {'name': 'Jaipur', 'lat': 26.9124, 'lon': 75.7873, 'tier': 2},
    'chandigarh': {'name': 'Chandigarh', 'lat': 30.7333, 'lon': 76.7794, 'tier': 2},
    'indore': {'name': 'Indore', 'lat': 22.7196, 'lon': 75.8577, 'tier': 2},
    'bhopal': {'name': 'Bhopal', 'lat': 23.1815, 'lon': 79.9864, 'tier': 2},
    'coimbatore': {'name': 'Coimbatore', 'lat': 11.0066, 'lon': 76.9485, 'tier': 2},
    'kochi': {'name': 'Kochi', 'lat': 9.9312, 'lon': 76.2673, 'tier': 2},
    'trivandrum': {'name': 'Trivandrum', 'lat': 8.5241, 'lon': 76.9366, 'tier': 2},
    'trichy': {'name': 'Trichy', 'lat': 10.7905, 'lon': 78.7047, 'tier': 2},
    'madurai': {'name': 'Madurai', 'lat': 9.9252, 'lon': 78.1198, 'tier': 2},
    'salem': {'name': 'Salem', 'lat': 11.6643, 'lon': 78.1460, 'tier': 2},
    'tirunelveli': {'name': 'Tirunelveli', 'lat': 8.7139, 'lon': 77.7567, 'tier': 2},
    'visakhapatnam': {'name': 'Visakhapatnam', 'lat': 17.6869, 'lon': 83.2185, 'tier': 2},
    'vijayawada': {'name': 'Vijayawada', 'lat': 16.5062, 'lon': 80.6480, 'tier': 2},
    'guntur': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365, 'tier': 2},
    'nellore': {'name': 'Nellore', 'lat': 14.4426, 'lon': 79.9864, 'tier': 2},
    'rajahmundry': {'name': 'Rajahmundry', 'lat': 16.9891, 'lon': 81.7744, 'tier': 2},
    'warangal': {'name': 'Warangal', 'lat': 17.9689, 'lon': 79.5941, 'tier': 2},
    'nagpur': {'name': 'Nagpur', 'lat': 21.1458, 'lon': 79.0882, 'tier': 2},
    'nashik': {'name': 'Nashik', 'lat': 19.9975, 'lon': 73.7898, 'tier': 2},
    'aurangabad': {'name': 'Aurangabad', 'lat': 19.8762, 'lon': 75.3433, 'tier': 2},
    'kolhapur': {'name': 'Kolhapur', 'lat': 16.7050, 'lon': 73.7421, 'tier': 2},
    'udaipur': {'name': 'Udaipur', 'lat': 24.5854, 'lon': 73.7125, 'tier': 2},
    'jodhpur': {'name': 'Jodhpur', 'lat': 26.2389, 'lon': 73.0243, 'tier': 2},
    'kota': {'name': 'Kota', 'lat': 25.2138, 'lon': 75.8648, 'tier': 2},
    'ajmer': {'name': 'Ajmer', 'lat': 26.4499, 'lon': 74.6399, 'tier': 2},
    'dehradun': {'name': 'Dehradun', 'lat': 30.1975, 'lon': 78.1348, 'tier': 2},
    'haridwar': {'name': 'Haridwar', 'lat': 29.9457, 'lon': 78.1642, 'tier': 2},
    'roorkee': {'name': 'Roorkee', 'lat': 29.8680, 'lon': 77.8971, 'tier': 2},
    'ludhiana': {'name': 'Ludhiana', 'lat': 30.9010, 'lon': 75.8573, 'tier': 2},
    'amritsar': {'name': 'Amritsar', 'lat': 31.6340, 'lon': 74.8723, 'tier': 2},
    'jalandhar': {'name': 'Jalandhar', 'lat': 31.7260, 'lon': 75.5762, 'tier': 2},
    'patiala': {'name': 'Patiala', 'lat': 30.3398, 'lon': 76.3869, 'tier': 2},
    'mohali': {'name': 'Mohali', 'lat': 30.6394, 'lon': 76.8216, 'tier': 2},
    'panipat': {'name': 'Panipat', 'lat': 29.3910, 'lon': 77.2863, 'tier': 2},
    'karnal': {'name': 'Karnal', 'lat': 29.6200, 'lon': 77.1040, 'tier': 2},
    'hisar': {'name': 'Hisar', 'lat': 29.1724, 'lon': 75.7339, 'tier': 2},
    'rohtak': {'name': 'Rohtak', 'lat': 28.8955, 'lon': 77.0413, 'tier': 2},
    'alwar': {'name': 'Alwar', 'lat': 27.5330, 'lon': 75.6245, 'tier': 2},
    'mysuru': {'name': 'Mysuru', 'lat': 12.2958, 'lon': 76.6394, 'tier': 3},
    'hubballi': {'name': 'Hubballi', 'lat': 15.3647, 'lon': 75.1240, 'tier': 3},
    'belagavi': {'name': 'Belagavi', 'lat': 15.8497, 'lon': 74.4977, 'tier': 3},
    'mangalore': {'name': 'Mangalore', 'lat': 12.8628, 'lon': 74.8430, 'tier': 3},
    'shimla': {'name': 'Shimla', 'lat': 31.7724, 'lon': 77.1025, 'tier': 3},
    'srinagar': {'name': 'Srinagar', 'lat': 34.0837, 'lon': 74.7973, 'tier': 3},
    'guwahati': {'name': 'Guwahati', 'lat': 26.1445, 'lon': 91.7362, 'tier': 3},
    'ranchi': {'name': 'Ranchi', 'lat': 23.3441, 'lon': 85.3096, 'tier': 3},
    'patna': {'name': 'Patna', 'lat': 25.5941, 'lon': 85.1376, 'tier': 3},
    'varanasi': {'name': 'Varanasi', 'lat': 25.3176, 'lon': 82.9739, 'tier': 3},
    'lucknow': {'name': 'Lucknow', 'lat': 26.8467, 'lon': 80.9462, 'tier': 3},
    'kanpur': {'name': 'Kanpur', 'lat': 26.4499, 'lon': 80.3319, 'tier': 3},
    'agra': {'name': 'Agra', 'lat': 27.1767, 'lon': 78.0081, 'tier': 3},
    'meerut': {'name': 'Meerut', 'lat': 28.9845, 'lon': 77.7064, 'tier': 3},
    'noida': {'name': 'Noida', 'lat': 28.5355, 'lon': 77.3910, 'tier': 3},
    'ghaziabad': {'name': 'Ghaziabad', 'lat': 28.6692, 'lon': 77.4538, 'tier': 3},
}

# Premium plans configuration
PREMIUM_PLANS = {
    'week_1': {
        'name': '1 Week',
        'stars': 100,
        'days': 7,
        'display': '100⭐ – 1 Week'
    },
    'week_2': {
        'name': '2 Weeks',
        'stars': 150,
        'days': 14,
        'display': '150⭐ – 2 Weeks'
    },
    'month_1': {
        'name': '1 Month',
        'stars': 250,
        'days': 30,
        'display': '250⭐ – 1 Month'
    },
    'month_3': {
        'name': '3 Months',
        'stars': 500,
        'days': 90,
        'display': '500⭐ – 3 Months'
    }
}


# All messages
MESSAGES = {
    'welcome': """🔥 Welcome to DateEveryNight 🔥

Where hearts race, sparks fly,
and strangers turn into midnight fantasies 😏

Let's set your vibe…
Tell me your age (18–100) 😉""",

    'start_onboarding': """🔄 Let's start fresh 😏

Tell me your age (18–100) 😉""",

    'start_idle': """🔥 Ready to start a new night? 😏

Tell me your age (18–100) 😉""",

    'start_searching': """🔄 Search stopped 😏

Let's reset your vibe…
Tell me your age (18–100) 😉""",

    'start_chatting': """🔥 You ended the chat to start fresh 😏

Let's reset your vibe…
Tell me your age (18–100) 😉""",

    'start_chatting_other': """⚠️ Your match ended the chat 😏

You're back to browsing now…
Type /start when you're ready 🔥""",

    'start_blocked': """🚫 Your access is restricted.

Please contact support if you believe this is a mistake.""",

    'invalid_age': """😈 Slow down, trouble…
Give me a real age between 18 and 100.""",

    'gender_prompt': """Pick your energy tonight… who are you feeling like? 😏

👨 Male
👩 Female""",

    'preference_prompt': """Who do you want to get close to…
your next obsession? 😏

👨 Male
👩 Female""",


    'searching': """🔥 Profile locked in…

Now hunting for someone who can handle your vibe 😏
Someone out there is about to have a very exciting night…

Type /end anytime to stop.""",

    'match_found': """💥 MATCH FOUND!

Fate just matched you with someone irresistible…
Your mystery match is waiting 😏

Be bold. Be smooth. Turn up the heat 🔥""",

    'end_chat_user': """🔥 You ended the chat.

Plenty more sparks are waiting for you…
Type /reconnect when you're ready for another thrill 😉""",

    'end_chat_other': """⚠️ Your match slipped away… for now 😏
Don't worry — the next one might be even hotter.""",

    'report_success': """🚨 Report received.

We've shut it down.
Thanks for keeping DateEveryNight spicy… but classy 🔥""",

    'report_other': """⚠️ This chat has been ended by your match.""",

    'premium_required': """👑 PREMIUM REQUIRED

Looks like you've used up your free taste 😏

Go Premium to:
• Match without limits
• Skip the waiting line
• Meet hotter, faster, irresistible matches 🔥

👉 Type /premium to upgrade now""",

    'premium_header': """💎 Upgrade to DateEveryNight Premium

Unlimited matches.
Faster connections.
Priority access to the hottest people online 🔥""",

    'payment_success': """🎉 Payment Successful!

🔥 DateEveryNight Premium Activated 🔥

Plan: {plan_name}
Cost: {stars}⭐
Duration: {days} days
Expires: {expiration_date}

You're officially VIP now…
Type /start and let the flirting begin 😏""",

    'subscription_free': """📋 Your Subscription

🆓 Plan: Free
Status: No Premium ❌

Free Matches:
• Used: {used} / 2
• Remaining: {remaining}

👑 Premium unlocks unlimited matches & faster connections
👉 Type /premium to upgrade 😏""",

    'subscription_premium': """📋 Your Subscription

👑 Plan: {plan_name}
Status: Active 🔥
Days Remaining: {days_remaining}
Expires on: {expiration_date}

✨ Benefits:
• Unlimited matches
• Priority matching
• Faster connections

Enjoy the VIP life 😏""",

    'subscription_expired': """📋 Your Subscription

🆓 Plan: Free
Status: Premium Expired ❌

Free Matches:
• Used: {used} / 2
• Remaining: {remaining}

👉 Type /premium to renew your subscription 😏""",

    'menu': """📋 DateEveryNight Menu

/start – Start your night
/premium – Unlock VIP access
/subscription – Check your status
/support – Get help
/menu – Show this menu
/end – End current chat
/report – Report bad behavior
/reconnect – Find a new match""",

    'support': """📧 Need help or feeling stuck?

We've got your back 😏

Reach us anytime at:
dateeverynight@gmail.com

Whether it's a bug, a question,
or something that didn't feel right —
we're here to help 🔥""",

    'no_match': """🔍 No matches right now… but keep looking 😏
Type /end to stop searching.""",

    'not_in_chat': """⚠️ You're not in a chat right now.""",

    'reconnect_ready': """🔄 Ready for someone new? 😏

Type /start to jump back in
and update your vibe if you want 🔥""",

    'reconnect_invalid_state': """⚠️ You can use /reconnect only after ending a chat.""",

    'end_searching': """🛑 Search stopped.

No worries — you're back in control 😏
Type /start whenever you're ready to jump back in 🔥""",

    'end_chatting_user': """🔥 You ended the chat.

Plenty more sparks are waiting for you…
Type /reconnect when you're ready 😉""",

    'end_chatting_other': """⚠️ Your match ended the chat 😏

Don't worry — another spark is just a /start away 🔥""",

    'end_invalid_state': """⚠️ There's nothing to end right now 😌""",

    'welcome_back': """🔥 Welcome back to DateEveryNight 🔥

Type /menu to see your options 😏""",

    'already_premium': """👑 You're already premium! 🔥

Plan: {plan_name}
Expires: {expiration_date}

You're living the VIP life 😏
Unlimited matches. No limits. Pure vibe.""",

    'report_prompt': """What's the issue? (Type your reason)""",
}

def get_message(key, **kwargs):
    """Get message from MESSAGES dict with optional formatting"""
    message = MESSAGES.get(key, '')
    if kwargs:
        return message.format(**kwargs)
    return message

def get_match_found_message():
    """Generate match found message"""
    return "💥 MATCH FOUND!\n\nFate just matched you with someone irresistible…\nYour mystery match is waiting 😏\n\nBe bold. Be smooth. Turn up the heat 🔥"

def check_premium_expiration(user_id):
    """Check if user's premium subscription has expired and downgrade if necessary"""
    try:
        user = db.get_user(user_id)
        if not user:
            return False
        
        if not user['is_premium']:
            return False
        
        if user['premium_expires_at'] and user['premium_expires_at'] < datetime.now():
            db.downgrade_premium(user_id)
            logger.info(f"Premium expired for user {user_id}, downgraded to free")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking premium expiration: {e}")
        return False

async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_id: str):
    """Send an invoice for a premium plan using Telegram Stars (XTR)"""
    try:
        if plan_id not in PREMIUM_PLANS:
            logger.error(f"Invalid plan_id: {plan_id}")
            return
        
        plan = PREMIUM_PLANS[plan_id]
        user_id = update.effective_user.id
        
        payload = f"premium_{plan_id}_{user_id}"
        prices = [LabeledPrice(label="Premium Subscription", amount=plan['stars'])]
        
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"DateEveryNight Premium – {plan['name']}",
            description="Unlimited matches and priority access",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            is_flexible=False
        )
        
        logger.info(f"Invoice sent to user {user_id} for plan {plan_id}")
        
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        try:
            await update.callback_query.answer(
                "Error processing payment. Please try again.",
                show_alert=True
            )
        except:
            pass

async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query. Always approve unless payload is invalid."""
    try:
        query = update.pre_checkout_query
        
        if not query.payload or '_' not in query.payload:
            logger.warning(f"Invalid payload format: {query.payload}")
            await query.answer(ok=False, error_message="Invalid payment payload")
            return
        
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling pre-checkout: {e}")
        try:
            await query.answer(ok=False, error_message="Payment processing error")
        except:
            pass

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment and activate premium subscription"""
    try:
        payment = update.message.successful_payment
        user_id = update.effective_user.id
        
        payload_parts = payment.payload.split('_')
        if len(payload_parts) < 3 or payload_parts[0] != 'premium':
            logger.error(f"Invalid payload format: {payment.payload}")
            return
        
        plan_id = payload_parts[1]
        
        if plan_id not in PREMIUM_PLANS:
            logger.error(f"Invalid plan_id in payload: {plan_id}")
            return
        
        plan = PREMIUM_PLANS[plan_id]
        expiration_date = datetime.now() + timedelta(days=plan['days'])
        
        db.set_premium(user_id, plan['name'], plan['stars'], plan['days'])
        
        confirmation_msg = f"""🎉 Payment Successful!

🔥 DateEveryNight Premium Activated 🔥

Plan: {plan['name']}
Cost: {plan['stars']}⭐
Duration: {plan['days']} days
Expires: {expiration_date.strftime('%d %b %Y')}

You're officially VIP now…
Type /start and let the flirting begin 😏"""
        
        await update.message.reply_text(confirmation_msg)
        
        logger.info(f"Premium activated for user {user_id}: plan {plan_id}, expires {expiration_date}")
        
    except Exception as e:
        logger.error(f"Error handling successful payment: {e}")
        try:
            await update.message.reply_text(
                "Payment processed but there was an error activating your premium. Please contact support."
            )
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command - Main entry and reset command
    Works in all states except BLOCKED
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    db.create_user(user_id, username)
    user = db.get_user(user_id)
    
    if not user:
        return ConversationHandler.END
    
    check_premium_expiration(user_id)
    user = db.get_user(user_id)
    
    state = user['state']
    is_premium = db.is_premium(user_id)
    
    # CHECK: If user has exhausted free matches and is not premium, block them
    if not is_premium and user['free_matches_used'] >= 2:
        premium_msg = """🔒 Premium Required

You've used your 2 free chats!

To continue matching and chatting:
💰 Type /premium to upgrade

Premium Benefits:
✅ Unlimited matches
✅ Faster connections
✅ Match with anyone (no gender restriction)
✅ Priority matching

Type /premium to upgrade now! 🚀"""
        await update.message.reply_text(premium_msg)
        return ConversationHandler.END
    
    if state == 'BLOCKED':
        await update.message.reply_text(get_message('start_blocked'))
        return ConversationHandler.END
    
    elif state == 'NEW':
        db.set_user_state(user_id, 'ONBOARDING')
        await update.message.reply_text(get_message('welcome'))
        return AGE
    
    elif state == 'ONBOARDING':
        await update.message.reply_text(get_message('start_onboarding'))
        return AGE
    
    elif state == 'IDLE':
        db.set_user_state(user_id, 'ONBOARDING')
        await update.message.reply_text(get_message('start_idle'))
        return AGE
    
    elif state == 'SEARCHING':
        db.set_user_state(user_id, 'ONBOARDING')
        db.clear_search_start_time(user_id)
        await update.message.reply_text(get_message('start_searching'))
        return AGE
    
    elif state == 'CHATTING':
        match = db.get_match(user_id)
        
        if match:
            db.end_match(match['match_id'], user_id)
            other_user_id = db.get_other_user_in_match(match['match_id'], user_id)
            
            db.set_user_state(user_id, 'IDLE')
            db.set_user_state(user_id, 'ONBOARDING')
            db.clear_search_start_time(user_id)
            
            await update.message.reply_text(get_message('start_chatting'))
            
            try:
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=get_message('start_chatting_other')
                )
            except:
                pass
        else:
            db.set_user_state(user_id, 'ONBOARDING')
            await update.message.reply_text(get_message('start_chatting'))
        
        return AGE
    
    else:
        await update.message.reply_text(get_message('welcome'))
        return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if 18 <= age <= 100:
            context.user_data['age'] = age
            
            keyboard = [
                [InlineKeyboardButton("👨 Male", callback_data='gender_male')],
                [InlineKeyboardButton("👩 Female", callback_data='gender_female')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                get_message('gender_prompt'),
                reply_markup=reply_markup
            )
            return GENDER
        else:
            await update.message.reply_text(get_message('invalid_age'))
            return AGE
    except ValueError:
        await update.message.reply_text(get_message('invalid_age'))
        return AGE

async def gender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gender = 'Male' if query.data == 'gender_male' else 'Female'
    context.user_data['gender'] = gender
    
    keyboard = [
        [InlineKeyboardButton("👨 Male", callback_data='pref_male')],
        [InlineKeyboardButton("👩 Female", callback_data='pref_female')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_message('preference_prompt'),
        reply_markup=reply_markup
    )
    
    return PREFERENCE

async def preference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    preference = 'Male' if query.data == 'pref_male' else 'Female'
    context.user_data['preference'] = preference
    
    await query.edit_message_text(
        "🏙️ Type your city name (e.g., Bengaluru, Mumbai, Delhi, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad)\n\nOr type 'skip' to match with anyone 😉"
    )
    
    return CITY

async def city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city_input = update.message.text.strip()
    
    age = context.user_data.get('age')
    gender = context.user_data.get('gender')
    preference = context.user_data.get('preference')
    
    city = None
    latitude = None
    longitude = None
    
    city_input_lower = city_input.lower()
    
    if city_input_lower == 'skip':
        city = None
        latitude = None
        longitude = None
    else:
        # Check if city exists in our database
        for city_key, city_info in CITIES.items():
            if city_info['name'].lower() == city_input_lower:
                city = city_info['name']
                latitude = city_info['lat']
                longitude = city_info['lon']
                break
        
        if not city:
            await update.message.reply_text(
                f"❌ City '{city_input}' not found.\n\nTry cities like: Bengaluru, Mumbai, Delhi, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, etc.\n\nOr type 'skip' to match with anyone 😉"
            )
            return CITY
    
    db.update_user_profile(user_id, age, gender, preference, city, latitude, longitude)
    db.set_user_state(user_id, 'SEARCHING')
    
    await update.message.reply_text(get_message('searching'))
    
    return ConversationHandler.END

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_message('menu'))

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    check_premium_expiration(user_id)
    user = db.get_user(user_id)
    
    if user and user['is_premium'] and user['premium_expires_at'] and user['premium_expires_at'] > datetime.now():
        await update.message.reply_text(
            get_message('subscription_premium', 
                       plan_name=user['premium_plan'], 
                       days_remaining=(user['premium_expires_at'] - datetime.now()).days, 
                       expiration_date=user['premium_expires_at'].strftime('%d %b %Y'))
        )
        return
    
    await update.message.reply_text(get_message('premium_header'))
    
    keyboard = [
        [InlineKeyboardButton(PREMIUM_PLANS['week_1']['display'], callback_data='premium_week_1')],
        [InlineKeyboardButton(PREMIUM_PLANS['week_2']['display'], callback_data='premium_week_2')],
        [InlineKeyboardButton(PREMIUM_PLANS['month_1']['display'], callback_data='premium_month_1')],
        [InlineKeyboardButton(PREMIUM_PLANS['month_3']['display'], callback_data='premium_month_3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Choose your plan:",
        reply_markup=reply_markup
    )

async def premium_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_id = query.data.replace('premium_', '')
    
    if plan_id not in PREMIUM_PLANS:
        await query.answer("Invalid plan", show_alert=True)
        return
    
    await send_invoice(update, context, plan_id)

async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read-only subscription status display with 3 cases"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    check_premium_expiration(user_id)
    user = db.get_user(user_id)
    
    remaining = db.get_free_matches_remaining(user_id)
    used = user['free_matches_used']
    
    if user['is_premium'] and user['premium_expires_at'] and user['premium_expires_at'] > datetime.now():
        days_remaining = (user['premium_expires_at'] - datetime.now()).days
        await update.message.reply_text(
            get_message('subscription_premium', 
                       plan_name=user['premium_plan'], 
                       days_remaining=days_remaining, 
                       expiration_date=user['premium_expires_at'].strftime('%d %b %Y'))
        )
    elif user['is_premium'] and user['premium_expires_at'] and user['premium_expires_at'] <= datetime.now():
        await update.message.reply_text(
            get_message('subscription_expired', used=used, remaining=remaining)
        )
    else:
        await update.message.reply_text(
            get_message('subscription_free', used=used, remaining=remaining)
        )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_message('support'))

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /end command - Strict state-based behavior
    SEARCHING→IDLE, CHATTING→IDLE with notifications
    """
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    state = user['state']
    
    if state == 'SEARCHING':
        db.set_user_state(user_id, 'IDLE')
        db.clear_search_start_time(user_id)
        await update.message.reply_text(get_message('end_searching'))
        return
    
    elif state == 'CHATTING':
        match = db.get_match(user_id)
        
        if not match:
            await update.message.reply_text(get_message('end_invalid_state'))
            return
        
        db.end_match(match['match_id'], user_id)
        db.set_user_state(user_id, 'IDLE')
        db.clear_search_start_time(user_id)
        
        other_user_id = db.get_other_user_in_match(match['match_id'], user_id)
        
        await update.message.reply_text(get_message('end_chatting_user'))
        
        try:
            await context.bot.send_message(
                chat_id=other_user_id,
                text=get_message('end_chatting_other')
            )
        except:
            pass
        
        return
    
    else:
        await update.message.reply_text(get_message('end_invalid_state'))

async def reconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reconnect command - Works only when user state is IDLE
    """
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    if user['state'] != 'IDLE':
        await update.message.reply_text(get_message('reconnect_invalid_state'))
        return
    
    await update.message.reply_text(get_message('reconnect_ready'))

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    match = db.get_match(user_id)
    
    if not match:
        await update.message.reply_text(get_message('not_in_chat'))
        return
    
    other_user_id = db.get_other_user_in_match(match['match_id'], user_id)
    db.block_user(user_id, other_user_id, 'User reported')
    db.report_user(user_id, other_user_id, 'User reported')
    db.end_match(match['match_id'], user_id)
    db.set_user_state(user_id, 'IDLE')
    db.clear_search_start_time(user_id)
    
    await update.message.reply_text(get_message('report_success'))
    
    try:
        await context.bot.send_message(
            chat_id=other_user_id,
            text=get_message('report_other')
        )
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    state = user['state']
    
    if state == 'SEARCHING':
        await update.message.reply_text("🔍 You're in the waiting pool. Please wait while we find your match...")
        return
    
    elif state == 'CHATTING':
        match = db.get_match(user_id)
        if match:
            other_user_id = db.get_other_user_in_match(match['match_id'], user_id)
            db.save_message(match['match_id'], user_id, update.message.text)
            
            try:
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=update.message.text
                )
            except:
                pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def periodic_match_check(context: ContextTypes.DEFAULT_TYPE):
    """Periodically check for matches among users in SEARCHING state - optimized for 25,000+ users"""
    try:
        searching_users = db.get_searching_users()
        num_users = len(searching_users)
        
        if num_users == 0:
            return
        
        logger.debug(f"Periodic match check: {num_users} users in SEARCHING state")
        
        # For small numbers of users, use individual matching
        if num_users < 100:
            for user in searching_users:
                user_id = user['user_id']
                match_user = db.find_match(user_id)
                
                if match_user:
                    match_id = db.create_match(user_id, match_user['user_id'])
                    
                    if match_id:
                        # Increment free matches for both users if they're not premium
                        is_premium_1 = db.is_premium(user_id)
                        is_premium_2 = db.is_premium(match_user['user_id'])
                        
                        if not is_premium_1:
                            db.increment_free_matches(user_id)
                        if not is_premium_2:
                            db.increment_free_matches(match_user['user_id'])
                        
                        db.set_user_state(user_id, 'CHATTING')
                        db.set_user_state(match_user['user_id'], 'CHATTING')
                        db.clear_search_start_time(user_id)
                        db.clear_search_start_time(match_user['user_id'])
                        
                        match_msg = get_match_found_message()
                        
                        try:
                            await context.bot.send_message(chat_id=user_id, text=match_msg)
                        except Exception as e:
                            logger.debug(f"Failed to send message to {user_id}: {e}")
                        
                        try:
                            await context.bot.send_message(chat_id=match_user['user_id'], text=match_msg)
                        except Exception as e:
                            logger.debug(f"Failed to send message to {match_user['user_id']}: {e}")
                        
                        logger.info(f"Match created: {user_id} <-> {match_user['user_id']}")
        else:
            # For large numbers of users, use batch matching
            user_ids = [u['user_id'] for u in searching_users]
            matches = db.batch_find_matches(user_ids)
            
            logger.info(f"Batch matching: {len(matches)} matches created from {num_users} users")
            
            # Process matches asynchronously
            for user1_id, user2_id in matches:
                try:
                    is_premium_1 = db.is_premium(user1_id)
                    is_premium_2 = db.is_premium(user2_id)
                    
                    if not is_premium_1:
                        db.increment_free_matches(user1_id)
                    if not is_premium_2:
                        db.increment_free_matches(user2_id)
                    
                    match_id = db.create_match(user1_id, user2_id)
                    
                    if match_id:
                        db.set_user_state(user1_id, 'CHATTING')
                        db.set_user_state(user2_id, 'CHATTING')
                        db.clear_search_start_time(user1_id)
                        db.clear_search_start_time(user2_id)
                        
                        match_msg = get_match_found_message()
                        
                        # Send messages with rate limiting
                        try:
                            await context.bot.send_message(chat_id=user1_id, text=match_msg)
                        except Exception as e:
                            logger.debug(f"Failed to send message to {user1_id}: {e}")
                        
                        try:
                            await context.bot.send_message(chat_id=user2_id, text=match_msg)
                        except Exception as e:
                            logger.debug(f"Failed to send message to {user2_id}: {e}")
                        
                        logger.debug(f"Batch match created: {user1_id} <-> {user2_id}")
                except Exception as e:
                    logger.error(f"Error processing batch match {user1_id} <-> {user2_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in periodic match check: {e}", exc_info=True)

def main():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except RuntimeError as e:
        logger.warning(f"Could not create new event loop: {e}")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
                GENDER: [CallbackQueryHandler(gender_callback)],
                PREFERENCE: [CallbackQueryHandler(preference_callback)],
                CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_handler)],
            },
            fallbacks=[CommandHandler('menu', menu), CommandHandler('start', start)],
            per_message=False,
        )
        
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('menu', menu))
        application.add_handler(CommandHandler('premium', premium))
        application.add_handler(CallbackQueryHandler(premium_plan_callback, pattern='^premium_'))
        application.add_handler(CommandHandler('subscription', subscription))
        application.add_handler(CommandHandler('support', support))
        application.add_handler(CommandHandler('end', end_chat))
        application.add_handler(CommandHandler('reconnect', reconnect))
        application.add_handler(CommandHandler('report', report))
        
        application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
        async def successful_payment_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_successful_payment(update, context)
        application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_wrapper))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        application.add_error_handler(error_handler)
        
        application.job_queue.run_repeating(periodic_match_check, interval=5, first=1)
        
        logger.info("Starting DateEveryNight bot...")
        logger.info("Bot is now running and listening for messages...")
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import math
import logging
import time

logger = logging.getLogger(__name__)

# Database schema SQL
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    age INT,
    gender VARCHAR(10),
    preference VARCHAR(10),
    city VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    state VARCHAR(50) DEFAULT 'NEW',
    is_premium BOOLEAN DEFAULT FALSE,
    premium_plan VARCHAR(100),
    premium_expires_at TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE,
    free_matches_used INT DEFAULT 0,
    search_start_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    match_id SERIAL PRIMARY KEY,
    user1_id BIGINT REFERENCES users(user_id),
    user2_id BIGINT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    ended_by BIGINT
);

CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    match_id INT REFERENCES matches(match_id),
    sender_id BIGINT REFERENCES users(user_id),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blocked_pairs (
    id SERIAL PRIMARY KEY,
    blocker_id BIGINT REFERENCES users(user_id),
    blocked_id BIGINT REFERENCES users(user_id),
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blocker_id, blocked_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id SERIAL PRIMARY KEY,
    reporter_id BIGINT REFERENCES users(user_id),
    reported_id BIGINT REFERENCES users(user_id),
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS premium_transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    plan_name VARCHAR(100),
    stars_cost INT,
    duration_days INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, database_url):
        self.database_url = database_url
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema on startup"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")

    def get_connection(self, max_retries=3, retry_delay=2):
        """Get database connection with retry logic"""
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(self.database_url)
                if attempt > 0:
                    logger.info(f"Database connection established after {attempt} retries")
                return conn
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise

    def create_user(self, user_id, username):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (user_id, username, state) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, username, 'NEW')
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error creating user: {e}")

    def get_user(self, user_id):
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def update_user_profile(self, user_id, age, gender, preference, city, latitude, longitude):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET age = %s, gender = %s, preference = %s, city = %s, 
                       latitude = %s, longitude = %s, state = %s, updated_at = %s 
                       WHERE user_id = %s""",
                    (age, gender, preference, city, latitude, longitude, 'IDLE', datetime.now(), user_id)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")

    def set_user_state(self, user_id, state):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                if state == 'SEARCHING':
                    cur.execute(
                        "UPDATE users SET state = %s, search_start_time = %s, updated_at = %s WHERE user_id = %s",
                        (state, datetime.now(), datetime.now(), user_id)
                    )
                else:
                    cur.execute(
                        "UPDATE users SET state = %s, updated_at = %s WHERE user_id = %s",
                        (state, datetime.now(), user_id)
                    )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error setting user state: {e}")

    def get_user_state(self, user_id):
        user = self.get_user(user_id)
        return user['state'] if user else None
    
    def get_searching_users(self):
        """Get all users currently in SEARCHING state"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE state = 'SEARCHING' AND is_blocked = FALSE ORDER BY search_start_time ASC"
                )
                results = cur.fetchall()
            conn.close()
            return results if results else []
        except Exception as e:
            logger.error(f"Error getting searching users: {e}")
            return []
    
    def clear_search_start_time(self, user_id):
        """Clear search_start_time when user exits SEARCHING state"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET search_start_time = NULL WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error clearing search start time: {e}")

    def find_match(self, user_id):
        """
        Distance-aware matching algorithm with location-based priority windows.
        
        ELIGIBILITY CHECK:
        - state == SEARCHING
        - is_premium OR free_matches_used < 2
        - NOT blocked
        
        COMPATIBILITY:
        - A.gender == B.preference AND B.gender == A.preference
        - Bidirectional preference match required
        
        LOCATION PRIORITY WINDOWS:
        1. SAME CITY (0-30s): Highest priority
        2. NEARBY (30s+, ≤50km): Medium priority
        3. REGIONAL (≤300km): Lower priority
        4. FALLBACK (anywhere): Last resort
        """
        try:
            user = self.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # ELIGIBILITY CHECK
            if user['state'] != 'SEARCHING':
                logger.debug(f"User {user_id} not in SEARCHING state")
                return None
            
            is_premium = self.is_premium(user_id)
            if not is_premium and user['free_matches_used'] >= 2:
                logger.debug(f"User {user_id} exceeded free match limit")
                return None
            
            if user['is_blocked']:
                logger.debug(f"User {user_id} is blocked")
                return None
            
            conn = self.get_connection()
            
            # FETCH ALL ELIGIBLE CANDIDATES IN SEARCHING STATE
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM users 
                    WHERE user_id != %s 
                    AND state = 'SEARCHING'
                    AND is_blocked = FALSE
                    AND user_id NOT IN (
                        SELECT blocked_id FROM blocked_pairs WHERE blocker_id = %s
                        UNION
                        SELECT blocker_id FROM blocked_pairs WHERE blocked_id = %s
                    )
                    AND user_id NOT IN (
                        SELECT user2_id FROM matches WHERE user1_id = %s
                        UNION
                        SELECT user1_id FROM matches WHERE user2_id = %s
                    )
                """, (user_id, user_id, user_id, user_id, user_id))
                
                candidates = cur.fetchall()
            
            conn.close()
            
            if not candidates:
                logger.debug(f"No candidates found for user {user_id}")
                return None
            
            # FILTER BY BIDIRECTIONAL PREFERENCE COMPATIBILITY
            compatible = []
            for candidate in candidates:
                if user['gender'] == candidate['preference'] and candidate['gender'] == user['preference']:
                    compatible.append(candidate)
            
            if not compatible:
                logger.debug(f"No compatible candidates for user {user_id}")
                return None
            
            # APPLY LOCATION-BASED PRIORITY WINDOWS
            current_time = datetime.now()
            search_duration = (current_time - user['search_start_time']).total_seconds() if user['search_start_time'] else 0
            
            # WINDOW 1: SAME CITY or STAY MYSTERIOUS (0-30 seconds)
            if search_duration <= 30:
                if user['city']:
                    same_city = [c for c in compatible if c['city'] == user['city'] and c['city'] is not None]
                    if same_city:
                        logger.info(f"Match found in WINDOW 1 (same city) for user {user_id}")
                        return same_city[0]
                    mysterious = [c for c in compatible if c['city'] is None]
                    if mysterious:
                        logger.info(f"Match found in WINDOW 1 (city + stay mysterious) for user {user_id}")
                        return mysterious[0]
                else:
                    any_match = [c for c in compatible]
                    if any_match:
                        logger.info(f"Match found in WINDOW 1 (stay mysterious) for user {user_id}")
                        return any_match[0]
            
            # WINDOW 2: NEARBY (>30s, ≤50km)
            if search_duration > 30:
                nearby = []
                for candidate in compatible:
                    if candidate['latitude'] and candidate['longitude'] and user['latitude'] and user['longitude']:
                        distance = self._haversine_distance(
                            user['latitude'], user['longitude'],
                            candidate['latitude'], candidate['longitude']
                        )
                        if distance <= 50:
                            nearby.append((candidate, distance))
                
                if nearby:
                    nearby.sort(key=lambda x: x[1])
                    logger.info(f"Match found in WINDOW 2 (nearby ≤50km) for user {user_id}")
                    return nearby[0][0]
            
            # WINDOW 3: REGIONAL (≤300km)
            regional = []
            for candidate in compatible:
                if candidate['latitude'] and candidate['longitude'] and user['latitude'] and user['longitude']:
                    distance = self._haversine_distance(
                        user['latitude'], user['longitude'],
                        candidate['latitude'], candidate['longitude']
                    )
                    if distance <= 300:
                        regional.append((candidate, distance))
            
            if regional:
                regional.sort(key=lambda x: x[1])
                logger.info(f"Match found in WINDOW 3 (regional ≤300km) for user {user_id}")
                return regional[0][0]
            
            # WINDOW 4: FALLBACK (anywhere, including users without location data)
            if compatible:
                logger.info(f"Match found in WINDOW 4 (fallback) for user {user_id}")
                return compatible[0]
            
            logger.debug(f"No match found for user {user_id} in any window")
            return None
            
        except Exception as e:
            logger.error(f"Error finding match: {e}")
            return None

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def create_match(self, user1_id, user2_id):
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO matches (user1_id, user2_id) VALUES (%s, %s) 
                       ON CONFLICT DO NOTHING RETURNING match_id""",
                    (user1_id, user2_id)
                )
                result = cur.fetchone()
                conn.commit()
            conn.close()
            return result['match_id'] if result else None
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return None

    def get_match(self, user_id):
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM matches 
                    WHERE (user1_id = %s OR user2_id = %s) 
                    AND ended_at IS NULL
                """, (user_id, user_id))
                result = cur.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error getting match: {e}")
            return None

    def end_match(self, match_id, ended_by):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE matches SET ended_at = %s, ended_by = %s WHERE match_id = %s",
                    (datetime.now(), ended_by, match_id)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error ending match: {e}")

    def get_other_user_in_match(self, match_id, user_id):
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT CASE 
                        WHEN user1_id = %s THEN user2_id 
                        ELSE user1_id 
                    END as other_user_id
                    FROM matches WHERE match_id = %s
                """, (user_id, match_id))
                result = cur.fetchone()
            conn.close()
            return result['other_user_id'] if result else None
        except Exception as e:
            logger.error(f"Error getting other user: {e}")
            return None

    def increment_free_matches(self, user_id):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET free_matches_used = free_matches_used + 1 WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error incrementing free matches: {e}")

    def get_free_matches_remaining(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        return max(0, 2 - user['free_matches_used'])

    def is_premium(self, user_id):
        user = self.get_user(user_id)
        if not user or not user['is_premium']:
            return False
        
        if user['premium_expires_at']:
            return user['premium_expires_at'] > datetime.now()
        
        return False

    def set_premium(self, user_id, plan_name, stars_cost, duration_days):
        try:
            expires_at = datetime.now() + timedelta(days=duration_days)
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET is_premium = TRUE, premium_plan = %s, 
                       premium_expires_at = %s WHERE user_id = %s""",
                    (plan_name, expires_at, user_id)
                )
                cur.execute(
                    """INSERT INTO premium_transactions (user_id, plan_name, stars_cost, duration_days) 
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, plan_name, stars_cost, duration_days)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error setting premium: {e}")
    
    def downgrade_premium(self, user_id):
        """Downgrade user from premium to free (called when premium expires)"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET is_premium = FALSE, premium_plan = NULL, 
                       premium_expires_at = NULL WHERE user_id = %s""",
                    (user_id,)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error downgrading premium: {e}")

    def block_user(self, blocker_id, blocked_id, reason):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO blocked_pairs (blocker_id, blocked_id, reason) 
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    (blocker_id, blocked_id, reason)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error blocking user: {e}")

    def report_user(self, reporter_id, reported_id, reason):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO reports (reporter_id, reported_id, reason) 
                       VALUES (%s, %s, %s)""",
                    (reporter_id, reported_id, reason)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error reporting user: {e}")

    def save_message(self, match_id, sender_id, content):
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO messages (match_id, sender_id, content) 
                       VALUES (%s, %s, %s)""",
                    (match_id, sender_id, content)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving message: {e}")

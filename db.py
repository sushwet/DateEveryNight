import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from datetime import datetime, timedelta
import math
import logging
import time
from threading import Lock

logger = logging.getLogger(__name__)

# Connection pool for better resource management
connection_pool = None
pool_lock = Lock()

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
        self.connection_pool = None
        self._init_pool()
        self._init_schema()

    def _init_pool(self):
        """Initialize connection pool for better resource management"""
        try:
            # Close any existing pool first (in case of restart)
            if self.connection_pool:
                try:
                    self.connection_pool.closeall()
                except:
                    pass
            
            self.connection_pool = pool.SimpleConnectionPool(
                10,  # Minimum connections
                50,  # Maximum connections
                self.database_url,
                connect_timeout=5
            )
            logger.info("Database connection pool initialized (10-50 connections)")
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise

    def _init_schema(self):
        """Initialize database schema on startup"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
        finally:
            if conn:
                self.return_connection(conn)
    
    def health_check(self):
        """Verify database connection is working"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)

    def get_connection(self, max_retries=3, retry_delay=1):
        """Get database connection from pool with retry logic"""
        for attempt in range(max_retries):
            try:
                conn = self.connection_pool.getconn()
                if attempt > 0:
                    logger.debug(f"Database connection obtained after {attempt} retries")
                return conn
            except pool.PoolError as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Connection pool attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Connection pool exhausted after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise

    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            self.connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")

    def create_user(self, user_id, username):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (user_id, username, state) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, username, 'NEW')
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error creating user: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def get_user(self, user_id):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
            return result
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def update_user_profile(self, user_id, age, gender, preference, city, latitude, longitude):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET age = %s, gender = %s, preference = %s, city = %s, 
                       latitude = %s, longitude = %s, updated_at = %s 
                       WHERE user_id = %s""",
                    (age, gender, preference, city, latitude, longitude, datetime.now(), user_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def set_user_state(self, user_id, state):
        conn = None
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
        except Exception as e:
            logger.error(f"Error setting user state: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def get_user_state(self, user_id):
        user = self.get_user(user_id)
        return user['state'] if user else None
    
    def get_searching_users(self):
        """Get all users currently in SEARCHING state - optimized for batch processing"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, username, state, search_start_time FROM users WHERE state = 'SEARCHING' AND is_blocked = FALSE ORDER BY search_start_time ASC"
                )
                results = cur.fetchall()
            return results if results else []
        except Exception as e:
            logger.error(f"Error getting searching users: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    def clear_search_start_time(self, user_id):
        """Clear search_start_time when user exits SEARCHING state"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET search_start_time = NULL WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error clearing search start time: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def find_match(self, user_id):
        """
        Dual matching algorithm:
        
        FOR FREE USERS (free_matches_used < 2):
        - MUST match Male ↔ Female only
        - Priority 1: Same city + opposite gender
        - Priority 2: Any city + opposite gender
        
        FOR PREMIUM USERS (is_premium OR free_matches_used >= 2):
        - Can match with anyone (no gender restriction)
        - Priority 1: Same city
        - Priority 2: Any city
        """
        conn = None
        try:
            user = self.get_user(user_id)
            if not user:
                logger.debug(f"User {user_id} not found")
                return None
            
            # ELIGIBILITY CHECK
            if user['state'] != 'SEARCHING':
                logger.debug(f"User {user_id} not in SEARCHING state: {user['state']}")
                return None
            
            is_premium = self.is_premium(user_id)
            if not is_premium and user['free_matches_used'] >= 2:
                logger.debug(f"User {user_id} exceeded free match limit")
                return None
            
            if user['is_blocked']:
                logger.debug(f"User {user_id} is blocked")
                return None
            
            conn = self.get_connection()
            if not conn:
                return None
            
            # Determine if user is in free tier
            is_free_user = not is_premium and user['free_matches_used'] < 2
            
            # PRIORITY 1: SAME CITY
            if user['city']:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if is_free_user:
                        # Free users: must match opposite gender
                        opposite_gender = 'Female' if user['gender'] == 'Male' else 'Male'
                        cur.execute("""
                            SELECT user_id, username FROM users 
                            WHERE user_id != %s 
                            AND state = 'SEARCHING'
                            AND is_blocked = FALSE
                            AND city = %s
                            AND gender = %s
                            AND user_id NOT IN (
                                SELECT user2_id FROM matches WHERE user1_id = %s AND ended_at IS NULL
                                UNION
                                SELECT user1_id FROM matches WHERE user2_id = %s AND ended_at IS NULL
                            )
                            ORDER BY search_start_time ASC
                            LIMIT 1
                        """, (user_id, user['city'], opposite_gender, user_id, user_id))
                    else:
                        # Premium users: match anyone
                        cur.execute("""
                            SELECT user_id, username FROM users 
                            WHERE user_id != %s 
                            AND state = 'SEARCHING'
                            AND is_blocked = FALSE
                            AND city = %s
                            AND user_id NOT IN (
                                SELECT user2_id FROM matches WHERE user1_id = %s AND ended_at IS NULL
                                UNION
                                SELECT user1_id FROM matches WHERE user2_id = %s AND ended_at IS NULL
                            )
                            ORDER BY search_start_time ASC
                            LIMIT 1
                        """, (user_id, user['city'], user_id, user_id))
                    
                    candidate = cur.fetchone()
                    if candidate:
                        match_type = "same city (opposite gender)" if is_free_user else "same city"
                        logger.info(f"Match found for {user_id}: {match_type}")
                        return candidate
            
            # PRIORITY 2: ANY CITY (fallback)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if is_free_user:
                    # Free users: must match opposite gender
                    opposite_gender = 'Female' if user['gender'] == 'Male' else 'Male'
                    cur.execute("""
                        SELECT user_id, username FROM users 
                        WHERE user_id != %s 
                        AND state = 'SEARCHING'
                        AND is_blocked = FALSE
                        AND gender = %s
                        AND user_id NOT IN (
                            SELECT user2_id FROM matches WHERE user1_id = %s AND ended_at IS NULL
                            UNION
                            SELECT user1_id FROM matches WHERE user2_id = %s AND ended_at IS NULL
                        )
                        ORDER BY search_start_time ASC
                        LIMIT 1
                    """, (user_id, opposite_gender, user_id, user_id))
                else:
                    # Premium users: match anyone
                    cur.execute("""
                        SELECT user_id, username FROM users 
                        WHERE user_id != %s 
                        AND state = 'SEARCHING'
                        AND is_blocked = FALSE
                        AND user_id NOT IN (
                            SELECT user2_id FROM matches WHERE user1_id = %s AND ended_at IS NULL
                            UNION
                            SELECT user1_id FROM matches WHERE user2_id = %s AND ended_at IS NULL
                        )
                        ORDER BY search_start_time ASC
                        LIMIT 1
                    """, (user_id, user_id, user_id))
                
                candidate = cur.fetchone()
            
            if not candidate:
                match_type = "opposite gender" if is_free_user else "any user"
                logger.debug(f"No {match_type} candidates found for user {user_id}")
                return None
            
            match_type = "any city (opposite gender)" if is_free_user else "any city"
            logger.info(f"Match found for {user_id}: {match_type}")
            return candidate
            
        except Exception as e:
            logger.error(f"Error finding match: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def batch_find_matches(self, user_ids):
        """
        Batch matching for multiple users - highly optimized for 25,000+ users.
        Returns list of (user_id, match_user_id) tuples.
        """
        conn = None
        try:
            if not user_ids:
                return []
            
            conn = self.get_connection()
            if not conn:
                return []
            
            matches = []
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all eligible users in one query
                placeholders = ','.join(['%s'] * len(user_ids))
                cur.execute(f"""
                    SELECT user_id, username, search_start_time FROM users 
                    WHERE user_id IN ({placeholders})
                    AND state = 'SEARCHING'
                    AND is_blocked = FALSE
                    ORDER BY search_start_time ASC
                """, user_ids)
                
                eligible_users = cur.fetchall()
            
            # Pair up users efficiently
            for i in range(0, len(eligible_users) - 1, 2):
                user1 = eligible_users[i]
                user2 = eligible_users[i + 1]
                matches.append((user1['user_id'], user2['user_id']))
            
            logger.info(f"Batch matching: {len(matches)} matches found from {len(user_ids)} users")
            return matches
            
        except Exception as e:
            logger.error(f"Error in batch matching: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

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
        conn = None
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
            return result['match_id'] if result else None
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_match(self, user_id):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM matches 
                    WHERE (user1_id = %s OR user2_id = %s) 
                    AND ended_at IS NULL
                """, (user_id, user_id))
                result = cur.fetchone()
            return result
        except Exception as e:
            logger.error(f"Error getting match: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def end_match(self, match_id, ended_by):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE matches SET ended_at = %s, ended_by = %s WHERE match_id = %s",
                    (datetime.now(), ended_by, match_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error ending match: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def get_other_user_in_match(self, match_id, user_id):
        conn = None
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
            return result['other_user_id'] if result else None
        except Exception as e:
            logger.error(f"Error getting other user: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def increment_free_matches(self, user_id):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET free_matches_used = free_matches_used + 1 WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing free matches: {e}")
        finally:
            if conn:
                self.return_connection(conn)

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
        conn = None
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
        except Exception as e:
            logger.error(f"Error setting premium: {e}")
        finally:
            if conn:
                self.return_connection(conn)
    
    def downgrade_premium(self, user_id):
        """Downgrade user from premium to free (called when premium expires)"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET is_premium = FALSE, premium_plan = NULL, 
                       premium_expires_at = NULL WHERE user_id = %s""",
                    (user_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error downgrading premium: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def block_user(self, blocker_id, blocked_id, reason):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO blocked_pairs (blocker_id, blocked_id, reason) 
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    (blocker_id, blocked_id, reason)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def report_user(self, reporter_id, reported_id, reason):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO reports (reporter_id, reported_id, reason) 
                       VALUES (%s, %s, %s)""",
                    (reporter_id, reported_id, reason)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error reporting user: {e}")
        finally:
            if conn:
                self.return_connection(conn)

    def save_message(self, match_id, sender_id, content):
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO messages (match_id, sender_id, content) 
                       VALUES (%s, %s, %s)""",
                    (match_id, sender_id, content)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving message: {e}")
        finally:
            if conn:
                self.return_connection(conn)

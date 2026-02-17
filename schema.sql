-- DateEveryNight Database Schema

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    age INT,
    gender VARCHAR(10),
    preference VARCHAR(10),
    city VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    state VARCHAR(50) DEFAULT 'NEW',
    free_matches_used INT DEFAULT 0,
    is_premium BOOLEAN DEFAULT FALSE,
    premium_plan VARCHAR(50),
    premium_expires_at TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE,
    search_start_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS city_coordinates (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(255) UNIQUE,
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blocked_pairs (
    block_id SERIAL PRIMARY KEY,
    blocker_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    blocked_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blocker_id, blocked_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id SERIAL PRIMARY KEY,
    reporter_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    reported_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    reason VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    match_id SERIAL PRIMARY KEY,
    user1_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    user2_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    ended_by BIGINT,
    UNIQUE(user1_id, user2_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
    sender_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS premium_transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    plan_name VARCHAR(50),
    stars_cost INT,
    duration_days INT,
    telegram_payment_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_state ON users(state);
CREATE INDEX idx_users_gender ON users(gender);
CREATE INDEX idx_users_preference ON users(preference);
CREATE INDEX idx_users_city ON users(city);
CREATE INDEX idx_users_premium ON users(is_premium);
CREATE INDEX idx_blocked_pairs ON blocked_pairs(blocker_id, blocked_id);
CREATE INDEX idx_matches_users ON matches(user1_id, user2_id);

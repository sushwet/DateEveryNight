import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get all searching users
cur.execute('SELECT user_id, username, state FROM users WHERE state = %s', ('SEARCHING',))
searching = cur.fetchall()
print(f"=== All SEARCHING users ===")
for u in searching:
    print(f"User {u['user_id']}: {u['username']}")

# Test the find_match query for first user
if searching:
    user_id = searching[0]['user_id']
    print(f"\n=== Testing find_match query for User {user_id} ===")
    
    # Step 1: Check basic eligibility
    cur.execute('SELECT user_id, state, is_blocked FROM users WHERE user_id = %s', (user_id,))
    user = cur.fetchone()
    print(f"User state: {user['state']}, is_blocked: {user['is_blocked']}")
    
    # Step 2: Check blocked pairs
    cur.execute("""
        SELECT blocked_id FROM blocked_pairs WHERE blocker_id = %s
        UNION
        SELECT blocker_id FROM blocked_pairs WHERE blocked_id = %s
    """, (user_id, user_id))
    blocked = cur.fetchall()
    print(f"Blocked users: {[b['blocked_id'] for b in blocked]}")
    
    # Step 3: Check existing matches
    cur.execute("""
        SELECT user2_id FROM matches WHERE user1_id = %s
        UNION
        SELECT user1_id FROM matches WHERE user2_id = %s
    """, (user_id, user_id))
    matched = cur.fetchall()
    print(f"Already matched with: {[m['user1_id'] if 'user1_id' in m else m['user2_id'] for m in matched]}")
    
    # Step 4: Run the full query
    print(f"\n=== Running full find_match query ===")
    cur.execute("""
        SELECT user_id, username, state FROM users 
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
        ORDER BY search_start_time ASC
        LIMIT 1
    """, (user_id, user_id, user_id, user_id, user_id))
    
    candidate = cur.fetchone()
    if candidate:
        print(f"Found candidate: User {candidate['user_id']} ({candidate['username']})")
    else:
        print("No candidate found!")
        
        # Debug: Check all SEARCHING users except self
        print(f"\n=== All SEARCHING users except {user_id} ===")
        cur.execute("""
            SELECT user_id, username, state, is_blocked FROM users 
            WHERE user_id != %s AND state = 'SEARCHING'
        """, (user_id,))
        others = cur.fetchall()
        for o in others:
            print(f"User {o['user_id']}: {o['username']} - state: {o['state']}, blocked: {o['is_blocked']}")

conn.close()

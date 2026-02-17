import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def setup_database():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set in .env file")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        cursor.execute(schema)
        conn.commit()
        
        print("✅ Database schema created successfully!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ schema.sql file not found")
        sys.exit(1)

if __name__ == '__main__':
    setup_database()

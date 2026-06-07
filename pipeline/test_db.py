from src.config import DATABASE_URL
import psycopg

conn = psycopg.connect(DATABASE_URL, connect_timeout=10)
print("connected")
conn.close()

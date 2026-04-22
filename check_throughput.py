import psycopg2 

conn = psycopg2.connect(
    dbname="news_db",
    user="user",
    password="password",
    host="localhost", 
    port="5433"        
)
cur = conn.cursor()

# Get the total count of every article ever processed
cur.execute("SELECT COUNT(*) FROM news_sentiment;")
total = cur.fetchone()[0]

print(f"Total articles in database: {total}")

cur.close()
conn.close()
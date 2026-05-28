import psycopg2 

# Diagnostics Connectivity Channel Setup
conn = psycopg2.connect(
    dbname="news_db",
    user="user",
    password="password",
    host="localhost", 
    port="5433"        
)
cur = conn.cursor()

# Ingestion Volume Auditing Execution Loop
# Evaluates total raw record volumes stored inside our structural destination sink target table
cur.execute("SELECT COUNT(*) FROM news_sentiment;")
total = cur.fetchone()[0]

print(f"Total articles in database: {total}")

# Immediate Resource Deallocation
cur.close()
conn.close()
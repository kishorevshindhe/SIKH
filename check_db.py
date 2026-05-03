import sqlite3
conn = sqlite3.connect('sikh.db')
cursor = conn.cursor()
cursor.execute("SELECT id, username, email, password FROM users")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()
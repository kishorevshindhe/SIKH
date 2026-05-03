import sqlite3
from auth.auth import verify_password

# Get kishore's hash from DB
conn = sqlite3.connect('sikh.db')
cursor = conn.cursor()
cursor.execute("SELECT email, password FROM users WHERE email='kishore@test.com'")
row = cursor.fetchone()
conn.close()

print("Email:", row[0])
print("Hash:", row[1])
print("Password check:", verify_password("test123", row[1]))
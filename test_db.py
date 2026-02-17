#Use to check if db has been created correctly from sql_init.py
import sqlite3

conn = sqlite3.connect("hospital_management.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(table[0])

conn.close()

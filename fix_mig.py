import sqlite3
try:
    conn = sqlite3.connect('db.sqlite3')
    conn.execute("DELETE FROM django_migrations WHERE app='print3d' AND name LIKE '0002_%'")
    conn.commit()
    print("Fixed migrations.")
except Exception as e:
    print("Error:", e)

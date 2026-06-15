import sqlite3
p = r"C:\Users\Diwakar Chaudhary\OneDrive\Documents\Desktop\E-commerce\e_commerce\db.sqlite3"
print('DB path:', p)
conn = sqlite3.connect(p)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', sorted([r[0] for r in c.fetchall()]))
try:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='easy_kart_customuser'")
    print('easy_kart_customuser exists:', bool(c.fetchone()))
except Exception as e:
    print('error checking customuser:', e)
conn.close()

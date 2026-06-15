import sqlite3, pathlib
p = pathlib.Path(__file__).resolve().parent.parent / 'db.sqlite3'
print('DB:', p)
conn = sqlite3.connect(p)
c = conn.cursor()
try:
    c.execute("SELECT id, app, name FROM django_migrations ORDER BY id")
    rows = c.fetchall()
    if not rows:
        print('no rows')
    for r in rows:
        print(r)
except Exception as e:
    print('error:', e)
conn.close()

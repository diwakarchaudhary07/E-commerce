import sqlite3
p = r"C:\Users\Diwakar Chaudhary\OneDrive\Documents\Desktop\E-commerce\e_commerce\db.sqlite3"
print('DB path:', p)
conn = sqlite3.connect(p)
c = conn.cursor()
print('Dropping table easy_kart_profile if exists')
try:
    c.execute('DROP TABLE IF EXISTS easy_kart_profile')
    conn.commit()
    print('dropped easy_kart_profile (if it existed)')
except Exception as e:
    print('error dropping table:', e)
print('Removing easy_kart rows from django_migrations')
try:
    c.execute("DELETE FROM django_migrations WHERE app='easy_kart'")
    conn.commit()
    print('deleted migration records for easy_kart')
except Exception as e:
    print('error deleting migration records:', e)
conn.close()

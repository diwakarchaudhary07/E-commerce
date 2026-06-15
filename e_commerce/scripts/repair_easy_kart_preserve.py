"""
Safely repair the SQLite DB to add missing easy_kart tables and mark migrations applied,
without deleting existing data. Run this with the project's virtualenv active.

Usage:
  python scripts\repair_easy_kart_preserve.py

It will:
- create `easy_kart_customuser` and M2M tables if missing
- insert rows into `django_migrations` for easy_kart 0001_initial and 0002_profile if missing
- make a backup copy `db.sqlite3.preserve_bak` before changes

Note: Inspect the script before running. If you have a DB backup elsewhere, keep it.
"""
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(__file__).resolve().parent.parent / 'db.sqlite3'
BACKUP = DB.with_suffix('.sqlite3.preserve_bak')

print('DB path:', DB)
if not DB.exists():
    raise SystemExit('DB file not found: ' + str(DB))

# backup
shutil.copy2(DB, BACKUP)
print('Backup created at', BACKUP)

conn = sqlite3.connect(DB)
c = conn.cursor()

# helper
def table_exists(name):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return bool(c.fetchone())

# Create easy_kart_customuser if missing
if not table_exists('easy_kart_customuser'):
    print('Creating table easy_kart_customuser')
    c.execute('''
    CREATE TABLE easy_kart_customuser (
        id integer PRIMARY KEY AUTOINCREMENT,
        password varchar(128) NOT NULL,
        last_login datetime,
        is_superuser bool NOT NULL DEFAULT 0,
        username varchar(150) NOT NULL UNIQUE,
        first_name varchar(150) NOT NULL,
        last_name varchar(150) NOT NULL,
        is_staff bool NOT NULL DEFAULT 0,
        is_active bool NOT NULL DEFAULT 1,
        date_joined datetime NOT NULL,
        full_name varchar(255) NOT NULL,
        email varchar(254) NOT NULL UNIQUE,
        mobile_no varchar(15) NOT NULL,
        dob date,
        address text NOT NULL,
        alternate_mobile_no varchar(15),
        profile_image varchar(255),
        gender varchar(10)
    )
    ''')
    print('easy_kart_customuser created')
else:
    print('Table easy_kart_customuser already exists')

# create M2M tables if missing
if not table_exists('easy_kart_customuser_groups'):
    print('Creating M2M table easy_kart_customuser_groups')
    c.execute('''
    CREATE TABLE easy_kart_customuser_groups (
        id integer PRIMARY KEY AUTOINCREMENT,
        customuser_id integer NOT NULL,
        group_id integer NOT NULL
    )
    ''')
    # create index/unique constraint similar to Django
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS easy_kart_customuser_groups_customuser_id_group_id_uniq ON easy_kart_customuser_groups(customuser_id, group_id)')
    except Exception:
        pass
    print('M2M created')
else:
    print('M2M easy_kart_customuser_groups exists')

if not table_exists('easy_kart_customuser_user_permissions'):
    print('Creating M2M table easy_kart_customuser_user_permissions')
    c.execute('''
    CREATE TABLE easy_kart_customuser_user_permissions (
        id integer PRIMARY KEY AUTOINCREMENT,
        customuser_id integer NOT NULL,
        permission_id integer NOT NULL
    )
    ''')
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS easy_kart_customuser_user_permissions_customuser_id_permission_id_uniq ON easy_kart_customuser_user_permissions(customuser_id, permission_id)')
    except Exception:
        pass
    print('M2M created')
else:
    print('M2M easy_kart_customuser_user_permissions exists')

# ensure django_migrations table exists
if not table_exists('django_migrations'):
    raise SystemExit('django_migrations table not found; run `python manage.py migrate` on a temporary copy to initialize migrations table or restore backup.')

# insert migration rows if missing
def migration_row_exists(app, name):
    c.execute('SELECT 1 FROM django_migrations WHERE app=? AND name=?', (app, name))
    return bool(c.fetchone())

now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
if not migration_row_exists('easy_kart', '0001_initial'):
    print('Inserting django_migrations row for easy_kart 0001_initial')
    c.execute('INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)', ('easy_kart', '0001_initial', now))
else:
    print('django_migrations already contains easy_kart 0001_initial')

if not migration_row_exists('easy_kart', '0002_profile'):
    # if the migration file exists, mark it as not applied — we will let migrate handle it
    print('Leaving easy_kart 0002_profile unapplied (migrate will run it).')
else:
    print('django_migrations already contains easy_kart 0002_profile')

conn.commit()
conn.close()
print('Done. Now run: python manage.py migrate --fake-initial  OR python manage.py migrate')

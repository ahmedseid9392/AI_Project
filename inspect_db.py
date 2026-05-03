import sqlite3
import os
path = os.path.abspath('db.sqlite3')
print('DB path:', path)
conn = sqlite3.connect(path)
cur = conn.cursor()
print('Tables:')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(' ', row[0])
print('\nMigration rows:')
for row in cur.execute("SELECT app, name FROM django_migrations ORDER BY app, name"):
    print(' ', row[0], row[1])
conn.close()

import time
import sqlite3
import ast
import string
import binascii
from datetime import datetime

conn = sqlite3.connect('link_table.db')
c = conn.cursor()

# Create necessary tables if they do not exist
c.execute('''CREATE TABLE IF NOT EXISTS links ([key] STRING PRIMARY KEY NOT NULL, [id] STRING NOT NULL, [date] INTEGER NOT NULL, [url] STRING NOT NULL, [log] STRING NOT NULL)''')
conn.commit()

def clean_by_date(connection = conn, cursor = c, limit:int = 365*24*3600, commit:bool = True):
    cursor.execute(f'''DELETE FROM links WHERE date < strftime('%s', 'now')-({int(limit)})''')
    if commit: connection.commit()

def calc_id(key):
    val = binascii.crc32(key.encode('utf-8', errors='ignore'))

    # convert to base short code
    bases = string.digits + string.ascii_lowercase + string.ascii_uppercase
    num = ''
    while val > 0:
        num = f'{num}{bases[val % len(bases)]}'
        val //= len(bases)
    return num

def create_entry(key, url='', connection = conn, cursor = c):
    return create_custom_entry(key, calc_id(key), connection=connection, cursor=cursor)

def create_custom_entry(key, id, url='', connection = conn, cursor = c):
    if not id: id = calc_id(key)

    cursor.execute('SELECT * FROM links WHERE id=(?) LIMIT 1', (id,))
    finds = cursor.fetchall()
    if len(finds) > 0 and finds[0][0] != key: return False

    cursor.execute('''REPLACE INTO links VALUES (?, ?, strftime('%s', 'now'), ?, ?)''', (
        key, id, url, '[]'
    ))
    connection.commit()
    cursor.execute('''SELECT * from links''')
    print(cursor.fetchall())
    return True

def get_all(id, connection = conn, cursor = c):
    cursor.execute('SELECT * FROM links WHERE id=(?) LIMIT 1', (id,))
    rows = cursor.fetchall()
    if len(rows) > 0:
        return (str(rows[0][0]), str(rows[0][1]), datetime.utcfromtimestamp(rows[0][2]), rows[0][3], ast.literal_eval(rows[0][4]))
    else:
        return None

def push(key, url='', connection = conn, cursor = c):
    pass

def add_track(id, track, connection = conn, cursor = c):
    cursor.execute('UPDATE links SET log=SUBSTR(log, 0, LENGTH(log)) || IIF(LENGTH(log) > 2, \',\', \'\') || (?) || \']\' WHERE id=(?)', (repr(track), id))
    connection.commit()

if __name__ == "__main__":
    key = 'sickpass'
    create_entry(key)
    print(get_all(calc_id(key)))
    add_track(calc_id(key), {'argh': 1})
    add_track(calc_id(key), {'argh': 2})
    add_track(calc_id(key), {'argh': 3})
    print(get_all(calc_id(key)))
    clean_by_date(limit=-1)
    print(get_all(calc_id(key)))
import link_table
import sqlite3
import time, threading, os, re
import datetime
from geolite2 import geolite2
from flask import Flask, request, abort, g, render_template, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from waitress import serve
app = Flask(__name__)

DATABASE = 'link_table.db'
CLEAN_INTERVAL = 60
CLEAN_TIMEALIVE = 6*30*24*3600 # 6mo
LEAD_TIMEALIVE = 10
BLOCKED_IDS = ('create', 'info', 'static')

# Create a default testing shorturl that leads to google
created = link_table.create_custom_entry('google', 'google', url='http://google.com')

# Close current db connection
link_table.c.close()
link_table.conn.close()

# Stores all active requests
# information may be added but will be commited to the DB every LEAD_TIMEALIVE seconds
# each entry should be a dictionary with 'timestamp' -> float, 'id' -> str (tracking id, NOT lid), 'info': dict() (the tracking info)
# Indexed by LID, or lead id
leads_alive = dict()

# Ran in a seperate thread by the apscheduler
# Quick, thread-safe open-close db when needed
def clean(): 
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    link_table.clean_by_date(limit=CLEAN_TIMEALIVE, connection=conn, cursor=c)
    c.close()
    conn.close()

# Ran in a seperate thread by the apscheduler
# Resolves all 'cold' leads
def resolve_active():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    now = time.time()
    toDelete = list()
    for lid, lead in leads_alive.items():
        if now > lead['timestamp'] + LEAD_TIMEALIVE:
            link_table.add_track(lead['id'], lead['info'], connection=conn, cursor=c) # commit it
            toDelete.append(lid) # delete it
            print('Lead Added')
    for d in toDelete: del leads_alive[d]
    conn.commit()

    c.close()
    conn.close()

# Gets the db for flask app context. Quick connections
def get_db(): 
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Closes the quick connection
@app.teardown_appcontext 
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Homepage
@app.route('/')
def home():
    return render_template('index.html')

# Get info for an existing tracking link
# You must know the ID and the key, username and password stand-ins
@app.route('/info/<id>', methods=['GET'])
def info(id):
    if not id or len(id) == 0: return abort(400, 'No ID given')
    
    conn = get_db()
    c = conn.cursor()
    info = link_table.get_all(id, connection=conn, cursor=c)
    if not info: return abort(404, 'ShortLink not created')
    
    key = request.args.get('key', '', type=str)

    parsed = {
        'id': info[1],
        'created': info[2].timestamp(),
        'expires': info[2].timestamp()+CLEAN_TIMEALIVE
    }
    if info[3]: parsed['url'] = info[3]
    if info[0] == key: parsed['log'] = sorted(info[4], key=lambda x: x['time'])
    return parsed

# Create new tracking links
@app.route('/create', methods=['POST', 'PATCH'])
def post():
    if not request.json: return abort(400, 'No json in request body')
    
    # get and check key
    if 'key' not in request.json: return abort(400, 'No key in request json')
    key = request.json['key']
    if len(key) < 3: return abort(400, 'Key must have 3 or more letters')

    # get and check id
    id = request.json['id'] if 'id' in request.json else link_table.calc_id(key)
    id = re.sub(r'''[^[:word:].,!+()\[\]<>{}\|~"':;*$%]''', '', str(id))

    # get url without checks
    url = request.json['url'] if 'url' in request.json else ''

    # make sure ID is never an endpoint, which could be confusing
    if str(id).lower() in repr(BLOCKED_IDS).lower():
        id = link_table.calc_id(key)
        if str(id).lower() in repr(BLOCKED_IDS).lower(): id = f'_{id}_'
    
    # Actually try to create it
    conn = get_db()
    c = conn.cursor()
    created = link_table.create_custom_entry(key, id, url=url, connection=conn, cursor=c)
    if created: return {'status': 'OK', 'message': 'Shortlink created', 'id': id}
    else: abort(403, 'ShortLink already exists and key is incorrect')

# Send redirect HTML file
@app.route('/<id>', methods=['GET'])
def ping_redirect(id):
    conn = get_db()
    c = conn.cursor()

    info = link_table.get_all(id, connection=conn, cursor=c)
    
    # Save current tracking information with a new lead id
    # This should be updated in pong_redirect, but if it isn't, it's better to have some info than none
    # This happens when the user does not have javascript enabled or something else blocks our tracking post
    lid = save_lead(id, request_fingerprint())

    if info:
        if info[3]: return render_template('redirect.html', url=info[3], lid=lid)
        elif info[2]: return abort(404, 'ShortLink created but no redirect set')
    else:
        return abort(404, 'ShortLink not created or no longer valid')

# Listen for a post from the redirect.html
@app.route('/<id>', methods=['POST'])
def pong_redirect(id):
    # If there is a leadID, update the information for that one
    lid = request.json['lid'] if 'lid' in request.json else None
    track = request_fingerprint()

    # Filter out request json and add selected elements to track
    # Important note: lid is not in here but in request.json
    for k in ('locality', 'os', 'screen', 'time_zone', 'fonts', 'plugins', 'mimetypes', 'screen_avail', 'build_id', 'dnt', 'fire_gloves', 'window_hash', 'file_requested'):
        if k in request.json and 0 < len(repr(request.json[k])) < 2000: # cap each json response at 2k chars. That should be enough and slows down spam
            track[k] = request.json[k]
    
    # Save the lead to the queue
    # Note that if there is no leadID, we will count this user twice
    save_lead(id, track, lid=lid)
    
    return {'status': 1, 'message': 'OK'}

# Just serve a file
# You get much less tracking info :(
@app.route('/<id>/<name>.<ext>', methods=['GET'])
def serve_file(name, ext):
    conn = get_db()
    c = conn.cursor()

    info = link_table.get_all(id, connection=conn, cursor=c)
    if not info: return abort(404, 'ShortLink not created or no longer valid')

    # We don't expect a pong, so save the raw request fingerprint
    link_table.add_track(id, request_fingerprint(), connection=conn, cursor=c)

    if os.path.exists(f'./files/{name}.{ext}'):
        return send_file(f'./files/{name}.{ext}')
    return abort(404, 'File not found')

# Gets a fingerprint using only the request's context
def request_fingerprint():
    print('Lead found')

    # Get basic tracking info
    track = {
        'time': datetime.datetime.utcnow().timestamp(),
        'user_agent': request.user_agent.string,
        'headers': dict(request.headers),
        'ip': request.environ['REMOTE_ADDR']
    }

    # GEOIP the IP
    if request.environ['REMOTE_ADDR']:
        reader = geolite2.reader()
        match = reader.get(str(request.environ['REMOTE_ADDR']))
        if match:
            if match['country'] and match['country']['iso_code']:   track['country'] = match['country']['iso_code']
            if match['location']:
                track['location'] = dict()
                if match['location']['latitude']:                   track['location']['latitude'] = match['location']['latitude']
                if match['location']['longitude']:                  track['location']['longitude'] = match['location']['longitude']
                if match['location']['accuracy_radius']:            track['location']['accuracy'] = match['location']['accuracy_radius']
                if match['location']['time_zone']:                  track['timezone'] = match['location']['time_zone']
    return track

# Queues a lead for saving
# Will update a lead if lid is set to a valid lead
def save_lead(id, json, lid=None):
    # If not given a lead id, generate it
    if not lid or not isinstance(lid, int):
        lid = (time.time_ns() % 1000) * 100 
        while lid in leads_alive: lid += 1
    
    # If lead exists already, add to it, overwriting existing fields
    elif lid in leads_alive:
        json.update(leads_alive[lid]['info'])

    # Add track to lid tracks
    leads_alive[lid] = {
        'timestamp': time.time(),
        'id': id,
        'info': json
    }

    return lid

if __name__ == "__main__":
    apsched = BackgroundScheduler()
    apsched.start()
    apsched.add_job(clean, 'interval', seconds=CLEAN_INTERVAL)
    apsched.add_job(resolve_active, 'interval', seconds=LEAD_TIMEALIVE)

    serve(app,host='0.0.0.0',port=8080)
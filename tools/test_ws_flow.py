import requests
import sqlite3
import time
import asyncio
import websockets

BASE='http://127.0.0.1:7860'
USERNAME='test_auditor'
PASSWORD='Password123!'

# 1. register (may fail if exists)
print('registering...')
res = requests.post(BASE+'/api/auth/register', json={'username': USERNAME, 'password': PASSWORD})
if res.status_code==200:
    print('registered')
else:
    print('register response', res.status_code, res.text)

# 2. promote to auditor directly in sqlite DB
dbfile='aigi_holmes.db'
print('updating role in DB...')
conn = sqlite3.connect(dbfile)
cur = conn.cursor()
cur.execute("UPDATE users SET role='auditor' WHERE username=?", (USERNAME,))
conn.commit()
print('rows affected', cur.rowcount)
conn.close()

# 3. login
print('logging in...')
res = requests.post(BASE+'/api/auth/login', json={'username': USERNAME, 'password': PASSWORD})
print('login status', res.status_code, res.text)
if res.status_code!=200:
    raise SystemExit('login failed')
token = res.json().get('access_token')
print('token len', len(token) if token else 'None')

# 4. create job
print('creating job...')
res = requests.post(BASE+'/api/detect-batch-init', headers={'Authorization': 'Bearer '+token})
print('init status', res.status_code, res.text)
if res.status_code!=200:
    raise SystemExit('init failed')
job_id = res.json().get('job_id')
print('job_id', job_id)

# 5. test websocket connection
async def ws_test():
    proto='ws'
    uri=f"{proto}://127.0.0.1:7860/ws/detect/{job_id}?token={token}"
    print('connecting to', uri)
    try:
        async with websockets.connect(uri) as ws:
            print('ws open')
            # wait for a short time for messages
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                print('recv:', msg)
            except asyncio.TimeoutError:
                print('no message in 5s')
    except Exception as e:
        print('ws error:', type(e), e)

asyncio.run(ws_test())

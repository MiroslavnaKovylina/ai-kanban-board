import urllib.request
import json
import sys
import time

BASE = 'http://localhost:8000'


def fetch(url, retries=5, delay=1):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                status = r.getcode()
                body = r.read().decode('utf-8', errors='replace')
                return status, body
        except Exception as e:
            last = e
            time.sleep(delay)
    raise last


errors = []

# Check API ping
try:
    status, body = fetch(BASE + '/api/ping')
    print('GET /api/ping ->', status)
    data = json.loads(body)
    if not (isinstance(data, dict) and data.get('success') is True and data.get('message') == 'pong'):
        errors.append('/api/ping returned unexpected payload: ' + repr(data))
except Exception as e:
    errors.append('/api/ping failed: ' + str(e))

# Check root
try:
    status, body = fetch(BASE + '/')
    print('GET / ->', status, 'len=', len(body))
    if status != 200:
        errors.append('/ returned status ' + str(status))
    if '<!DOCTYPE html>' not in body and '<html' not in body:
        errors.append('/ returned non-HTML content')
except Exception as e:
    errors.append('/ failed: ' + str(e))

if errors:
    print('FAILURES:')
    for e in errors:
        print('-', e)
    sys.exit(1)

print('Integration tests passed')
sys.exit(0)

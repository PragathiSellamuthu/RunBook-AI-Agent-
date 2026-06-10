import time
import urllib.request
import json

time.sleep(5)

r = urllib.request.urlopen('http://127.0.0.1:8000/api/agent/feed')
feed = json.loads(r.read())

print(f"=== AGENT FEED ({len(feed)} entries) ===")
for e in feed:
    msg = e['message'].encode('ascii', 'ignore').decode()[:80]
    print(f"[{e['timestamp']}] [{e['status']}] {msg}")

r2 = urllib.request.urlopen('http://127.0.0.1:8000/api/status')
status = json.loads(r2.read())
print(f"\n=== SERVER STATUS ===")
print(json.dumps(status, indent=2))

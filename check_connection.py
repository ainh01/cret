"""Probe the endpoint once; report connectivity without exposing secrets."""
import time
import urllib.error
import urllib.request
from pathlib import Path

values = dict(line.strip().split('=', 1) for line in Path('.env').read_text().splitlines()
              if '=' in line and not line.lstrip().startswith('#'))
url = values['ENDPOINT'].strip().strip('\"\'')
for label, proxies in [('direct', {}), ('proxy', {'http': 'http://127.0.0.1:3128', 'https': 'http://127.0.0.1:3128'})]:
    start = time.monotonic()
    try:
        response = urllib.request.build_opener(urllib.request.ProxyHandler(proxies)).open(
            urllib.request.Request(url, method='HEAD'), timeout=8)
        print(label, 'reachable:', response.status, round(time.monotonic() - start, 2), 'seconds')
        break
    except urllib.error.HTTPError as exc:
        print(label, 'reachable: HTTP', exc.code, round(time.monotonic() - start, 2), 'seconds')
        break
    except Exception as exc:
        print(label, 'failed:', type(exc).__name__, round(time.monotonic() - start, 2), 'seconds')
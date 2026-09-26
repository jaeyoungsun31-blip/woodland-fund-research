from pathlib import Path
import json, time, shutil
import pandas as pd
import requests

root = Path.home() / 'Downloads' / 'Woodland-EODHD'
root.mkdir(exist_ok=True)
key = Path('/tmp/woodland-eodhd-key').read_text().strip()
if not key:
    raise SystemExit('Saved API key is empty.')
session = requests.Session()

def fetch(endpoint, params=None):
    for attempt in range(4):
        time.sleep(0.2)
        try:
            response = session.get('https://eodhd.com/api/' + endpoint,
                params={**(params or {}), 'api_token': key, 'fmt': 'json'},
                timeout=45, allow_redirects=False)
        except requests.RequestException:
            if attempt == 3:
                raise RuntimeError('Network request failed; rerun to resume.') from None
            time.sleep(2 ** attempt)
            continue
        if response.status_code in (401, 403, 429):
            raise RuntimeError(f'HTTP {response.status_code}: stopped; check access or quota.')
        if response.status_code >= 500 and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        if response.status_code != 200:
            raise RuntimeError(f'HTTP {response.status_code}: stopped; rerun to resume.')
        try:
            return response.json()
        except ValueError:
            raise RuntimeError('Unexpected response format; stopped.') from None

try:
    symbols = set()
    for label, flag in [('active', 0), ('delisted', 1)]:
        path = root / (label + '-symbols.json')
        if path.exists():
            rows = json.loads(path.read_text())
        else:
            rows = fetch('exchange-symbol-list/US', {'delisted': flag, 'type': 'common_stock'})
            if not isinstance(rows, list):
                raise RuntimeError('Unexpected symbol list.')
            path.write_text(json.dumps(rows))
        for row in rows:
            code = row.get('Code', '')
            if code and all(c.isalnum() or c in '.-_' for c in code):
                symbols.add(code)
    print(f'{len(symbols):,} unique stock symbols. Saving to {root}', flush=True)
    for i, code in enumerate(sorted(symbols), 1):
        target = root / (code + '.US.parquet')
        empty = root / (code + '.US.empty.json')
        if target.exists() or empty.exists():
            continue
        if shutil.disk_usage(root).free < 10_000_000_000:
            raise RuntimeError('Stopped to preserve 10 GB of free disk space.')
        rows = fetch('eod/' + code + '.US', {'period': 'd'})
        if not isinstance(rows, list):
            raise RuntimeError('Unexpected price response for ' + code)
        if not rows:
            empty.write_text('{"status":"empty_response_not_verified_missing"}')
            print(f'{i}/{len(symbols)} {code}: empty response', flush=True)
            continue
        frame = pd.DataFrame(rows)
        if not {'date','close','adjusted_close','volume'}.issubset(frame.columns):
            raise RuntimeError('Unexpected price columns for ' + code)
        temp = target.with_suffix('.partial')
        frame.to_parquet(temp, index=False)
        temp.replace(target)
        print(f'{i}/{len(symbols)} {code}: {len(frame):,} daily records', flush=True)
    print('Download finished. These are raw vendor files awaiting data-quality validation.')
except (RuntimeError, KeyboardInterrupt) as error:
    print(str(error) if isinstance(error, RuntimeError) else 'Interrupted. Rerun to resume.')

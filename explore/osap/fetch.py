"""Download the Open Source Asset Pricing files used by the anomaly triage.

Public Google Drive files from the October 2025 release (v2.0.0),
https://www.openassetpricing.com/data/. No credentials. Files land in the
gitignored raw/ directory; URLs, sizes and sha256 go to sources.json.
"""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
MANIFEST = ROOT / "sources.json"
RELEASE = "https://drive.google.com/drive/folders/1qQDuTsnyvWfEJR6nPBQZ8xxlq6bkLG_y"
# Both Drive copies of SignalDoc.csv (release root 1rdi0jTPSA6xtn6TpQAMT5WyEczQ1gK59
# and the data page's 1Sev9s6cPFUGgxp1pFiej0lGzpsMqJCI2) returned Drive "Quota
# exceeded" on 2026-09-26, so the documentation comes from the v2.0.0 code tag
# that produced this data release.
DIRECT = {
    "SignalDoc.csv": "https://raw.githubusercontent.com/OpenSourceAP/CrossSection/v2.0.0/SignalDoc.csv",
}
FILES = {
    # Portfolios / Full Sets OP / PredictorLSretWide.csv
    "PredictorLSretWide.csv": "10sOryk_ddjkXagaajTKUk1nwJs2ZLRiI",
    # Portfolios / Full Sets Alt / PredictorAltPorts_LiqScreen_VWforce.zip
    "PredictorAltPorts_LiqScreen_VWforce.zip": "1KZE3FgBxFPaNOyxoRw63ubZHOlkR9kZW",
}


def url_for(file_id):
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


def download(name, file_id=None, url=None):
    url = url or url_for(file_id)
    path = RAW / name
    if not path.exists():
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=600) as response:
            body = response.read()
        if body[:15].lower().startswith((b"<!doctype html", b"<html")):
            raise RuntimeError(f"{name}: Drive returned an HTML page, not the file")
        path.write_bytes(body)
    data = path.read_bytes()
    return {
        "file": f"raw/{name}",
        "drive_id": file_id,
        "view_url": f"https://drive.google.com/file/d/{file_id}/view" if file_id else url,
        "download_url": url,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main():
    RAW.mkdir(exist_ok=True)
    t0 = time.time()
    entries = [download(name, url=url) for name, url in DIRECT.items()]
    entries += [download(name, file_id) for name, file_id in FILES.items()]
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    notes = {f["file"]: f for f in previous.get("files", [])}
    for entry in entries:
        if "acquisition" in notes.get(entry["file"], {}):
            entry["acquisition"] = notes[entry["file"]]["acquisition"]
    entries += [f for f in previous.get("files", []) if "extracted_from" in f]
    manifest = {
        "release": "Open Source Asset Pricing, October 2025 release (v2.0.0)",
        "data_page": "https://www.openassetpricing.com/data/",
        "release_folder": RELEASE,
        "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0, 1),
        "files": entries,
    }
    if "retrieved_utc_note" in previous:
        manifest["retrieved_utc_note"] = previous["retrieved_utc_note"]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

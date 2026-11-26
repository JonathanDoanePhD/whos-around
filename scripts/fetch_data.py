"""Download a project's raw data from its data/sources.csv.

Usage (from the repo root):
    python3 -I scripts/fetch_data.py .
    python3 -I scripts/fetch_data.py . --force   # re-download all

sources.csv columns:
    file      path under data/raw/ to save to
    url       direct download link (no login)
    source    human-readable source name
    license   license / terms note
    unzip     "yes" to extract a .zip next to it (optional)

Every download is recorded in data/sources.lock.csv (date, bytes, sha256). Commit that
file: it shows exactly which version of each source the outputs were built from, and a
changed hash on re-download tells you the publisher updated the file.
"""
import csv
import datetime as dt
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    project = Path(sys.argv[1]).resolve()
    force = "--force" in sys.argv
    sources = project / "data" / "sources.csv"
    raw = project / "data" / "raw"
    lock_path = project / "data" / "sources.lock.csv"
    raw.mkdir(parents=True, exist_ok=True)

    lock = {}
    if lock_path.exists():
        with open(lock_path, newline="") as f:
            lock = {r["file"]: r for r in csv.DictReader(f)}

    with open(sources, newline="") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        dest = raw / r["file"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not force:
            print(f"skip  {r['file']} (exists)")
            if r["file"] not in lock:  # placed by hand: record it so the lock is complete
                lock[r["file"]] = {
                    "file": r["file"], "url": r["url"],
                    "downloaded_utc": dt.datetime.fromtimestamp(
                        dest.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d"),
                    "bytes": dest.stat().st_size, "sha256": sha256(dest),
                }
            continue
        print(f"get   {r['file']} <- {r['url']}")
        req = urllib.request.Request(r["url"], headers={"User-Agent": "research-data-fetch/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
        digest = sha256(dest)
        old = lock.get(r["file"], {}).get("sha256")
        if old and old != digest:
            print(f"      NOTE: {r['file']} changed since last lock ({old[:12]} -> {digest[:12]})")
        lock[r["file"]] = {
            "file": r["file"],
            "url": r["url"],
            "downloaded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            "bytes": dest.stat().st_size,
            "sha256": digest,
        }
        if r.get("unzip", "").strip().lower() == "yes":
            with zipfile.ZipFile(dest) as z:
                for m in z.namelist():  # refuse paths that escape the folder
                    if Path(m).is_absolute() or ".." in Path(m).parts:
                        sys.exit(f"unsafe path in zip: {m}")
                z.extractall(dest.parent)

    with open(lock_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "downloaded_utc", "bytes", "sha256"])
        w.writeheader()
        for k in sorted(lock):
            w.writerow(lock[k])
    print(f"wrote {lock_path.relative_to(project.parent.parent)}")


if __name__ == "__main__":
    main()

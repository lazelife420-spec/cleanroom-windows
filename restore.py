#!/usr/bin/env python3
import argparse
import json
import os
import shutil
from datetime import datetime

try:
    from send2trash import send2trash
except Exception:
    send2trash = None


def load_log(path):
    # open with utf-8-sig to gracefully handle files starting with a BOM
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    # Some runs append human-readable summaries after the JSON object; parse the first JSON value
    decoder = json.JSONDecoder()
    try:
        obj, idx = decoder.raw_decode(content)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON log: {e}")
    data = obj
    # Expecting either a list of dicts or a dict with "actions" or "candidates"
    if isinstance(data, dict) and "actions" in data:
        return data["actions"]
    if isinstance(data, dict) and "candidates" in data:
        # main.py writes {count,total_bytes,candidates}
        return data["candidates"]
    if isinstance(data, list):
        return data
    raise ValueError("Unrecognized log format: expected list or {actions: [...]} or {candidates: [...]}")


def entries_from_log(actions):
    # Yield tuples (src, dest, timestamp, entry)
    for e in actions:
        # Try common key names
        src = e.get("src") or e.get("src_path") or e.get("source") or e.get("original")
        dest = e.get("dest") or e.get("dest_path") or e.get("target") or e.get("archive") or e.get("archived_path")
        ts = e.get("timestamp") or e.get("time") or e.get("when")
        if src and dest:
            yield src, dest, ts, e


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def unique_path(path):
    base, ext = os.path.splitext(path)
    t = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base}.restoreconflict.{t}{ext}"


def restore_one(src, dest, apply=False, use_trash=False):
    # dest is where file currently is (in archive); src is original location to restore to
    if not os.path.exists(dest):
        return (False, f"missing archived file: {dest}")
    if os.path.exists(src):
        # avoid overwriting
        new_src = unique_path(src)
        if apply:
            try:
                shutil.move(src, new_src)
            except Exception as e:
                return (False, f"failed to move existing src to {new_src}: {e}")
        else:
            return (False, f"would rename existing target {src} -> {new_src}")
    ensure_parent(src)
    if apply:
        try:
            shutil.move(dest, src)
            return (True, f"moved {dest} -> {src}")
        except Exception as e:
            return (False, f"error moving {dest} -> {src}: {e}")
    else:
        return (True, f"would move {dest} -> {src}")


def main():
    p = argparse.ArgumentParser(description="Restore files from a smart-clean JSON log.")
    p.add_argument("--log", "-l", default="cleanup_log.json", help="Path to JSON log file (default: cleanup_log.json)")
    p.add_argument("--apply", action="store_true", help="Perform the restore moves (default is dry-run)")
    p.add_argument("--filter", help="Only restore entries containing this substring in the original path")
    p.add_argument("--limit", type=int, help="Only process this many entries (for testing)")
    p.add_argument("--trash", action="store_true", help="If set, files removed during conflict resolution will be sent to Recycle Bin instead of permanent delete (requires send2trash)")
    p.add_argument("--quiet", action="store_true", help="Only print summary lines")
    args = p.parse_args()

    if args.trash and send2trash is None:
        print("send2trash not available; install it or omit --trash")
        return

    actions = load_log(args.log)
    ents = list(entries_from_log(actions))
    if args.filter:
        ents = [e for e in ents if args.filter in e[0]]
    if args.limit:
        ents = ents[: args.limit]

    results = []
    for src, dest, ts, entry in ents:
        ok, msg = restore_one(src, dest, apply=args.apply, use_trash=args.trash)
        results.append({"src": src, "dest": dest, "ok": ok, "msg": msg, "timestamp": ts})
        if not args.quiet:
            print(("OK:" if ok else "FAIL:"), msg)

    moved = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    print("\nSummary:")
    print(f"  Candidates processed: {len(results)}")
    print(f"  Successful (or would-be): {len(moved)}")
    print(f"  Failed/skipped: {len(failed)}")

    if args.apply:
        # Optionally append a restore record to the log
            try:
                now = datetime.now().isoformat()
                restore_entries = [{"action": "restore", "src": r["src"], "dest": r["dest"], "ok": r["ok"], "msg": r["msg"], "time": now} for r in results]
                # read-modify-write using utf-8-sig as well
                with open(args.log, "r+", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        data.extend(restore_entries)
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
                    elif isinstance(data, dict) and "actions" in data:
                        data["actions"].extend(restore_entries)
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
            except Exception:
                pass


if __name__ == "__main__":
    main()

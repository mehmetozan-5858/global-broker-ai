import hashlib, json
from pathlib import Path

STATE=Path("data/seen.json")

def key(source, source_id, title):
    raw=f"{source}|{source_id}|{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()

def only_new(rows):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    seen=set(json.loads(STATE.read_text()) if STATE.exists() else [])
    fresh=[]
    for row in rows:
        k=key(row.get("source",""),row.get("source_id",""),row.get("title",""))
        if k not in seen:
            fresh.append(row); seen.add(k)
    STATE.write_text(json.dumps(sorted(seen),indent=2))
    return fresh

#!/usr/bin/env python3
"""Port knowledge base: validate knowledge/ and build the agent API into dist/.

Usage: python3 atlas.py validate          # JSON errors on stdout, exit 1 if any
       python3 atlas.py build             # validate, then write dist/api/*, dist/llms.txt
       python3 atlas.py titles [--refresh] # rebuild data/titles.json from blawar/titledb

See SPEC.md. Needs PyYAML.
"""
import json, re, sys, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
KB, DIST = HERE / "knowledge", HERE / "dist"
TITLES = HERE / "data/titles.json"
SPEC_VERSION = "0.1"
SITE = "https://catoncat.github.io/d2r-port-radar"

STAGES = ["none", "analysed", "rewritten", "boots", "first-frame", "title-screen",
          "in-game", "playable", "complete"]
ENUMS = {
    ("finding", "kind"): {"blocker", "pitfall", "technique", "fact"},
    ("finding", "status"): {"inferred", "verified", "replicated", "contradicted", "superseded"},
    ("component", "kind"): {"hle", "nvn", "middleware", "engine", "host", "platform"},
}
REQUIRED = {
    "game": ["id", "name", "summary", "builds", "status"],
    "component": ["id", "name", "summary", "kind"],
    "finding": ["id", "title", "summary", "kind", "components", "status", "evidence", "updated", "by"],
}
TITLE_ID = re.compile(r"^01[0-9A-F]{14}$")

# Content boundary (SPEC §3). Patterns are deliberately blunt; a false positive costs a rewording.
GUARDS = [
    (re.compile(r"\b[0-9a-fA-F]{48,}\b"), "long hex run (looks like raw bytes or a key)"),
    (re.compile(r"(?:[0-9a-fA-F]{2}[ ,]){24,}"), "byte dump"),
    (re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"), "base64 blob"),
    (re.compile(r"(?im)^\s*(header_key|key_area_key|titlekek|master_key|package\d?_key)\w*\s*="), "key material"),
    (re.compile(r"(?i)\b(nsw2u|nswdl|ziperto|nxbrew|switchrom|romsfun|nsp-?xci)\.\w+"), "link to a piracy site"),
    (re.compile(r"(?i)\.(nsp|xci|nsz|ipa|apk)\b.*https?://|https?://\S+\.(nsp|xci|nsz|ipa|apk)\b"), "link to an installer"),
]
MAX_FILE = 200_000


def err(errors, f, field, error, hint=""):
    errors.append({"file": str(f.relative_to(HERE)), "field": field, "error": error, "hint": hint})


def parse(f):
    text = f.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2).strip()


def load(errors):
    objs = {"game": {}, "component": {}, "finding": {}}
    dirs = {"game": "games", "component": "components", "finding": "findings"}
    for kind, d in dirs.items():
        for f in sorted((KB / d).glob("*")):
            if f.suffix != ".md":
                err(errors, f, "-", "only .md files are allowed here", "binary or data files are never accepted (SPEC §3)")
                continue
            if f.stat().st_size > MAX_FILE:
                err(errors, f, "-", f"file larger than {MAX_FILE} bytes", "split it, or link to code instead of pasting it")
            raw = f.read_text(encoding="utf-8", errors="replace")
            for pat, why in GUARDS:
                hit = pat.search(raw)
                if hit:
                    line = raw[:hit.start()].count("\n") + 1
                    err(errors, f, f"line {line}", f"content boundary: {why}", "describe it in words, cite an address, or link to code (SPEC §3)")
            try:
                meta, body = parse(f)
            except yaml.YAMLError as e:
                err(errors, f, "front matter", f"YAML error: {e}".splitlines()[0])
                continue
            if meta is None:
                err(errors, f, "front matter", "missing --- YAML front matter ---", "copy a file from templates/")
                continue
            for k in REQUIRED[kind]:
                if meta.get(k) in (None, "", []):
                    err(errors, f, k, "required field missing")
            for (k2, field), allowed in ENUMS.items():
                if k2 == kind and meta.get(field) is not None and meta[field] not in allowed:
                    err(errors, f, field, f"'{meta[field]}' is not one of {sorted(allowed)}")
            if len(str(meta.get("summary", ""))) > 200:
                err(errors, f, "summary", "longer than 200 characters", "put the detail in the body")
            if meta.get("id") and f.stem != str(meta["id"]):
                err(errors, f, "id", f"id '{meta['id']}' does not match file name '{f.stem}'")
            meta["_body"], meta["_file"] = body, f
            objs[kind][str(meta.get("id", f.stem))] = meta
    return objs


def check_refs(objs, errors):
    comps, games, finds = objs["component"], objs["game"], objs["finding"]
    for g in games.values():
        if not TITLE_ID.match(str(g["id"])):
            err(errors, g["_file"], "id", "not a base-game titleId (01 + 14 hex, uppercase)")
        for c in (g.get("middleware") or []) + (g.get("uses") or []):
            if c not in comps:
                err(errors, g["_file"], "uses", f"unknown component '{c}'", "add knowledge/components/<id>.md")
        for s in g.get("status") or []:
            if s.get("stage") not in STAGES:
                err(errors, g["_file"], "status.stage", f"'{s.get('stage')}' is not one of {STAGES}")
            if not s.get("evidence"):
                err(errors, g["_file"], "status.evidence", "every status entry needs evidence")
    for x in finds.values():
        f = x["_file"]
        for c in x.get("components") or []:
            if c not in comps:
                err(errors, f, "components", f"unknown component '{c}'", "add knowledge/components/<id>.md")
        for t in x.get("games") or []:
            if t not in games:
                err(errors, f, "games", f"unknown game '{t}'", "add knowledge/games/<titleId>.md")
        for r in x.get("related") or []:
            if r not in finds:
                err(errors, f, "related", f"unknown finding '{r}'")
        if x.get("games") and not x.get("builds"):
            err(errors, f, "builds", "game-specific finding without builds", "addresses are only meaningful for a build")
        for e in x.get("evidence") or []:
            if e.get("type") not in {"disasm", "runtime", "source", "config", "report"} or not e.get("ref"):
                err(errors, f, "evidence", f"bad entry {e}", "need {type: disasm|runtime|source|config|report, ref: ...}")
        fix = x.get("fix") or {}
        if fix and fix.get("state") not in {"open", "done", "wontfix"}:
            err(errors, f, "fix.state", "must be open / done / wontfix")
        if fix.get("state") == "done" and not fix.get("where"):
            err(errors, f, "fix.where", "a done fix must say where the code is")
        if x.get("status") == "inferred" and not x.get("reproduce"):
            err(errors, f, "reproduce", "an inferred finding needs a way to check it")


def validate():
    errors = []
    objs = load(errors)
    check_refs(objs, errors)
    return objs, errors


# ---------------- build ----------------

def clean(o):
    return {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in o.items() if not k.startswith("_")}


def brief(o, kind):
    return {"type": kind, "id": str(o["id"]), "title": o.get("title") or o.get("name"), "summary": o["summary"]}


def write(path, data):
    p = DIST / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str))


def est_tokens(obj):
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return round(len(s.encode()) / 3.2)  # rough: mixed CJK / code


def build(objs):
    games, comps, finds = objs["game"], objs["component"], objs["finding"]
    by_comp, by_game = {c: [] for c in comps}, {g: [] for g in games}
    for x in finds.values():
        for c in x.get("components") or []:
            by_comp[c].append(x)
        for g in x.get("games") or []:
            by_game[g].append(x)
    comp_games = {c: [] for c in comps}
    for g in games.values():
        for c in set((g.get("middleware") or []) + (g.get("uses") or [])):
            comp_games[c].append(str(g["id"]))
    for c, xs in by_comp.items():
        for x in xs:
            for g in x.get("games") or []:
                if g not in comp_games[c]:
                    comp_games[c].append(g)

    def task_of(x):
        fx = x.get("fix") or {}
        return {"id": x["id"], "title": x["title"], "summary": x["summary"], "kind": x["kind"],
                "needs": x.get("needs") or ["generic"], "size": fx.get("size"), "games": x.get("games") or [],
                "components": x["components"], "bundle": f"api/task/{x['id']}.json"}

    tasks = [task_of(x) for x in finds.values() if (x.get("fix") or {}).get("state") == "open"]
    tasks.sort(key=lambda t: (t["needs"] != ["generic"], "SMLX".find((t["size"] or "M")[0])))

    for x in finds.values():
        write(f"api/findings/{x['id']}.json", {**clean(x), "body": x["_body"]})
    for c in comps.values():
        write(f"api/components/{c['id']}.json", {**clean(c), "body": c["_body"], "games": comp_games[c["id"]],
                                                 "findings": [brief(x, "finding") | {"status": x["status"], "kind": x["kind"]} for x in by_comp[c["id"]]]})
    for g in games.values():
        gid = str(g["id"])
        cids = sorted(set((g.get("middleware") or []) + (g.get("uses") or []) + [c for x in by_game[gid] for c in x["components"]]))
        write(f"api/games/{gid}.json", {**clean(g), "body": g["_body"],
                                        "components": [brief(comps[c], "component") for c in cids],
                                        "findings": [brief(x, "finding") | {"status": x["status"], "kind": x["kind"],
                                                                            "fix": (x.get("fix") or {}).get("state")} for x in by_game[gid]],
                                        "open_tasks": [t["id"] for t in tasks if gid in t["games"]]})
    for t in tasks:
        x = finds[t["id"]]
        bundle = {
            "task": t,
            "finding": {**clean(x), "body": x["_body"]},
            "components": [{**clean(comps[c]), "body": comps[c]["_body"]} for c in x["components"]],
            "related": [{**clean(finds[r]), "body": finds[r]["_body"]} for r in x.get("related") or []],
            "games": [clean(games[g]) for g in x.get("games") or []],
            "host_files": sorted({p for c in x["components"] for p in comps[c].get("host_files") or []}),
            "rules": f"{SITE}/llms.txt#rules",
        }
        bundle["token_estimate"] = est_tokens(bundle)
        write(f"api/task/{t['id']}.json", bundle)
    write("api/tasks.json", tasks)

    search = [brief(g, "game") | {"tags": [g.get("engine")] + (g.get("middleware") or [])} for g in games.values()]
    search += [brief(c, "component") | {"tags": [c["kind"]]} for c in comps.values()]
    search += [brief(x, "finding") | {"tags": x["components"] + [x["kind"], x["status"]] + (x.get("games") or [])} for x in finds.values()]
    write("api/search.json", search)

    stage = {str(g["id"]): max(g["status"], key=lambda s: STAGES.index(s["stage"]))["stage"] for g in games.values()}
    titles = json.loads(TITLES.read_text()) if TITLES.exists() else []
    write("api/titles.json", [t + [stage.get(t[0])] for t in titles])

    index = {
        "spec": SPEC_VERSION, "generated": datetime.now(timezone.utc).isoformat(), "site": SITE,
        "counts": {"games": len(games), "components": len(comps), "findings": len(finds),
                   "open_tasks": len(tasks), "titles": len(titles)},
        "endpoints": {
            "search": "api/search.json", "tasks": "api/tasks.json", "titles": "api/titles.json",
            "game": "api/games/{titleId}.json", "component": "api/components/{id}.json",
            "finding": "api/findings/{id}.json", "task_bundle": "api/task/{id}.json", "radar": "radar.json",
        },
        "spec_url": "https://github.com/catoncat/d2r-port-radar/blob/main/SPEC.md",
    }
    write("api/index.json", index)
    (DIST / "atlas.html").write_text((HERE / "site/atlas.html").read_text())
    (DIST / "llms.txt").write_text((HERE / "site/llms.txt").read_text()
                                   .replace("{{COUNTS}}", json.dumps(index["counts"]))
                                   .replace("{{SITE}}", SITE))
    return index["counts"]


def titles(refresh):
    """Whitelist text fields only: titledb also carries title keys, which must never be copied."""
    src = HERE / "data/.titledb-US.en.json"
    if refresh or not src.exists():
        urllib.request.urlretrieve("https://raw.githubusercontent.com/blawar/titledb/master/US.en.json", src)
    d = json.loads(src.read_text())
    best = {}  # one row per titleId: titledb lists editions (e.g. Switch 2 Edition) under the same id; keep the shortest name
    for t in d.values():
        tid, name = t.get("id"), (t.get("name") or "").strip()
        if not (tid and TITLE_ID.match(tid) and tid.endswith("000") and name) or t.get("isDemo") or "demo" in name.lower():
            continue
        row = (tid, name, (t.get("publisher") or "").strip(), str(t.get("releaseDate") or "")[:4])
        if tid not in best or len(name) < len(best[tid][1]):
            best[tid] = row
    rows = sorted(best.values())
    TITLES.write_text(json.dumps([list(r) for r in rows], ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {TITLES.relative_to(HERE)} ({len(rows)} base games)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "titles":
        return titles("--refresh" in sys.argv)
    objs, errors = validate()
    if errors:
        print(json.dumps(errors, ensure_ascii=False, indent=1))
        sys.exit(1)
    if cmd == "validate":
        print(json.dumps({"ok": True, **{k + "s": len(v) for k, v in objs.items()}}))
    elif cmd == "build":
        print(json.dumps({"ok": True, **build(objs)}))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

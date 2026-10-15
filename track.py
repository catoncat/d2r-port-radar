#!/usr/bin/env python3
"""Track ports built on jhaizhou-ops/d2r-mobile and render dist/index.html + dist/radar.json.

Usage: python3 track.py            # incremental (only re-checks repos pushed since last run)
       python3 track.py --full     # ignore cache

Sources: the fork network (forks + forks of forks, every branch) and independent
repos found by GitHub search or listed in data/notes.json.
Requires an authenticated `gh` CLI (GH_TOKEN works in CI).
"""
import json, subprocess, sys, re, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM = "jhaizhou-ops/d2r-mobile"
HERE = Path(__file__).resolve().parent
CACHE, NOTES = HERE / "data/cache.json", HERE / "data/notes.json"
TEMPLATE, DIST = HERE / "site/template.html", HERE / "dist"
# GitHub repo search queries for independent (non-fork) repos.
SEARCH = ["d2r-mobile", "d2r-mobile in:readme"]
SEARCH_SINCE = "2026-10-01"

# Paths that don't count as real porting work.
TRIVIAL = re.compile(r"^(\.github/|README|LICENSE|\.gitignore|docs/)", re.I)
# Keyword -> label, matched against repo name, description, branch names, commit subjects.
GAME_HINTS = {
    r"botw|zelda|塞尔达|breath of the wild": "Zelda BotW",
    r"totk|tears of the kingdom|王国之泪": "Zelda TotK",
    r"android|vulkan": "Android",
    r"tvos|apple tv": "tvOS",
    r"mario|马力欧|马里奥|smo\b|odyssey": "Mario",
    r"project ?diva|mega39|pjdv|初音": "Project DIVA",
    r"fire emblem|engage|火焰纹章": "Fire Emblem",
    r"pokemon|pokémon|宝可梦": "Pokémon",
    r"xenoblade|异度": "Xenoblade",
    r"hades": "Hades",
    r"p5r|persona|女神异闻录": "Persona 5 Royal",
    r"harmony|鸿蒙|openharmony": "HarmonyOS",
    r"ios ?18": "iOS 18",
}


def run_gh(args, required=False):
    for attempt in range(3):
        r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        if "HTTP 404" in r.stderr or "HTTP 422" in r.stderr:
            return None  # real "no such repo/branch/commit", retrying won't help
        time.sleep(2 * (attempt + 1))
    if required:
        sys.exit(f"gh api {' '.join(args)} failed:\n{r.stderr.strip()}")
    raise RuntimeError(r.stderr.strip())


def gh(path):
    return run_gh([path])


def gh_paginate(path):
    return [x for page in run_gh(["--paginate", "--slurp", path], required=True) for x in page]


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def list_forks():
    forks = gh_paginate(f"repos/{UPSTREAM}/forks?per_page=100")
    # One level of forks-of-forks, only for forks that have them.
    for f in [f for f in forks if f["forks_count"] > 0]:
        forks += gh_paginate(f"repos/{f['full_name']}/forks?per_page=100")
    return forks


def inspect(fork, upstream_heads):
    name, owner = fork["full_name"], fork["owner"]["login"]
    branches = gh(f"repos/{name}/branches?per_page=100") or []
    out = []
    for b in branches:
        if b["commit"]["sha"] in upstream_heads or b["name"] == "gh-pages":
            continue
        c = gh(f"repos/{UPSTREAM}/compare/main...{owner}:{b['name']}")
        if not c:
            out.append({"branch": b["name"], "unrelated": True})
            continue
        if c["ahead_by"] == 0:
            continue
        files = [f["filename"] for f in c.get("files", [])]
        real = [f for f in files if not TRIVIAL.match(f)]
        commits = c["commits"]
        out.append({
            "branch": b["name"],
            "ahead": c["ahead_by"],
            "behind": c["behind_by"],
            "files": len(files),
            "real_files": len(real),
            "dirs": sorted({"/".join(f.split("/")[:2]) for f in real})[:10],
            "last_commit": commits[-1]["commit"]["committer"]["date"] if commits else None,
            "subjects": [x["commit"]["message"].split("\n")[0] for x in commits[-8:]][::-1],
        })
    return out


def search_repos(extra):
    found = {}
    for q in SEARCH:
        res = run_gh(["-X", "GET", "search/repositories", "-f", f"q={q} fork:false created:>={SEARCH_SINCE}",
                      "-f", "per_page=100"], required=True)
        for r in res["items"]:
            found[r["full_name"]] = r
    for name in extra - found.keys():
        r = gh(f"repos/{name}")
        if r and not r.get("fork"):
            found[name] = r
    found.pop(UPSTREAM, None)
    return list(found.values())


def inspect_repo(repo, upstream_subjects):
    """Independent repo: no shared fork network, so just its recent commits.
    If every recent commit subject also appears upstream it is a mirror (SHAs may be rewritten)."""
    commits = gh(f"repos/{repo['full_name']}/commits?per_page=8") or []
    if not commits:
        return []
    subjects = [c["commit"]["message"].split("\n")[0] for c in commits]
    return [{
        "branch": repo["default_branch"],
        "mirror": set(subjects) <= upstream_subjects,
        "last_commit": commits[0]["commit"]["committer"]["date"],
        "subjects": subjects,
    }]


def tags(fork, branches, note):
    if note.get("game"):
        return [note["game"]]
    text = " ".join([fork["full_name"], fork.get("description") or ""] +
                    [b["branch"] for b in branches] +
                    [s for b in branches for s in b.get("subjects", [])]).lower()
    return [label for pat, label in GAME_HINTS.items() if re.search(pat, text)]


def refresh(cache, repos, fn):
    """Re-inspect repos whose pushed_at changed; failures are retried next run."""
    todo = [r for r in repos if cache.get(r["full_name"], {}).get("pushed_at") != r["pushed_at"]]

    def safe(r):
        try:
            return fn(r)
        except RuntimeError as err:
            print(f"  skip {r['full_name']} (will retry next run): {str(err).splitlines()[0]}")
            return None

    with ThreadPoolExecutor(8) as ex:
        for r, br in zip(todo, ex.map(safe, todo)):
            if br is not None:
                cache[r["full_name"]] = {"pushed_at": r["pushed_at"], "branches": br}
    return len(todo)


def row(repo, kind, branches, note):
    real = sum(b.get("real_files", 0) for b in branches)
    if kind == "repo":
        trivial = all(b.get("mirror") for b in branches)
    else:
        trivial = real == 0 and not any(b.get("unrelated") for b in branches)
    return {
        "name": repo["full_name"], "url": repo["html_url"], "kind": kind,
        "desc": repo.get("description") or "", "stars": repo["stargazers_count"],
        "pushed": repo["pushed_at"], "created": repo["created_at"], "branches": branches,
        "ahead": sum(b.get("ahead", 0) for b in branches), "real": real,
        "tags": tags(repo, branches, note), "note": note, "trivial": trivial,
    }


def main():
    full = "--full" in sys.argv
    cache = {} if full or not CACHE.exists() else json.loads(CACHE.read_text())
    notes = json.loads(NOTES.read_text()) if NOTES.exists() else {}

    upstream_heads = {b["commit"]["sha"] for b in gh_paginate(f"repos/{UPSTREAM}/branches?per_page=100")}
    forks = list_forks()
    fork_names = {f["full_name"] for f in forks}
    active = [f for f in forks if (ts(f["pushed_at"]) - ts(f["created_at"])).total_seconds() > 60]
    repos = search_repos(set(notes) - fork_names)
    n1 = refresh(cache, active, lambda f: inspect(f, upstream_heads))
    upstream_subjects = {c["commit"]["message"].split("\n")[0]
                         for c in gh(f"repos/{UPSTREAM}/commits?per_page=100") or []}
    n2 = refresh(cache, repos, lambda r: inspect_repo(r, upstream_subjects))
    print(f"{len(forks)} forks ({len(active)} pushed after forking), {len(repos)} independent repos; "
          f"re-checked {n1 + n2}")
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))

    rows = []
    for kind, items in (("fork", active), ("repo", repos)):
        for r in items:
            br = cache.get(r["full_name"], {}).get("branches")
            note = notes.get(r["full_name"], {})
            if br and not note.get("hide"):
                rows.append(row(r, kind, br, note))
    rows.sort(key=lambda r: (r["trivial"], -(r["note"].get("score", 0)), -r["real"], -r["ahead"]))

    data = {"upstream": UPSTREAM, "forks": len(forks), "active": len(active), "repos": len(repos),
            "generated": datetime.now(timezone.utc).isoformat(), "rows": rows}
    DIST.mkdir(exist_ok=True)
    (DIST / "radar.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (DIST / "index.html").write_text(TEMPLATE.read_text().replace("/*DATA*/null", blob))
    print(f"wrote dist/ ({sum(not r['trivial'] for r in rows)} substantive, {sum(r['trivial'] for r in rows)} trivial)")


if __name__ == "__main__":
    main()

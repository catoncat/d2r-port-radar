#!/usr/bin/env python3
"""MCP server (stdio) for the port knowledge base. Standard library only; reads the public static API.

Add to Claude Code:  claude mcp add port-atlas -- python3 /path/to/atlas_mcp.py
Override the source: PORT_ATLAS_URL=http://localhost:8000 (e.g. a local `python3 -m http.server -d dist`)
"""
import json, os, sys, urllib.request

BASE = os.environ.get("PORT_ATLAS_URL", "https://catoncat.github.io/d2r-port-radar").rstrip("/")
_cache = {}


def get(path):
    if path not in _cache:
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=30) as r:
            _cache[path] = json.load(r)
    return _cache[path]


def search(query, type=None, limit=20):
    q = query.lower()
    hits = [x for x in get("api/search.json")
            if (not type or x["type"] == type) and q in (x["id"] + x["title"] + x["summary"] + " ".join(map(str, x["tags"]))).lower()]
    if type in (None, "title"):
        hits += [{"type": "title", "id": t[0], "title": t[1], "summary": f"{t[2]} {t[3]}; port stage: {t[4] or 'no knowledge yet'}"}
                 for t in get("api/titles.json") if q in (t[0] + t[1] + t[2]).lower()]
    return hits[:limit]


TOOLS = {
    "search": ({"query": {"type": "string"}, "type": {"type": "string", "enum": ["game", "component", "finding", "title"]},
                "limit": {"type": "integer"}}, ["query"],
               "Search games, components, findings, and all Switch titles. Returns {type,id,title,summary}.", search),
    "get_game": ({"title_id": {"type": "string"}}, ["title_id"],
                 "A game's knowledge: technical profile, port status, components, findings, open tasks.",
                 lambda title_id: get(f"api/games/{title_id.upper()}.json")),
    "get_component": ({"id": {"type": "string"}}, ["id"],
                      "A reusable component (HLE service, NVN feature, middleware, engine) with every game and finding that touches it.",
                      lambda id: get(f"api/components/{id}.json")),
    "get_finding": ({"id": {"type": "string"}}, ["id"], "One finding in full: evidence, reproduction, fix location, body.",
                    lambda id: get(f"api/findings/{id}.json")),
    "list_tasks": ({"needs": {"type": "string", "description": "e.g. generic, game:0100CC80140F8000, device:mac"}}, [],
                   "Open work. Filter by what you can provide.",
                   lambda needs=None: [t for t in get("api/tasks.json") if not needs or needs in t["needs"]]),
    "get_task_bundle": ({"id": {"type": "string"}}, ["id"],
                        "Everything needed to start one task (finding, components, related findings, host files, rules) in one call.",
                        lambda id: get(f"api/task/{id}.json")),
}


def reply(id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id}
    msg.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except ValueError:
            continue
        m, id = req.get("method"), req.get("id")
        if id is None:
            continue  # notification
        if m == "initialize":
            reply(id, {"protocolVersion": req["params"].get("protocolVersion", "2025-06-18"),
                       "capabilities": {"tools": {}},
                       "serverInfo": {"name": "port-atlas", "version": "0.1"},
                       "instructions": "Switch native-port knowledge base. Start with search or list_tasks. "
                                       "Never request or share game bytes, keys or installers."})
        elif m == "tools/list":
            reply(id, {"tools": [{"name": n, "description": d,
                                  "inputSchema": {"type": "object", "properties": p, "required": r}}
                                 for n, (p, r, d, _) in TOOLS.items()]})
        elif m == "tools/call":
            name, args = req["params"]["name"], req["params"].get("arguments") or {}
            try:
                out = TOOLS[name][3](**args)
                reply(id, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]})
            except Exception as e:
                reply(id, {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True})
        elif m == "ping":
            reply(id, {})
        else:
            reply(id, error={"code": -32601, "message": f"unknown method {m}"})


if __name__ == "__main__":
    main()

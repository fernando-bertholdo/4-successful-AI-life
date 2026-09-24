#!/usr/bin/env python3
"""A stand-in for the `multica` binary, for the patch-description tests.

State lives in the JSON file named by FAKE_MULTICA_STATE and is rewritten on
every call. It serves `issue get`, `issue timeline` and `issue update` in the
shapes CLI v0.5.3 returns. What it reproduces, and where each came from:

- an update that changes the text moves `revision` by one and logs a
  `description_updated`; an identical one logs the event and moves nothing
  (throwaway issue, v0.5.2, 24/09/2026);
- the server drops one trailing newline of the text it stores (same issue);
- event and `updated_at` carry whole seconds only, and every event here lands in
  the same second (`now`), which is the case `--since` cannot see;
- `--since T` drops the whole second of T (measured on v0.5.3, 24/09/2026);
- `user profile get` returns as `id` the `actor_id` of the profile's own events
  (v0.5.3, 24/09/2026: all 9 `description_updated` on LAS-147). Its call is
  logged as "profile";
- with MULTICA_AGENT_ID set, as inside an agent task, `user profile get` still
  returns the member, and our update's event carries the agent's id, with
  `actor_type` agent and no `actor_name` key (LAS-140, LAS-141).

Hooks inject someone else's write around the n-th call of a kind:
{"when": "before"|"after", "call": "get"|"timeline"|"update", "nth": 1,
 "do": "write"|"append"|"identical"|"comment", "text": "..."}.
`own_event_lag` hides our own update's event from that many timeline reads.
"""
import json
import os
import sys

# An agent's event carries no `actor_name` key; a member's does (v0.5.3, 24/09/2026:
# LAS-140 and LAS-141 against LAS-147).
OTHER = {"actor_id": "other-actor", "actor_type": "agent"}
SELF = {"actor_id": "self-actor", "actor_type": "member", "actor_name": "Self"}


def write(st, text, who, hidden_until=0):
    if text.endswith("\n"):
        text = text[:-1]
    if text != st["description"]:
        st["revision"] += 1
    st["description"] = text
    st["updated_at"] = st["now"]
    st["seq"] += 1
    ev = dict(who, id=f"ev-{st['seq']}", action="description_updated",
              created_at=st["now"], details={}, type="activity")
    st["events"].append(dict(ev, hidden_until=hidden_until))


def run_hooks(st, when, call):
    for h in st.get("hooks", []):
        if h["when"] == when and h["call"] == call and h["nth"] == st["counts"][call]:
            if h["do"] == "comment":
                st["revision"] += 1
                st["updated_at"] = st["now"]
            elif h["do"] == "identical":
                write(st, st["description"], OTHER)
            elif h["do"] == "append":
                write(st, st["description"] + h["text"], OTHER)
            else:
                write(st, h["text"], OTHER)


def serve(st, cmd, ident, flags, stdin):
    if cmd == "profile":
        return {"id": SELF["actor_id"], "name": SELF["actor_name"]}
    if cmd == "get":
        return {"identifier": ident, "description": st["description"],
                "revision": st["revision"], "updated_at": st["updated_at"]}
    if cmd == "timeline":
        since = flags[flags.index("--since") + 1][:19] if "--since" in flags else None
        return [{k: v for k, v in e.items() if k != "hidden_until"}
                for e in st["events"]
                if e["hidden_until"] < st["counts"]["timeline"]
                and (since is None or e["created_at"][:19] > since)]
    if st.get("fail_update"):
        sys.exit(st["fail_update"])
    lag = st.get("own_event_lag", 0)
    agent = os.environ.get("MULTICA_AGENT_ID")
    who = {"actor_id": agent, "actor_type": "agent"} if agent else SELF
    write(st, stdin, who, st["counts"]["timeline"] + lag if lag else 0)
    return {"identifier": ident}


def main():
    path = os.environ["FAKE_MULTICA_STATE"]
    with open(path, encoding="utf-8") as f:
        st = json.load(f)
    args = sys.argv[1:]
    for flag in ("--profile", "--workspace-id"):
        if flag in args:
            i = args.index(flag)
            del args[i:i + 2]
    _, cmd, ident, *flags = args
    stdin = sys.stdin.read() if "--description-stdin" in flags else None
    st["calls"].append([cmd] + flags)
    st["counts"][cmd] = st["counts"].get(cmd, 0) + 1
    run_hooks(st, "before", cmd)
    out = serve(st, cmd, ident, flags, stdin)
    run_hooks(st, "after", cmd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

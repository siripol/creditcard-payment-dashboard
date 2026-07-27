---
description: List every merchant-group override (from merchant_group.json) with the group name and how many merchants and transactions each regex matches.
argument-hint: (no arguments)
---

Show the personal merchant-group overrides the user has set, and how much data each regex
actually groups. **Read-only** — never writes config, never rebuilds.

Do this:

1. **Read the overrides.** Open `merchant_group.json` (project root, git-ignored). If it is absent
   or has an empty `groups` list, say there are no merchant-group overrides yet and point to
   `/set-merchantGroup`, then stop. Each entry is `{"pattern": "<regex>", "group": "<name>"}`,
   applied in order — **first matching regex wins** — matched case-insensitively against the
   merchant display name (same rule as the build's `load_group_overrides()`).
2. **Count matches from data — never guess numbers.** If `data.js` is missing, run
   `python3 build_data.py` first (Python 3.12+; use `python3.12` if older). Then compute per-rule
   match counts with a small script over `CCDATA.tx`, honoring first-match-wins so each tx is
   attributed to only one rule:

   ```bash
   python3 - <<'PY'
   import re,json
   d=json.loads(re.search(r'window\.CCDATA\s*=\s*(\{.*\})\s*;',open('skills/credit-card-spending-dashboard/data.js',encoding='utf-8').read(),re.S).group(1))
   groups=json.load(open('merchant_group.json',encoding='utf-8')).get('groups',[])
   rx=[(re.compile(g['pattern'],re.I),g['group'],g['pattern']) for g in groups]
   for r,name,pat in rx:
       hits=[t for t in d['tx'] if r.search(t['merch']) and next((nm for rr,nm,_ in rx if rr.search(t['merch'])),None)==name]
       merchants=sorted({t['merch'] for t in hits})
       print(f"{pat}\t{name}\t{len(merchants):,}\t{len(hits):,}\t{sum(t['amt'] for t in hits):,.0f}\t{' | '.join(merchants[:3])}")
   PY
   ```
3. **Render one row per override:**

   | Pattern | Group name | Merchants | Tx | Total | Example matches |
   |---------|-----------|----------:|---:|------:|-----------------|

4. **Flag stale entries** — any rule matching **0** transactions (regex no longer hits anything)
   so the user can prune it.
5. Close with the override count and a note that these are set/renamed with `/set-merchantGroup`
   (grouping-only — the raw merchant name `tx.merch` is never changed).

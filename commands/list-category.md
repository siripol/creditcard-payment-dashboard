---
description: List every merchant→category override (from merchant_category.json) with how many merchants and transactions each one matches.
argument-hint: (no arguments)
---

Show the personal category overrides the user has set, and how much data each one actually
affects. **Read-only** — never writes config, never rebuilds.

Do this:

1. **Read the overrides.** Open `merchant_category.json` (project root, git-ignored). If it is
   absent or empty (only `_comment` / `{}`), say there are no overrides yet and point to
   `/set-category`, then stop. Ignore `_`-prefixed keys. Each remaining entry is
   `"KEYWORD": "Category"`, matched case-insensitively as a **substring of the raw description**
   (same rule as the build's `load_category_overrides()`).
2. **Count matches from data — never guess numbers.** If `data.js` is missing, run
   `python3 build_data.py` first (Python 3.12+; use `python3.12` if older). Then compute the
   per-keyword match counts with a small script over `CCDATA.tx`, e.g.:

   ```bash
   python3 - <<'PY'
   import re,json
   d=json.loads(re.search(r'window\.CCDATA\s*=\s*(\{.*\})\s*;',open('skills/credit-card-spending-dashboard/data.js',encoding='utf-8').read(),re.S).group(1))
   raw=json.load(open('merchant_category.json',encoding='utf-8'))
   ov={k:v for k,v in raw.items() if not k.startswith('_')}
   src=raw.get('_source',{})   # keyword -> "user" | "llm"
   for kw,cat in ov.items():
       hits=[t for t in d['tx'] if kw.lower() in t['desc'].lower()]
       merchants={t['merchGroup'] or t['merch'] for t in hits}
       who={'user':'user','llm':'LLM'}.get(src.get(kw),'—')
       print(f"{kw}\t{cat}\t{who}\t{len(merchants):,}\t{len(hits):,}\t{sum(t['amt'] for t in hits):,.0f}")
   PY
   ```
3. **Render one row per override** (a `Source` column shows who set it — `user`, `LLM`, or `—`):

   | Keyword | Category | Source | Merchants | Tx | Total |
   |---------|----------|--------|----------:|---:|------:|

4. **Flag stale entries** — any override matching **0** transactions (keyword no longer in the
   data) so the user can prune it.
5. Close with the override count and a note that these are set/edited with `/set-category`
   (`user` source) or `/auto-categorize` (`LLM` source); `user`-sourced entries are pinned and
   never changed by `/auto-categorize`. The mapping is category-only — merchant names are never
   changed.

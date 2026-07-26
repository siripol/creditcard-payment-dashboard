---
description: List all merchant rules — category mappings, name cleanups, and extra excludes.
argument-hint: (no arguments)
---

Show the current merchant rules from `merchant_rules.json` (project root, git-ignored).

Do this:

1. Open `merchant_rules.json`. If it does not exist, tell the user no personal merchant rules are
   set yet — only the built-in defaults in `build_data.py` (`cat()`/`merch()`) apply — and point
   them at `/set-merchantRule` (or copying `merchant_rules.example.json`). Then stop.
2. If it exists, render its three sections, each as a small table (skip a section if empty):

   **Category** (keyword → category)
   | Keyword | Category |
   |---------|----------|

   **Cleanup** (keyword → display name)
   | Keyword | Display name |
   |---------|--------------|

   **Exclude** (extra non-spending keywords) — a simple list.
3. Flag any `category` value that is NOT one of the valid keys (`Travel`, `Insurance`,
   `Shopping & Retail`, `Food & Dining`, `Subscriptions & Digital`, `Groceries & Convenience`,
   `Transport & Ride-hailing`, `Online Shopping`, `Health & Medical`, `Utilities & Telecom`,
   `Fuel`, `Card Fees`, `Other`) — those are ignored at build time.
4. Read-only: do not edit the file or rebuild. To change a rule, use `/set-merchantRule`.

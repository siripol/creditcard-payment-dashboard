#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data.py — Credit-card statement importer / data builder.

WHAT IT DOES
  1. Reads every statement PDF in the SOURCE_DIR (one or more cards).
  2. Parses each transaction, keeping the real transaction date.
  3. Categorises + normalises merchant names from the Description text.
  4. Applies the data rules:
       - drop payments / cashback / credit-adjustments / refunds / negatives
       - remove matched debit<->reversal pairs (same card+amount, desc-normalized so
         "REVERSAL X" pairs with "X"; same date preferred, any date accepted)
       - DEDUPE by a stable key so re-importing the same statement never
         double-counts (this is the human-error guard).
  5. Writes data.js  ->  window.CCDATA = { ... }
     The dashboard (index.html) loads that file with <script src="data.js">.

MONTHLY WORKFLOW
  - Drop the new month's statement PDF(s) into SOURCE_DIR.
  - Run:  python3 build_data.py
  - Re-open index.html. Done. Re-running with a duplicate file is safe.

STABLE DEDUPE KEY = (card, transaction_date, normalised_description, amount)
  Identical lines that share this key are treated as the SAME transaction and
  kept only once — whether the duplication comes from one file or from
  importing the same file twice.
"""
import re, glob, json, sys, os

# ---- where the statement PDFs live ----
# Default: a "statements" folder next to this script.
# Override with:  CC_SOURCE_DIR=/path/to/pdfs python3 build_data.py
_HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.environ.get("CC_SOURCE_DIR", os.path.join(_HERE, "statements"))
OUT_JS     = os.environ.get("CC_OUT", os.path.join(_HERE, "data.js"))
OUT_HTML   = os.environ.get("CC_DASH", os.path.join(_HERE, "dashboard.html"))
VENDOR_CHARTJS = os.path.join(_HERE, "vendor", "chart.umd.js")
CARDS_CONFIG = os.path.join(_HERE, "cards.config.json")
CARD_PALETTE =[("#134e7a","#7ba0c4"),("#c65a2b","#e2a06f"),("#0f6e56","#6db3a0"),("#6a3d9a","#a684c7"),("#9a6a00","#d0ad5a"),("#8a1f4b","#c77394")]
def load_card_config():
    if os.path.isfile(CARDS_CONFIG):
        try: return json.load(open(CARDS_CONFIG, encoding="utf-8"))
        except Exception: return {}
    return {}

def save_card_config(cfg):
    """Persist cards.config.json (git-ignored personal data). Keeps insertion order so
    _comment / _default stay on top."""
    with open(CARDS_CONFIG, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

def _valid_mmdd(s):
    s = str(s or "")
    return len(s) == 4 and s.isdigit() and 1 <= int(s[:2]) <= 12

def ensure_card_defaults(cfg, cards):
    """Standing rule: any detected card with no mmdd inherits cfg['_default']['mmdd']
    (e.g. '1231' = year-end). Preserves every existing entry -- idempotent. Returns True
    if cfg changed. No-op when _default is absent (generic plugin behaviour)."""
    default_mmdd = (cfg.get("_default") or {}).get("mmdd")
    if not _valid_mmdd(default_mmdd):
        return False
    changed = False
    for k in cards:
        entry = cfg.get(k)
        if not isinstance(entry, dict) or not _valid_mmdd(entry.get("mmdd")):
            merged = dict(entry) if isinstance(entry, dict) else {}
            merged["mmdd"] = default_mmdd
            cfg[k] = merged
            changed = True
    return changed

def _rev_norm(s):
    """Normalise a description for reversal matching: collapse whitespace, uppercase, and
    strip a leading reversal marker so 'REVERSAL X' pairs with 'X'."""
    s = re.sub(r'\s+', ' ', s.strip()).upper()
    return re.sub(r'^(REVERSAL|REVERSE|REV|VOID|CANCELLATION|CANCELLED|CANCEL|'
                  r'ยกเลิก|โอนกลับ|'
                  r'คืนรายการ)\b[\s:\-]*', '', s)

def cancel_reversal_pairs(dedup):
    """Cancel a positive charge against an opposite-sign reversal. Matches on
    (card, amount, normalized-desc); two passes so a same-date reversal is preferred and a
    cross-date one still cancels. Only non-EXCLUDE negatives are eligible (plain
    refunds/cashback are EXCLUDE and dropped separately). Returns (drop_set, pair_count).
    Each row is a dict with card / date / desc / amt / cat."""
    from collections import defaultdict
    drop = set(); used_neg = set()
    def _pair(keyfn):
        idx = defaultdict(list)
        for i, r in enumerate(dedup):
            if i not in used_neg and r['amt'] < 0 and r['cat'] != 'EXCLUDE':
                idx[keyfn(r, round(-r['amt'], 2))].append(i)
        c = 0
        for i, r in enumerate(dedup):
            if i not in drop and r['amt'] > 0 and r['cat'] != 'EXCLUDE':
                lst = idx.get(keyfn(r, round(r['amt'], 2)))
                if lst:
                    used_neg.add(lst.pop()); drop.add(i); c += 1
        return c
    pairs  = _pair(lambda r, a: (r['card'], r['date'], _rev_norm(r['desc']), a))  # same date
    pairs += _pair(lambda r, a: (r['card'], _rev_norm(r['desc']), a))             # any date
    return drop, pairs

MON = {m: i + 1 for i, m in enumerate(
    ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'])}

# Spending category keys (display order). Module-level; build() reuses this for the CCDATA
# payload. Keys must match TH / COLORS / GROUP in build().
CAT_ORDER = ['Travel','Insurance','Shopping & Retail','Food & Dining',
             'Subscriptions & Digital','Groceries & Convenience','Transport & Ride-hailing',
             'Online Shopping','Health & Medical','Utilities & Telecom','Fuel',
             'Card Fees','Other']

# ------------------------------------------------------------------ categorise
def cat(d):
    """Map a raw transaction DESCRIPTION to a spending category.
    EXAMPLE keyword rules only -- replace the keywords in has(...) with YOUR merchants.
    Keep EXCLUDE first so non-spending lines are dropped. Category KEYS must match
    CAT_ORDER / TH / COLORS / GROUP in build()."""
    D = d.upper()
    def has(*ks): return any(k in D for k in ks)
    if has('PAYMENT', 'CASHBACK', 'CASH BACK', 'REFUND', 'CR ADJUSTMENT'):  return 'EXCLUDE'
    if has('ANNUAL FEE', 'MEMBERSHIP FEE'):                                 return 'Card Fees'
    if has('TAXI', 'RIDE HAIL', 'TRANSIT', 'METRO', 'TOLL', 'EXPRESSWAY'):  return 'Transport & Ride-hailing'
    if has('FUEL', 'PETROL', 'GAS STATION'):                                return 'Fuel'
    if has('SUPERMARKET', 'GROCERY', 'CONVENIENCE STORE'):                  return 'Groceries & Convenience'
    if has('MARKETPLACE', 'ONLINE STORE'):                                  return 'Online Shopping'
    if has('RESTAURANT', 'CAFE', 'COFFEE', 'FOOD DELIVERY', 'DINING'):      return 'Food & Dining'
    if has('HOSPITAL', 'CLINIC', 'PHARMACY', 'DENTAL'):                     return 'Health & Medical'
    if has('INSURANCE', 'LIFE ASSURANCE'):                                  return 'Insurance'
    if has('SUBSCRIPTION', 'STREAMING', 'SOFTWARE', 'ONLINE COURSE'):       return 'Subscriptions & Digital'
    if has('ELECTRIC', 'WATER BILL', 'MOBILE', 'TELECOM', 'INTERNET'):      return 'Utilities & Telecom'
    if has('DEPARTMENT STORE', 'RETAIL', 'CLOTHING', 'ELECTRONICS'):        return 'Shopping & Retail'
    if has('HOTEL', 'AIRLINE', 'FLIGHT', 'CAR RENTAL', 'TOUR'):             return 'Travel'
    return 'Other'

# ------------------------------------------------------------------ merchant
def merch(d):
    """Turn a raw description into a clean display name. EXAMPLE rules only."""
    D = d.upper()
    rules = [
        ('SUPERMARKET', 'Supermarket'),
        ('COFFEE', 'Coffee Shop'),
        ('FUEL', 'Fuel Station'),
        # ('YOUR RAW KEYWORD', 'Your Display Name'),
    ]
    for k, v in rules:
        if k in D:
            return v
    n = re.sub(r'\s{2,}.*$', '', d).strip()
    return n.title() if n.isupper() else n

# ------------------------------------------------------------------ parse
def card_key(txt):
    """Return the card identifier = LAST 4 DIGITS of the card number shown on the statement.
    Statements usually print a masked PAN like '1234-56XX-XXXX-0135'. ADAPT this regex.
    Falls back to 'UNKNOWN' if not found (configure it in cards.config.json)."""
    m2 = re.search(r'(\d[\dX*\- ]{6,}\d)', txt)
    if m2:
        d = re.sub(r'\D', '', m2.group(1))
        if len(d) >= 4:
            return d[-4:]
    return 'UNKNOWN'

def parse_card_a(path):
    """EXAMPLE parser for one card's statement layout. ADAPT regexes to your
    `pdftotext -layout` output. Return dicts(card=..., stmt='YYYY-MM',
    date='YYYY-MM-DD', desc=str, amt=float). Negative amt = credit/refund.
    The 'card' value is overwritten with card_key() in build()."""
    txt = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'STATEMENT DATE\s+(\d{1,2}) (\w{3}) (\d{4})', txt)
    if not m:
        return []
    syear, smon = int(m.group(3)), MON[m.group(2)]
    stmt = f"{syear}-{smon:02d}"
    out = []
    for line in txt.splitlines():
        lm = re.match(r'\s*(\d{2}) (\w{3})\s+(\d{2}) (\w{3})\s+(.+?)\s+([\d,]+\.\d{2})(\s+CR)?\s*$', line)
        if not lm:
            continue
        tday, tmon = int(lm.group(3)), lm.group(4)
        desc = lm.group(5).strip()
        amt = float(lm.group(6).replace(',', ''))
        cr = bool(lm.group(7))
        if any(s in desc for s in ('PREVIOUS BALANCE', 'SUB TOTAL', 'TOTAL')):
            continue
        if tmon not in MON:
            continue
        tyear = syear if MON[tmon] <= smon else syear - 1
        tdate = f"{tyear}-{MON[tmon]:02d}-{tday:02d}"
        out.append(dict(card='', stmt=stmt, date=tdate, desc=desc, amt=-amt if cr else amt))
    return out

def parse_card_b(path):
    """EXAMPLE parser for a second layout. Adapt as above."""
    txt = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})\n', txt)
    if not m:
        return []
    stmt = f"{m.group(3)}-{m.group(2)}"
    out = []
    for line in txt.splitlines():
        lm = re.match(r'\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{2})/(\d{2})/(\d{4})\s+(.+?)\s+([\d,]+\.\d{2}).*$', line)
        if not lm:
            continue
        tdate = f"{lm.group(3)}-{lm.group(2)}-{lm.group(1)}"
        desc = lm.group(7).strip()
        if 'SUBTOTAL' in desc:
            continue
        amt = float(lm.group(8).replace(',', ''))
        out.append(dict(card='', stmt=stmt, date=tdate, desc=desc, amt=amt))
    return out

# ------------------------------------------------------------------ main build
def build():
    # statements/ may be absent when rebuilding from the .txt_cache archive (PDFs removed);
    # glob on a missing dir just returns [] and the .txt_cache fallback below handles it.
    files = sorted(glob.glob(os.path.join(SOURCE_DIR, '*.pdf'))) if os.path.isdir(SOURCE_DIR) else []
    cache = os.path.join(_HERE, '.txt_cache')
    os.makedirs(cache, exist_ok=True)
    # Resolve the extracted-text files to build from.
    if files:
        # PDFs present: convert each to cached text (skip if already cached).
        txts = []
        for f in files:
            base = re.sub(r'\.pdf$', '', os.path.basename(f))
            txt = os.path.join(cache, base + '.txt')
            if not os.path.exists(txt):
                os.system(f'pdftotext -layout "{f}" "{txt}" 2>/dev/null')
            txts.append(txt)
    else:
        # No PDFs: fall back to the archived extracted text in .txt_cache -- the complete raw
        # text of every statement -- so a rebuild still works after the source PDFs are removed.
        txts = sorted(glob.glob(os.path.join(cache, '*.txt')))
        if not txts:
            print(f"ERROR: ไม่พบไฟล์ PDF ใน {SOURCE_DIR} และไม่มีข้อความสำรองใน {cache}")
            print("วางไฟล์ statement PDF ไว้ใน statements/ แล้วรันใหม่")
            sys.exit(1)
        print(f"ไม่พบ PDF — ใช้ข้อความสำรองจาก .txt_cache ({len(txts)} ไฟล์)")
    built_from = [os.path.basename(t) for t in txts]
    # parse each extracted-text file
    rows = []
    for txt in txts:
        recs = parse_card_a(txt) or parse_card_b(txt)  # adapt routing to your files
        key = card_key(open(txt, encoding='utf-8', errors='ignore').read())
        for r in recs:
            r['card'] = key
        rows += recs

    # categorise
    for r in rows:
        r['cat'] = cat(r['desc'])
        r['merch'] = merch(r['desc'])

    raw_n = len(rows)

    # ---- STABLE-KEY DEDUPE (prevents double import) ----
    # key = card | transaction date | raw description | amount
    seen = set(); dedup = []; dup_removed = 0
    for r in rows:
        key = (r['card'], r['date'], r['desc'], round(r['amt'], 2))
        if key in seen:
            dup_removed += 1
            continue
        seen.add(key); dedup.append(r)

    # ---- reversal pairs: a positive expense + an opposite-sign reversal cancel both ----
    drop, pairs = cancel_reversal_pairs(dedup)

    expenses = [r for i, r in enumerate(dedup)
                if i not in drop and r['cat'] != 'EXCLUDE' and r['amt'] > 0]

    tx = [dict(d=r['date'], m=r['stmt'], card=r['card'], cat=r['cat'],
               merch=r['merch'], desc=re.sub(r'\s{2,}', ' ', r['desc'])[:48],
               amt=round(r['amt'], 2)) for r in expenses]
    tx.sort(key=lambda t: (t['d'], -t['amt']))

    # CAT_ORDER is defined at module scope (also used by cat() to validate user overrides)
    TH = {'Travel':'ท่องเที่ยว','Insurance':'ประกัน',
          'Shopping & Retail':'ช้อปปิ้งห้าง/ร้านค้า','Food & Dining':'อาหาร & ร้านอาหาร',
          'Subscriptions & Digital':'สมาชิก/ดิจิทัล/คอร์สเรียน','Groceries & Convenience':'ของกินของใช้/ซูเปอร์',
          'Transport & Ride-hailing':'เดินทาง','Online Shopping':'ช้อปออนไลน์',
          'Health & Medical':'สุขภาพ/หมอ/ยา','Utilities & Telecom':'ค่าน้ำไฟ/มือถือ','Fuel':'น้ำมัน',
          'Card Fees':'ค่าธรรมเนียมบัตร','Other':'อื่นๆ'}
    COLORS = {'Travel':'#2a78d6','Insurance':'#eb6834','Shopping & Retail':'#1baf7a',
              'Food & Dining':'#eda100','Subscriptions & Digital':'#e87ba4','Groceries & Convenience':'#008300',
              'Transport & Ride-hailing':'#4a3aa7','Online Shopping':'#d55181','Health & Medical':'#e34948',
              'Utilities & Telecom':'#199e70','Fuel':'#c98500','Card Fees':'#888780','Other':'#b4b2a9'}
    GROUP = {'Insurance':'need','Health & Medical':'need','Utilities & Telecom':'need','Fuel':'need',
             'Groceries & Convenience':'need','Card Fees':'special','Travel':'special'}

    months = sorted({t['m'] for t in tx})
    TMON = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']
    mth = {m: f"{TMON[int(m[5:7])-1]} {int(m[:4])%100:02d}" for m in months}

    cfg = load_card_config()
    cards = sorted(set(t['card'] for t in tx))
    if ensure_card_defaults(cfg, cards):      # standing rule: new card -> _default mmdd
        save_card_config(cfg)
    cardMeta = {}
    for i, k in enumerate(cards):
        mmdd = str((cfg.get(k) or {}).get("mmdd", "") or "")
        if len(mmdd) >= 2 and mmdd[:2].isdigit() and 1 <= int(mmdd[:2]) <= 12:
            anchor = int(mmdd[:2])
        else:
            mset = sorted({t['m'] for t in tx if t['card'] == k})
            anchor = int(mset[0][5:7]) if mset else 1
        col, bar = CARD_PALETTE[i % len(CARD_PALETTE)]
        cardMeta[k] = dict(name=(cfg.get(k) or {}).get("name", "Card \u2022\u2022" + k), anchor=anchor, color=col, bar=bar)
    reduce_groups = [c for c in CAT_ORDER if GROUP.get(c) == 'reduce']
    payload = dict(tx=tx, catOrder=CAT_ORDER, th=TH, colors=COLORS, group=GROUP,
                   cards=cards, cardMeta=cardMeta, reduceGroups=reduce_groups,
                   mth=mth, months=months,
                   meta=dict(raw=raw_n, dupRemoved=dup_removed, pairsRemoved=pairs,
                             expenses=len(tx), files=len(built_from),
                             builtFrom=built_from))
    with open(OUT_JS, 'w', encoding='utf-8') as fh:
        fh.write("window.CCDATA = " + json.dumps(payload, ensure_ascii=False) + ";\n")

    write_markdown(payload)
    write_monthly_brief(payload)
    write_single_html(payload)

    print(f"files={len(built_from)}  raw_lines={raw_n}  duplicates_removed={dup_removed}  "
          f"reversal_pairs={pairs}  final_expenses={len(tx)}")
    print(f"wrote {OUT_JS}  ({os.path.getsize(OUT_JS):,} bytes)")
    return payload


def write_markdown(P):
    """Emit a self-contained Markdown report for Cowork / sharing."""
    from collections import defaultdict
    tx, TH, CO, GROUP = P['tx'], P['th'], P['colors'], P['group']
    months, mth, CAT_ORDER = P['months'], P['mth'], P['catOrder']
    out = os.environ.get("CC_MD", os.path.join(_HERE, "spending_report.md"))

    def fmt(v): return "฿{:,.0f}".format(round(v))

    catMon = defaultdict(lambda: defaultdict(float))
    catTot = defaultdict(float); monTot = defaultdict(float)
    cardTot = defaultdict(float); cardN = defaultdict(int)
    merch = defaultdict(lambda: {"total": 0.0, "n": 0, "cat": None, "months": defaultdict(float), "cards": set(), "tx": []})
    total = 0.0
    for t in tx:
        catMon[t['cat']][t['m']] += t['amt']; catTot[t['cat']] += t['amt']
        monTot[t['m']] += t['amt']; cardTot[t['card']] += t['amt']; cardN[t['card']] += 1
        M = merch[t['merch']]; M['total'] += t['amt']; M['n'] += 1; M['cat'] = t['cat']
        M['months'][t['m']] += t['amt']; M['cards'].add(t['card']); M['tx'].append(t)
        total += t['amt']

    cats = [c for c in CAT_ORDER if catTot[c] > 0]
    cats.sort(key=lambda c: -catTot[c])
    active = len([m for m in months if monTot[m] > 0])
    peak = max(months, key=lambda m: monTot[m]) if months else None

    # recurring
    ALLM = months
    def recurring():
        res = []
        for name, x in merch.items():
            if x['cat'] == 'Insurance': continue  # ร้านค้าประจำ ไม่รวมบริษัทประกัน
            ms = sorted(x['months'].keys())
            maxrun = run = 1
            for i in range(1, len(ms)):
                if ALLM.index(ms[i]) - ALLM.index(ms[i-1]) == 1:
                    run += 1; maxrun = max(maxrun, run)
                else: run = 1
            multi = sum(1 for m in x['months'] if sum(1 for t in x['tx'] if t['m'] == m) > 1)
            if maxrun >= 3 or multi >= 3:
                res.append((name, x, len(ms)))
        res.sort(key=lambda r: (-r[2], -r[1]['total']))
        return res

    L = []
    L.append("# รายงานค่าใช้จ่ายบัตรเครดิต")
    L.append("")
    span = f"{mth[months[0]]} – {mth[months[-1]]}" if months else "-"
    _cm0 = P.get("cardMeta", {}); _cards0 = P.get("cards", [])
    cards_lbl = " + ".join((_cm0.get(k) or {}).get("name", "Card ••" + k) for k in _cards0) or "-"
    L.append(f"ช่วงข้อมูล: **{span}** · บัตร: {cards_lbl} · เฉพาะค่าใช้จ่ายจริง (ตัดยอดชำระ/เงินคืน/รายการซ้ำแล้ว)")
    L.append("")
    L.append("## สรุปภาพรวม")
    L.append("")
    L.append(f"- ยอดใช้จ่ายรวม: **{fmt(total)}** จาก {len(tx):,} รายการ")
    L.append(f"- เฉลี่ยต่อเดือน: **{fmt(total/max(active,1))}** ({active} เดือนที่มีการใช้จ่าย)")
    if peak:
        L.append(f"- เดือนที่ใช้สูงสุด: **{mth[peak]}** = {fmt(monTot[peak])}")
    _cm = P.get("cardMeta", {}); _cards = P.get("cards", sorted(cardTot.keys()))
    _nm = lambda k: (_cm.get(k) or {}).get("name", k)
    L.append("- แยกตามบัตร: " + " · ".join(f"{_nm(k)} {fmt(cardTot[k])} ({cardN[k]} รายการ)" for k in _cards))
    L.append("")

    # monthly totals
    L.append("## ยอดรวมรายเดือน")
    L.append("")
    L.append("| เดือน | " + " | ".join(_nm(k) for k in _cards) + " | รวมทั้งเดือน |")
    L.append("|---|" + "--:|" * (len(_cards) + 1))
    for m in months:
        vals = [sum(t['amt'] for t in tx if t['m'] == m and t['card'] == k) for k in _cards]
        L.append("| " + mth[m] + " | " + " | ".join(fmt(v) for v in vals) + f" | **{fmt(monTot[m])}** |")
    L.append("| **รวม** | " + " | ".join(f"**{fmt(cardTot[k])}**" for k in _cards) + f" | **{fmt(total)}** |")
    L.append("")

    # category x month matrix
    L.append("## เปรียบเทียบรายเดือน แยกตามประเภท")
    L.append("")
    L.append("| ประเภท | " + " | ".join(mth[m] for m in months) + " | รวม |")
    L.append("|---|" + "--:|" * (len(months) + 1))
    for c in cats:
        row = [TH[c]] + [fmt(catMon[c][m]) if catMon[c][m] else "–" for m in months] + [f"**{fmt(catTot[c])}**"]
        L.append("| " + " | ".join(row) + " |")
    totrow = ["**รวมทั้งเดือน**"] + [f"**{fmt(monTot[m])}**" for m in months] + [f"**{fmt(total)}**"]
    L.append("| " + " | ".join(totrow) + " |")
    L.append("")

    # spending structure
    L.append("## โครงสร้างค่าใช้จ่าย")
    L.append("")
    gsum = defaultdict(float)
    for c in catTot: gsum[GROUP.get(c, 'reduce')] += catTot[c]
    glabel = {'need': 'จำเป็น / ภาระประจำ', 'reduce': 'ปรับลดได้', 'special': 'ก้อนพิเศษ / ท่องเที่ยว'}
    L.append("| กลุ่ม | ยอดรวม | สัดส่วน |")
    L.append("|---|--:|--:|")
    for g in ['need', 'reduce', 'special']:
        L.append(f"| {glabel[g]} | {fmt(gsum[g])} | {gsum[g]/max(total,1)*100:.0f}% |")
    L.append("")

    # top merchants
    L.append("## Top 20 ร้านค้าตามยอดรวม")
    L.append("")
    L.append("| # | ร้านค้า / ผู้ให้บริการ | ประเภท | ครั้ง | เฉลี่ย/เดือน | รวม |")
    L.append("|--:|---|---|--:|--:|--:|")
    topm = sorted(merch.items(), key=lambda kv: -kv[1]['total'])[:20]
    for i, (name, x) in enumerate(topm, 1):
        avg = x['total'] / max(len(x['months']), 1)
        L.append(f"| {i} | {name} | {TH[x['cat']]} | {x['n']} | {fmt(avg)} | {fmt(x['total'])} |")
    L.append("")

    # recurring
    rec = recurring()
    L.append("## ร้านค้าประจำ (จ่ายซ้ำหลายเดือน)")
    L.append("")
    L.append("เงื่อนไข: จ่ายต่อเนื่อง ≥3 เดือนติด หรือ ≥3 เดือนที่ใช้มากกว่า 1 ครั้ง/เดือน")
    L.append("")
    L.append("| # | ร้านค้า | จำนวนเดือน | จำนวนครั้ง | ยอดรวม |")
    L.append("|--:|---|--:|--:|--:|")
    for i, (name, x, mc) in enumerate(rec[:20], 1):
        L.append(f"| {i} | {name} | {mc} | {x['n']} | {fmt(x['total'])} |")
    L.append("")

    # savings
    REDUCE = {'Food & Dining', 'Transport & Ride-hailing', 'Shopping & Retail',
              'Online Shopping', 'Subscriptions & Digital', 'Other'}
    reduceTot = sum(catTot[c] for c in catTot if c in REDUCE)
    L.append("## แนวทางลดค่าใช้จ่าย")
    L.append("")
    L.append(f"- กลุ่มที่ปรับลดได้รวม: **{fmt(reduceTot)}** — ประเมินประหยัดได้ ~15% = **{fmt(reduceTot*0.15)}**")
    for c in ['Food & Dining', 'Online Shopping', 'Shopping & Retail', 'Subscriptions & Digital']:
        v = catTot.get(c, 0)
        if v:
            L.append(f"- **{TH.get(c, c)}**: {fmt(v)} — ทบทวนรายการในหมวดนี้")
    ins = catTot.get('Insurance', 0)
    if ins: L.append(f"- **ประกัน**: {fmt(ins)} — ยอดใหญ่ที่คงที่ ควรรีวิวความคุ้มครองซ้ำซ้อนปีละครั้ง")
    fee = catTot.get('Card Fees', 0)
    if fee: L.append(f"- **ค่าธรรมเนียมบัตร**: {fmt(fee)} — โทรขอยกเว้นค่าธรรมเนียม (fee waiver)")
    L.append("")

    L.append("---")
    L.append(f"> ประมวลผลจาก {P['meta']['files']} ไฟล์ Statement · ตัดรายการซ้ำ {P['meta']['dupRemoved']} รายการ · คู่ที่ถูกยกเลิก {P['meta']['pairsRemoved']} คู่ · เหลือค่าใช้จ่ายจริง {P['meta']['expenses']:,} รายการ")
    L.append("> ตัวเลข “ประหยัดได้” เป็นการประเมินเบื้องต้น ไม่ใช่คำแนะนำทางการเงิน")

    with open(out, 'w', encoding='utf-8') as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")


def write_monthly_brief(P):
    """Monthly brief: latest month vs previous month + trailing average, with anomaly flags.

    This is the file the Cowork scheduled task reads each month.
    Everything here is computed deterministically so the numbers never drift.
    """
    from collections import defaultdict
    tx, TH, GROUP = P['tx'], P['th'], P['group']
    months, mth = P['months'], P['mth']
    out = os.environ.get("CC_BRIEF", os.path.join(_HERE, "monthly_brief.md"))

    def fmt(v): return "\u0e3f{:,.0f}".format(round(v))
    def pct(new, old):
        if old <= 0: return None
        return (new - old) / old * 100
    def arrow(p):
        if p is None: return ""
        return "\u25b2" if p > 0 else ("\u25bc" if p < 0 else "=")

    if not months:
        open(out, 'w', encoding='utf-8').write("# \u0e2a\u0e23\u0e38\u0e1b\u0e23\u0e32\u0e22\u0e40\u0e14\u0e37\u0e2d\u0e19\n\n\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\n")
        print(f"wrote {out} (no data)")
        return

    cur = months[-1]
    prev = months[-2] if len(months) > 1 else None
    base = months[-7:-1] if len(months) > 2 else []   # up to 6 previous months

    monTot = defaultdict(float)
    catMon = defaultdict(lambda: defaultdict(float))
    merchMon = defaultdict(lambda: defaultdict(float))
    merchN = defaultdict(lambda: defaultdict(int))
    cardMon = defaultdict(lambda: defaultdict(float))
    for t in tx:
        monTot[t['m']] += t['amt']
        catMon[t['cat']][t['m']] += t['amt']
        merchMon[t['merch']][t['m']] += t['amt']
        merchN[t['merch']][t['m']] += 1
        cardMon[t['card']][t['m']] += t['amt']

    def avg_of(d, mlist):
        vals = [d.get(m, 0) for m in mlist]
        return sum(vals) / len(vals) if vals else 0

    L = []
    L.append(f"# \u0e2a\u0e23\u0e38\u0e1b\u0e04\u0e48\u0e32\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22 \u2014 {mth[cur]}")
    L.append("")
    L.append(f"\u0e23\u0e2d\u0e1a statement \u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14: **{mth[cur]}** \u00b7 \u0e40\u0e17\u0e35\u0e22\u0e1a\u0e01\u0e31\u0e1a: {mth[prev] if prev else '\u2013'}")
    L.append("")

    # ---- headline ----
    curTot = monTot[cur]
    prevTot = monTot[prev] if prev else 0
    p = pct(curTot, prevTot)
    baseAvg = avg_of(monTot, base)
    pb = pct(curTot, baseAvg)
    L.append("## \u0e15\u0e31\u0e27\u0e40\u0e25\u0e02\u0e2b\u0e25\u0e31\u0e01")
    L.append("")
    L.append("| \u0e23\u0e32\u0e22\u0e01\u0e32\u0e23 | \u0e04\u0e48\u0e32 |")
    L.append("|---|--:|")
    L.append(f"| \u0e22\u0e2d\u0e14\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49 | **{fmt(curTot)}** |")
    if prev:
        L.append(f"| \u0e40\u0e17\u0e35\u0e22\u0e1a\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19 ({mth[prev]}) | {fmt(prevTot)} \u00b7 {arrow(p)} {p:+.0f}% |" if p is not None else f"| \u0e40\u0e17\u0e35\u0e22\u0e1a\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19 | {fmt(prevTot)} |")
    if base:
        L.append(f"| \u0e40\u0e09\u0e25\u0e35\u0e48\u0e22\u0e22\u0e49\u0e2d\u0e19\u0e2b\u0e25\u0e31\u0e07 {len(base)} \u0e40\u0e14\u0e37\u0e2d\u0e19 | {fmt(baseAvg)} \u00b7 {arrow(pb)} {pb:+.0f}% |" if pb is not None else f"| \u0e40\u0e09\u0e25\u0e35\u0e48\u0e22\u0e22\u0e49\u0e2d\u0e19\u0e2b\u0e25\u0e31\u0e07 | {fmt(baseAvg)} |")
    _cm = P.get('cardMeta', {})
    for card in P.get('cards', sorted(cardMon.keys())):
        if cardMon[card].get(cur):
            _n = (_cm.get(card) or {}).get('name', card)
            L.append(f"| {_n} | {fmt(cardMon[card][cur])} |")
    L.append(f"| \u0e08\u0e33\u0e19\u0e27\u0e19\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23 | {sum(1 for t in tx if t['m'] == cur):,} |")
    L.append("")

    # ---- category comparison ----
    L.append("## \u0e41\u0e22\u0e01\u0e15\u0e32\u0e21\u0e1b\u0e23\u0e30\u0e40\u0e20\u0e17 \u0e40\u0e17\u0e35\u0e22\u0e1a\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19")
    L.append("")
    L.append("| \u0e1b\u0e23\u0e30\u0e40\u0e20\u0e17 | \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49 | \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19 | \u0e40\u0e1b\u0e25\u0e35\u0e48\u0e22\u0e19\u0e41\u0e1b\u0e25\u0e07 |")
    L.append("|---|--:|--:|--:|")
    cats = sorted(catMon.keys(), key=lambda c: -catMon[c].get(cur, 0))
    for c in cats:
        a = catMon[c].get(cur, 0)
        b = catMon[c].get(prev, 0) if prev else 0
        if a == 0 and b == 0: continue
        cp = pct(a, b)
        ch = f"{arrow(cp)} {cp:+.0f}%" if cp is not None else ("\u0e43\u0e2b\u0e21\u0e48" if a > 0 else "\u2013")
        L.append(f"| {TH[c]} | {fmt(a)} | {fmt(b) if b else '\u2013'} | {ch} |")
    L.append("")

    # ---- top merchants this month ----
    L.append("## Top 10 \u0e23\u0e49\u0e32\u0e19\u0e04\u0e49\u0e32\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49")
    L.append("")
    L.append("| # | \u0e23\u0e49\u0e32\u0e19\u0e04\u0e49\u0e32 | \u0e04\u0e23\u0e31\u0e49\u0e07 | \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49 | \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19 |")
    L.append("|--:|---|--:|--:|--:|")
    tops = sorted(merchMon.items(), key=lambda kv: -kv[1].get(cur, 0))[:10]
    for i, (name, d) in enumerate(tops, 1):
        if d.get(cur, 0) <= 0: continue
        b = d.get(prev, 0) if prev else 0
        L.append(f"| {i} | {name} | {merchN[name].get(cur,0)} | {fmt(d[cur])} | {fmt(b) if b else '\u2013'} |")
    L.append("")

    # ---- anomaly flags ----
    flags = []
    # 1. total spend jump
    if p is not None and abs(p) >= 30:
        flags.append(f"\u0e22\u0e2d\u0e14\u0e23\u0e27\u0e21\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49 {arrow(p)} **{p:+.0f}%** \u0e08\u0e32\u0e01\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19 ({fmt(prevTot)} \u2192 {fmt(curTot)})")
    # 2. category spikes vs trailing average
    if base:
        for c in cats:
            a = catMon[c].get(cur, 0)
            av = avg_of(catMon[c], base)
            if av > 500 and a > av * 1.5:
                flags.append(f"\u0e2b\u0e21\u0e27\u0e14 **{TH[c]}** \u0e2a\u0e39\u0e07\u0e01\u0e27\u0e48\u0e32\u0e04\u0e48\u0e32\u0e40\u0e09\u0e25\u0e35\u0e48\u0e22 {a/av*100-100:+.0f}% ({fmt(av)} \u2192 {fmt(a)})")
    # 3. big new merchants
    for name, d in merchMon.items():
        if d.get(cur, 0) >= 3000 and not any(d.get(m, 0) > 0 for m in months[:-1]):
            flags.append(f"\u0e23\u0e49\u0e32\u0e19\u0e43\u0e2b\u0e21\u0e48\u0e22\u0e2d\u0e14\u0e43\u0e2b\u0e0d\u0e48: **{name}** {fmt(d[cur])}")
    # 4. recurring merchant disappeared
    if prev and len(months) >= 4:
        recent3 = months[-4:-1]
        for name, d in merchMon.items():
            if all(d.get(m, 0) > 0 for m in recent3) and d.get(cur, 0) == 0:
                avg3 = sum(d.get(m, 0) for m in recent3) / 3
                if avg3 >= 300:
                    flags.append(f"\u0e23\u0e49\u0e32\u0e19\u0e1b\u0e23\u0e30\u0e08\u0e33\u0e2b\u0e32\u0e22\u0e44\u0e1b: **{name}** (\u0e40\u0e04\u0e22\u0e08\u0e48\u0e32\u0e22\u0e40\u0e09\u0e25\u0e35\u0e48\u0e22 {fmt(avg3)}/\u0e40\u0e14\u0e37\u0e2d\u0e19) \u2014 \u0e40\u0e0a\u0e47\u0e04\u0e27\u0e48\u0e32\u0e15\u0e01\u0e2b\u0e25\u0e48\u0e19\u0e2b\u0e23\u0e37\u0e2d\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01\u0e44\u0e1b\u0e41\u0e25\u0e49\u0e27")
    # 5. duplicate spike warning
    if P['meta']['dupRemoved'] > 200:
        flags.append(f"\u26a0\ufe0f \u0e15\u0e31\u0e14\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e0b\u0e49\u0e33\u0e2d\u0e2d\u0e01 {P['meta']['dupRemoved']} \u0e23\u0e32\u0e22\u0e01\u0e32\u0e23 \u2014 \u0e2a\u0e39\u0e07\u0e1c\u0e34\u0e14\u0e1b\u0e01\u0e15\u0e34 \u0e2d\u0e32\u0e08\u0e21\u0e35\u0e44\u0e1f\u0e25\u0e4c statement \u0e0b\u0e49\u0e33\u0e43\u0e19\u0e42\u0e1f\u0e25\u0e40\u0e14\u0e2d\u0e23\u0e4c")

    L.append("## \u0e08\u0e38\u0e14\u0e17\u0e35\u0e48\u0e04\u0e27\u0e23\u0e14\u0e39")
    L.append("")
    if flags:
        for f in flags: L.append(f"- {f}")
    else:
        L.append("- \u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e04\u0e27\u0e32\u0e21\u0e1c\u0e34\u0e14\u0e1b\u0e01\u0e15\u0e34 \u0e01\u0e32\u0e23\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22\u0e2d\u0e22\u0e39\u0e48\u0e43\u0e19\u0e23\u0e30\u0e14\u0e31\u0e1a\u0e1b\u0e01\u0e15\u0e34")
    L.append("")

    # ---- reducible group ----
    REDUCE = {'Food & Dining', 'Transport & Ride-hailing', 'Shopping & Retail',
              'Online Shopping', 'Subscriptions & Digital', 'Other'}
    rcur = sum(catMon[c].get(cur, 0) for c in catMon if c in REDUCE)
    rprev = sum(catMon[c].get(prev, 0) for c in catMon if c in REDUCE) if prev else 0
    rp = pct(rcur, rprev)
    L.append("## \u0e01\u0e25\u0e38\u0e48\u0e21\u0e17\u0e35\u0e48\u0e1b\u0e23\u0e31\u0e1a\u0e25\u0e14\u0e44\u0e14\u0e49")
    L.append("")
    L.append(f"- \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49: **{fmt(rcur)}** ({rcur/max(curTot,1)*100:.0f}% \u0e02\u0e2d\u0e07\u0e22\u0e2d\u0e14\u0e23\u0e27\u0e21)")
    if rp is not None:
        L.append(f"- \u0e40\u0e17\u0e35\u0e22\u0e1a\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19: {fmt(rprev)} \u00b7 {arrow(rp)} {rp:+.0f}%")
    L.append(f"- \u0e16\u0e49\u0e32\u0e25\u0e14\u0e44\u0e14\u0e49 15% \u0e08\u0e30\u0e1b\u0e23\u0e30\u0e2b\u0e22\u0e31\u0e14 **{fmt(rcur*0.15)}**")
    L.append("")

    L.append("---")
    L.append(f"> \u0e1b\u0e23\u0e30\u0e21\u0e27\u0e25\u0e1c\u0e25\u0e08\u0e32\u0e01 {P['meta']['files']} \u0e44\u0e1f\u0e25\u0e4c \u00b7 \u0e15\u0e31\u0e14\u0e0b\u0e49\u0e33 {P['meta']['dupRemoved']} \u00b7 \u0e04\u0e39\u0e48 reverse {P['meta']['pairsRemoved']} \u00b7 \u0e04\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d {P['meta']['expenses']:,} \u0e23\u0e32\u0e22\u0e01\u0e32\u0e23")

    with open(out, 'w', encoding='utf-8') as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")



def write_single_html(P):
    """Generate a self-contained single-file dashboard.

    Inlines Chart.js and the CCDATA payload into a copy of index.html so the
    result opens standalone (no data.js, no zip, no internet). This is a
    read-only view export; the source index.html / data.js stay separate per
    the project rule (do not embed data back into index.html).
    """
    src_html = os.path.join(_HERE, "index.html")
    if not os.path.isfile(src_html):
        print("skip dashboard.html: index.html not found")
        return
    html = open(src_html, encoding='utf-8').read()

    def guard(s):
        # neutralize any literal </script> inside inlined code/data
        return s.replace("</script", "<\\/script")

    # 1) inline the exact data payload as window.CCDATA (same as data.js)
    data_js = "window.CCDATA = " + json.dumps(P, ensure_ascii=False) + ";\n"
    data_tag = "<script>\n" + guard(data_js) + "</script>"
    html = html.replace('<script src="data.js"></script>', data_tag)
    html = html.replace('<script src="__claude__data.js"></script>', '')

    # 2) inline Chart.js from the vendored copy so charts work offline;
    #    if it's missing, leave the CDN tag (charts then need internet).
    cdn = '<script src="vendor/chart.umd.js"></script>'
    if os.path.isfile(VENDOR_CHARTJS):
        chart_src = open(VENDOR_CHARTJS, encoding='utf-8').read()
        html = html.replace(cdn, "<script>\n" + guard(chart_src) + "\n</script>")
    else:
        print(f"note: {VENDOR_CHARTJS} not found -> dashboard.html keeps Chart.js CDN (needs internet)")

    # 2b) drop the sample-data tag (real data is inlined above and overrides it)
    html = html.replace('<script src="data.sample.js"></script>', '')

    # 2c) inline the recurring-rule hook so the offline file respects a custom rule;
    #     if the hook is absent, drop the tag (index.html falls back to its default).
    hook = os.path.join(_HERE, "recurring_rule.js")
    hook_tag = '<script src="recurring_rule.js"></script>'
    if os.path.isfile(hook):
        html = html.replace(hook_tag, "<script>\n" + guard(open(hook, encoding='utf-8').read()) + "\n</script>")
    else:
        html = html.replace(hook_tag, '')

    # inline the web fonts (base64) so the single file works fully offline
    import base64, glob as _glob
    fdir = os.path.join(_HERE, 'vendor', 'fonts')
    faces = []
    for fp in sorted(_glob.glob(os.path.join(fdir, 'ibmplex-*.woff2'))):
        name = os.path.basename(fp)
        parts = name.replace('.woff2','').split('-')  # ibmplex, <sub>, <weight>
        sub, wt = parts[1], parts[2]
        rng = 'unicode-range:U+0E01-0E5B,U+200C-200D,U+25CC,U+25CD;' if sub=='thai' else ''
        b64 = base64.b64encode(open(fp,'rb').read()).decode()
        faces.append("@font-face{font-family:'IBM Plex Sans Thai';font-weight:"+wt+";src:url(data:font/woff2;base64,"+b64+") format('woff2');"+rng+"font-display:swap;}")
    if faces:
        html = re.sub(r'<style id="app-fonts">.*?</style>', '<style id="app-fonts">'+''.join(faces)+'</style>', html, count=1, flags=re.DOTALL)

    with open(OUT_HTML, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f"wrote {OUT_HTML}  ({os.path.getsize(OUT_HTML):,} bytes)")


if __name__ == '__main__':
    build()
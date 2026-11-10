"""Builds assets/contribution-graph.svg from a user's public GitHub contribution calendar."""
import os, re, sys, html, datetime as dt, urllib.request

USER = os.environ.get("GH_USER", "IT21279584")
OUT = os.environ.get("OUT_FILE", "assets/contribution-graph.svg")

def fetch(user):
    if len(sys.argv) > 1:                      # local test: pass a saved HTML file
        return open(sys.argv[1], encoding="utf-8").read()
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": "contribution-graph-script"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

def parse(page):
    counts = {}
    for m in re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        t = m.group(2).strip()
        n = re.match(r'(\d[\d,]*|No) contributions?', t)
        if n:
            counts[m.group(1)] = 0 if n.group(1) == "No" else int(n.group(1).replace(",", ""))
    days = []
    for m in re.finditer(r'<td\b[^>]*>', page):
        tag = m.group(0)
        d = re.search(r'data-date="([\d-]+)"', tag)
        i = re.search(r'\bid="(contribution-day-component-(\d+)-(\d+))"', tag)
        lv = re.search(r'data-level="(\d)"', tag)
        if d and i and lv:
            days.append({"date": dt.date.fromisoformat(d.group(1)), "row": int(i.group(2)),
                         "col": int(i.group(3)), "level": int(lv.group(1)),
                         "count": counts.get(i.group(1), 0)})
    if not days:
        sys.exit("No contribution data found - GitHub may have changed its page layout.")
    return sorted(days, key=lambda x: x["date"])

def stats(days):
    total = sum(d["count"] for d in days)
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    current = 0
    seq = list(reversed(days))
    if seq and seq[0]["count"] == 0:         # today may not have contributions yet
        seq = seq[1:]
    for d in seq:
        if d["count"] == 0: break
        current += 1
    best = max(days, key=lambda x: x["count"])
    return total, current, longest, best

def fmt(n): return f"{n:,}"

def day(d): return f"{d:%b} {d.day}, {d.year}"

def build(days):
    total, current, longest, best = stats(days)
    start, end = days[0]["date"], days[-1]["date"]
    cols = max(d["col"] for d in days) + 1
    CELL, STEP, GX, GY = 11, 14, 62, 178
    W = GX + cols * STEP + 34
    H = GY + 7 * STEP + 40
    colors = ["#1a2335", "#0c4a6e", "#0369a1", "#0ea5e9", "#67e8f9"]

    cells = []
    for d in days:
        x, y = GX + d["col"] * STEP, GY + d["row"] * STEP
        delay = d["col"] * 0.025 + d["row"] * 0.01
        glow = ' filter="url(#cellglow)"' if d["level"] == 4 else ""
        tip = f'{d["count"]} contribution{"s" if d["count"] != 1 else ""} on {day(d["date"])}'
        cells.append(f'<rect class="c" style="animation-delay:{delay:.2f}s" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{colors[d["level"]]}"{glow}><title>{tip}</title></rect>')
    last = days[-1]
    lx, ly = GX + last["col"] * STEP + CELL / 2, GY + last["row"] * STEP + CELL / 2
    today = (f'<circle cx="{lx}" cy="{ly}" r="6" fill="none" stroke="#67e8f9" stroke-width="1.5">'
             f'<animate attributeName="r" values="6;11;6" dur="2.2s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="0.9;0;0.9" dur="2.2s" repeatCount="indefinite"/></circle>')

    months, prev_m, prev_col = [], None, -9
    for c in range(cols):
        col_days = [d for d in days if d["col"] == c]
        m = min(col_days, key=lambda d: d["row"])["date"].month if col_days else None
        if m != prev_m and c - prev_col >= 3:
            months.append(f'<text x="{GX + c * STEP}" y="{GY - 9}" class="axis">{dt.date(2000, m, 1):%b}</text>')
            prev_col = c
        prev_m = m
    wdays = "".join(f'<text x="{GX - 10}" y="{GY + r * STEP + 9}" class="axis" text-anchor="end">{n}</text>'
                    for r, n in [(1, "Mon"), (3, "Wed"), (5, "Fri")])

    chips_data = [
        ("TOTAL", fmt(total), "contributions this year", "#67e8f9"),
        ("CURRENT STREAK", f"{current} day{'s' if current != 1 else ''}", "keep it going", "#4ade80"),
        ("LONGEST STREAK", f"{longest} day{'s' if longest != 1 else ''}", "personal best", "#fbbf24"),
        ("BEST DAY", fmt(best["count"]), day(best["date"]), "#f472b6"),
    ]
    cw = (W - 64 - 3 * 14) / 4
    chips = []
    for i, (label, val, sub, col) in enumerate(chips_data):
        x = 32 + i * (cw + 14)
        chips.append(f'''<g class="chip" style="animation-delay:{0.15 + i * 0.12:.2f}s">
      <rect x="{x:.1f}" y="74" width="{cw:.1f}" height="66" rx="12" fill="#0f172a" fill-opacity="0.75" stroke="#1e293b"/>
      <rect x="{x:.1f}" y="86" width="3" height="42" rx="1.5" fill="{col}"/>
      <text x="{x + 16:.1f}" y="94" class="label">{label}</text>
      <text x="{x + 16:.1f}" y="118" class="value" fill="{col}">{html.escape(val)}</text>
      <text x="{x + 16:.1f}" y="132" class="sub">{html.escape(sub)}</text>
    </g>''')

    legend_x = W - 32 - 5 * 15 - 64
    legend = (f'<text x="{legend_x}" y="45" class="axis">Less</text>' +
              "".join(f'<rect x="{legend_x + 30 + i * 15}" y="36" width="11" height="11" rx="3" fill="{c}"/>' for i, c in enumerate(colors)) +
              f'<text x="{legend_x + 30 + 5 * 15 + 4}" y="45" class="axis">More</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1222"/><stop offset="1" stop-color="#111a33"/></linearGradient>
    <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="45"/></filter>
    <filter id="cellglow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
    <style>
      .title {{ font: 700 19px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; fill: #f1f5f9; }}
      .subtitle {{ font: 500 11px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; fill: #64748b; }}
      .label {{ font: 700 9px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; fill: #94a3b8; letter-spacing: 0.8px; }}
      .value {{ font: 800 19px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; }}
      .sub {{ font: 500 9.5px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; fill: #64748b; }}
      .axis {{ font: 500 10px 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; fill: #64748b; }}
      .c {{ animation: pop 0.5s ease-out backwards; transform-box: fill-box; transform-origin: center; }}
      .chip {{ animation: rise 0.6s ease-out backwards; }}
      @keyframes pop {{ from {{ opacity: 0; transform: scale(0.3); }} to {{ opacity: 1; transform: scale(1); }} }}
      @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    </style>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <circle cx="{W - 80}" cy="20" r="120" fill="#06b6d4" opacity="0.22" filter="url(#blur)"/>
    <circle cx="60" cy="{H}" r="130" fill="#7c3aed" opacity="0.2" filter="url(#blur)"/>
    <text x="32" y="42" class="title">Contribution Activity</text>
    <text x="32" y="60" class="subtitle">{day(start)} – {day(end)}</text>
    {legend}
    {"".join(chips)}
    {"".join(months)}
    {wdays}
    {"".join(cells)}
    {today}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="#1e293b"/>
</svg>
'''

if __name__ == "__main__":
    days = parse(fetch(USER))
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(build(days))
    t, c, l, b = stats(days)
    print(f"Wrote {OUT}: {len(days)} days, {t} contributions, current streak {c}, longest {l}, best day {b['count']} on {b['date']}")

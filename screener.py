"""
European Stock EOD Screener
Datenquelle: stooq.com (kein API-Key, funktioniert von GitHub Actions)
Output: docs/index.html (via GitHub Pages)
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import time
import requests
import io

# ─────────────────────────────────────────────
# Ticker-Mapping: Yahoo-Suffix → stooq-Suffix
# stooq verwendet Länder-Domains statt Börsen-Suffixe
# ─────────────────────────────────────────────
SUFFIX_MAP = {
    ".DE": ".de",   # XETRA → Deutschland
    ".PA": ".fr",   # Paris → Frankreich
    ".SW": ".sw",   # SIX Zürich
    ".L":  ".uk",   # London
    ".AS": ".nl",   # Amsterdam → Niederlande
    ".MC": ".es",   # Madrid → Spanien
    ".MI": ".it",   # Mailand → Italien
    ".ST": ".se",   # Stockholm → Schweden
    ".CO": ".dk",   # Kopenhagen → Dänemark
    ".OL": ".no",   # Oslo → Norwegen
    ".HE": ".fi",   # Helsinki → Finnland
    ".BR": ".be",   # Brüssel → Belgien
    ".VI": ".at",   # Wien → Österreich
}

EXCHANGE_MAP = {
    ".DE": "XETRA",     ".PA": "Paris",    ".SW": "Zürich",
    ".L":  "London",    ".AS": "Amsterdam",".MC": "Madrid",
    ".MI": "Mailand",   ".ST": "Stockholm",".CO": "Kopenhagen",
    ".OL": "Oslo",      ".HE": "Helsinki", ".BR": "Brüssel",
    ".VI": "Wien",
}

CURRENCY_MAP = {
    "London": "GBp", "Zürich": "CHF", "Stockholm": "SEK",
    "Oslo": "NOK", "Kopenhagen": "DKK",
}

# ─────────────────────────────────────────────
# Aktienliste
# ─────────────────────────────────────────────
EUROPEAN_TICKERS = [
    # Deutschland
    "SAP.DE","SIE.DE","ALV.DE","MRK.DE","DTE.DE","BAYN.DE","BMW.DE",
    "MBG.DE","VOW3.DE","BAS.DE","RWE.DE","EON.DE","DBK.DE","CBK.DE",
    "ADS.DE","IFX.DE","HEN3.DE","MUV2.DE","MTX.DE",
    # Frankreich
    "MC.PA","OR.PA","TTE.PA","SAN.PA","AIR.PA","BNP.PA","AXA.PA",
    "SU.PA","RI.PA","SGO.PA","KER.PA","STM.PA","VIV.PA","ENGI.PA",
    "LR.PA","RNO.PA","ORA.PA",
    # Schweiz
    "NESN.SW","NOVN.SW","ZURN.SW","SIKA.SW","LONN.SW","CFR.SW","HOLN.SW",
    # UK
    "HSBA.L","SHEL.L","AZN.L","ULVR.L","BP.L","GSK.L","RIO.L",
    "VOD.L","REL.L","NG.L","BARC.L","LLOY.L","NWG.L","PRU.L",
    # Niederlande
    "ASML.AS","HEIA.AS","PHIA.AS","ING.AS","AD.AS",
    # Spanien
    "ITX.MC","BBVA.MC","SAN.MC","IBE.MC","REP.MC","TEF.MC",
    # Italien
    "ENI.MI","ENEL.MI","UCG.MI","RACE.MI",
    # Schweden
    "VOLV-B.ST","ERIC-B.ST","HM-B.ST","SAND.ST",
    # Dänemark
    "NOVO-B.CO","DSV.CO",
    # Norwegen
    "EQNR.OL","DNB.OL",
    # Finnland
    "NOKIA.HE",
    # Belgien
    "UCB.BR","ABI.BR",
    # Österreich
    "OMV.VI","ERSTE.VI",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ─────────────────────────────────────────────
# Daten laden via stooq.com
# ─────────────────────────────────────────────
def yahoo_to_stooq(ticker):
    """Konvertiert Yahoo-Ticker-Format zu stooq-Format."""
    for yf_suffix, stooq_suffix in SUFFIX_MAP.items():
        if ticker.endswith(yf_suffix):
            base = ticker[:-len(yf_suffix)].lower().replace("-", "_")
            return base + stooq_suffix
    return ticker.lower()


def fetch_ticker(session, ticker, d1, d2):
    """Lädt Tagesdaten von stooq.com als CSV."""
    stooq_ticker = yahoo_to_stooq(ticker)
    url = "https://stooq.com/q/d/l/"
    params = {
        "s":  stooq_ticker,
        "d1": d1,
        "d2": d2,
        "i":  "d",
    }
    try:
        r = session.get(url, params=params, timeout=10, headers=HEADERS)
        if r.status_code != 200 or len(r.content) < 50:
            return None
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        return df
    except Exception:
        return None


def fetch_data(tickers):
    end   = datetime.today()
    start = end - timedelta(days=40)
    d1    = start.strftime("%Y%m%d")
    d2    = end.strftime("%Y%m%d")

    print(f"Lade {len(tickers)} Aktien von stooq.com...")
    session = requests.Session()
    results = {}
    skipped = 0

    for i, ticker in enumerate(tickers):
        df = fetch_ticker(session, ticker, d1, d2)
        if df is not None and len(df) >= 2:
            results[ticker] = df
        else:
            skipped += 1
        # Kurze Pause alle 15 Ticker
        if (i + 1) % 15 == 0:
            time.sleep(1)

    print(f"  ✅ {len(results)} geladen, {skipped} übersprungen")
    return results


# ─────────────────────────────────────────────
# Screener aufbauen
# ─────────────────────────────────────────────
def build_screener(ticker_data, tickers):
    records = []

    for ticker in tickers:
        try:
            df = ticker_data.get(ticker)
            if df is None or len(df) < 2:
                continue

            close  = df["Close"]
            volume = df["Volume"] if "Volume" in df.columns else pd.Series([0]*len(df))
            high   = df["High"]   if "High"   in df.columns else close

            today_close  = float(close.iloc[-1])
            prev_close   = float(close.iloc[-2])
            today_volume = float(volume.iloc[-1])
            avg_vol_20   = float(volume.iloc[-21:-1].mean()) if len(volume) >= 21 else float(volume.mean())
            pct_change   = (today_close - prev_close) / prev_close * 100
            vol_ratio    = today_volume / avg_vol_20 if avg_vol_20 > 0 else 1.0
            high_30d     = float(high.max())

            # Exchange & Currency
            exchange = "–"
            for suffix, exch in EXCHANGE_MAP.items():
                if ticker.endswith(suffix):
                    exchange = exch
                    break
            currency = CURRENCY_MAP.get(exchange, "EUR")

            # Anzeigename (Suffix entfernen)
            name = ticker
            for suffix in EXCHANGE_MAP:
                name = name.replace(suffix, "")

            records.append({
                "ticker":     ticker,
                "name":       name,
                "exchange":   exchange,
                "currency":   currency,
                "close":      round(today_close, 2),
                "prev_close": round(prev_close, 2),
                "pct_change": round(pct_change, 2),
                "volume":     int(today_volume),
                "vol_ratio":  round(vol_ratio, 2),
                "high_30d":   round(high_30d, 2),
            })
        except Exception as e:
            print(f"  Fehler {ticker}: {e}")
            continue

    df_out = pd.DataFrame(records)
    if df_out.empty:
        raise ValueError("Keine Daten verarbeitbar.")
    return df_out.sort_values("pct_change", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# HTML generieren
# ─────────────────────────────────────────────
def rows_html(subset):
    html = ""
    for _, row in subset.iterrows():
        pct = row["pct_change"]
        color_class = "pos" if pct >= 0 else "neg"
        arrow = "▲" if pct >= 0 else "▼"
        vol_badge = ""
        if row["vol_ratio"] >= 3:
            vol_badge = '<span class="badge badge-hot">🔥 Hoch</span>'
        elif row["vol_ratio"] >= 2:
            vol_badge = '<span class="badge badge-watch">↑ Erhöht</span>'

        html += f"""
        <tr>
            <td><span class="ticker-tag">{row['ticker']}</span></td>
            <td class="name-cell">{row['name']}</td>
            <td><span class="exchange-badge">{row['exchange']}</span></td>
            <td class="num">{row['close']:.2f} <span class="currency">{row['currency']}</span></td>
            <td class="num {color_class} bold">{arrow} {abs(pct):.2f}%</td>
            <td class="num">{row['vol_ratio']:.1f}x {vol_badge}</td>
        </tr>"""
    return html


def generate_html(df, date_str, generated_at):
    gainers         = df[df["pct_change"] > 0].head(20)
    losers          = df[df["pct_change"] < 0].sort_values("pct_change").head(20)
    volume_outliers = df[df["vol_ratio"] > 2.0].sort_values("vol_ratio", ascending=False).head(20)
    market_avg      = df["pct_change"].mean()
    positive_count  = len(df[df["pct_change"] > 0])
    total_count     = len(df)
    top_gainer_name = df.loc[df["pct_change"].idxmax(), "name"]
    top_loser_name  = df.loc[df["pct_change"].idxmin(), "name"]

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>European EOD Screener – {date_str}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0a0c0f; --surface:#111318; --surface2:#171b22;
    --border:#1e2430; --border2:#252d3a;
    --text:#e2e8f0; --text-dim:#64748b; --text-muted:#334155;
    --green:#22c55e; --red:#ef4444; --blue:#3b82f6; --gold:#f59e0b;
    --font-d:'Syne',sans-serif; --font-m:'Space Mono',monospace;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--bg);color:var(--text);font-family:var(--font-m);font-size:13px;min-height:100vh}}
  .header{{background:linear-gradient(135deg,#0f1420,#0a0c0f);border-bottom:1px solid var(--border);padding:32px 40px 28px;position:relative;overflow:hidden}}
  .header::before{{content:'';position:absolute;top:-80px;right:-80px;width:300px;height:300px;background:radial-gradient(circle,rgba(59,130,246,.08),transparent 70%);pointer-events:none}}
  .header-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px}}
  .brand{{display:flex;align-items:center;gap:12px}}
  .brand-icon{{width:42px;height:42px;background:var(--blue);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px}}
  h1{{font-family:var(--font-d);font-size:22px;font-weight:800;letter-spacing:-.5px;color:#fff}}
  .subtitle{{font-size:11px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;margin-top:2px}}
  .date-badge{{background:var(--surface2);border:1px solid var(--border2);border-radius:6px;padding:8px 16px;font-size:12px;color:var(--text-dim);letter-spacing:1px}}
  .stats-bar{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 20px;position:relative;overflow:hidden}}
  .stat-card::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
  .stat-card.up::after{{background:var(--green)}} .stat-card.down::after{{background:var(--red)}}
  .stat-card.neutral::after{{background:var(--blue)}} .stat-card.volume::after{{background:var(--gold)}}
  .stat-label{{font-size:10px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}}
  .stat-value{{font-family:var(--font-d);font-size:28px;font-weight:800;line-height:1}}
  .stat-value.up{{color:var(--green)}} .stat-value.down{{color:var(--red)}}
  .stat-value.neutral{{color:var(--blue)}} .stat-value.volume{{color:var(--gold)}}
  .stat-sub{{font-size:10px;color:var(--text-muted);margin-top:4px}}
  .main{{padding:32px 40px}}
  .search-bar{{position:relative;margin-bottom:32px}}
  .search-bar input{{width:100%;max-width:400px;background:var(--surface);border:1px solid var(--border2);border-radius:8px;padding:10px 16px 10px 40px;color:var(--text);font-family:var(--font-m);font-size:13px;outline:none;transition:border-color .2s}}
  .search-bar input:focus{{border-color:var(--blue)}}
  .search-icon{{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--text-dim)}}
  .tabs{{display:flex;border-bottom:1px solid var(--border);margin-bottom:24px}}
  .tab{{padding:10px 24px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;font-family:var(--font-d);font-weight:600;font-size:13px;color:var(--text-dim);transition:all .2s;letter-spacing:.3px}}
  .tab:hover{{color:var(--text)}} .tab.active{{color:var(--text);border-bottom-color:var(--blue)}}
  .tab-panel{{display:none}} .tab-panel.active{{display:block}}
  .table-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}}
  .table-header{{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}}
  .table-title{{font-family:var(--font-d);font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px}}
  .count-badge{{background:var(--surface2);border:1px solid var(--border2);border-radius:20px;padding:2px 10px;font-size:11px;color:var(--text-dim)}}
  table{{width:100%;border-collapse:collapse}}
  thead th{{padding:10px 16px;text-align:left;font-size:10px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;background:var(--surface2);cursor:pointer;user-select:none;white-space:nowrap;transition:color .15s}}
  thead th:hover{{color:var(--text)}}
  tbody tr{{border-top:1px solid var(--border);transition:background .15s}}
  tbody tr:hover{{background:rgba(59,130,246,.04)}}
  td{{padding:11px 16px;vertical-align:middle}}
  .num{{text-align:right}} .bold{{font-weight:700}} .name-cell{{color:var(--text-dim);font-size:12px}}
  .pos{{color:var(--green)}} .neg{{color:var(--red)}}
  .ticker-tag{{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);color:var(--blue);border-radius:4px;padding:2px 8px;font-size:12px;white-space:nowrap}}
  .exchange-badge{{background:var(--surface2);border:1px solid var(--border2);border-radius:4px;padding:2px 8px;font-size:10px;color:var(--text-dim);white-space:nowrap}}
  .currency{{font-size:10px;color:var(--text-muted)}}
  .badge{{border-radius:4px;padding:1px 6px;font-size:10px;margin-left:6px}}
  .badge-hot{{background:rgba(239,68,68,.15);color:var(--red);border:1px solid rgba(239,68,68,.2)}}
  .badge-watch{{background:rgba(245,158,11,.12);color:var(--gold);border:1px solid rgba(245,158,11,.2)}}
  .footer{{padding:20px 40px;border-top:1px solid var(--border);color:var(--text-muted);font-size:11px;display:flex;justify-content:space-between;align-items:center}}
  @media(max-width:768px){{
    .header,.main{{padding:20px}} .stats-bar{{grid-template-columns:repeat(2,1fr)}}
    .footer{{flex-direction:column;gap:8px;text-align:center}}
  }}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <div class="brand">
      <div class="brand-icon">🇪🇺</div>
      <div>
        <h1>European EOD Screener</h1>
        <div class="subtitle">End of Day · Swing Trading</div>
      </div>
    </div>
    <div class="date-badge">📅 {date_str}</div>
  </div>
  <div class="stats-bar">
    <div class="stat-card up">
      <div class="stat-label">Top Gainer</div>
      <div class="stat-value up">+{df['pct_change'].max():.1f}%</div>
      <div class="stat-sub">{top_gainer_name}</div>
    </div>
    <div class="stat-card down">
      <div class="stat-label">Top Loser</div>
      <div class="stat-value down">{df['pct_change'].min():.1f}%</div>
      <div class="stat-sub">{top_loser_name}</div>
    </div>
    <div class="stat-card neutral">
      <div class="stat-label">Markt-Breite</div>
      <div class="stat-value neutral">{positive_count}/{total_count}</div>
      <div class="stat-sub">Aktien im Plus</div>
    </div>
    <div class="stat-card volume">
      <div class="stat-label">Ø Tagesveränderung</div>
      <div class="stat-value volume">{"+" if market_avg >= 0 else ""}{market_avg:.2f}%</div>
      <div class="stat-sub">{total_count} Aktien analysiert</div>
    </div>
  </div>
</div>
<div class="main">
  <div class="search-bar">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Aktie suchen… (Ticker oder Name)" oninput="filterTable()">
  </div>
  <div class="tabs">
    <div class="tab active"  onclick="showTab('gainers',event)">📈 Top Gainer</div>
    <div class="tab"         onclick="showTab('losers',event)">📉 Top Loser</div>
    <div class="tab"         onclick="showTab('volume',event)">🔥 Volumen-Anomalien</div>
    <div class="tab"         onclick="showTab('all',event)">📋 Alle Aktien</div>
  </div>
  <div id="tab-gainers" class="tab-panel active">
    <div class="table-wrap">
      <div class="table-header">
        <div class="table-title">📈 Top Gainer <span class="count-badge">{len(gainers)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Stärkste Aufwärtsbewegungen heute</div>
      </div>
      <table><thead><tr>
        <th onclick="sortTable(this)">Ticker</th><th onclick="sortTable(this)">Name</th>
        <th onclick="sortTable(this)">Börse</th><th onclick="sortTable(this)" style="text-align:right">Kurs</th>
        <th onclick="sortTable(this)" style="text-align:right">% Change</th>
        <th onclick="sortTable(this)" style="text-align:right">Vol. Ratio</th>
      </tr></thead><tbody>{rows_html(gainers)}</tbody></table>
    </div>
  </div>
  <div id="tab-losers" class="tab-panel">
    <div class="table-wrap">
      <div class="table-header">
        <div class="table-title">📉 Top Loser <span class="count-badge">{len(losers)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Stärkste Abwärtsbewegungen heute</div>
      </div>
      <table><thead><tr>
        <th onclick="sortTable(this)">Ticker</th><th onclick="sortTable(this)">Name</th>
        <th onclick="sortTable(this)">Börse</th><th onclick="sortTable(this)" style="text-align:right">Kurs</th>
        <th onclick="sortTable(this)" style="text-align:right">% Change</th>
        <th onclick="sortTable(this)" style="text-align:right">Vol. Ratio</th>
      </tr></thead><tbody>{rows_html(losers)}</tbody></table>
    </div>
  </div>
  <div id="tab-volume" class="tab-panel">
    <div class="table-wrap">
      <div class="table-header">
        <div class="table-title">🔥 Volumen-Anomalien <span class="count-badge">{len(volume_outliers)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Volumen &gt; 2× 20-Tage-Durchschnitt</div>
      </div>
      <table><thead><tr>
        <th onclick="sortTable(this)">Ticker</th><th onclick="sortTable(this)">Name</th>
        <th onclick="sortTable(this)">Börse</th><th onclick="sortTable(this)" style="text-align:right">Kurs</th>
        <th onclick="sortTable(this)" style="text-align:right">% Change</th>
        <th onclick="sortTable(this)" style="text-align:right">Vol. Ratio</th>
      </tr></thead><tbody>{rows_html(volume_outliers)}</tbody></table>
    </div>
  </div>
  <div id="tab-all" class="tab-panel">
    <div class="table-wrap">
      <div class="table-header">
        <div class="table-title">📋 Alle Aktien <span class="count-badge">{total_count}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Sortierbar per Klick · nach % Change</div>
      </div>
      <table><thead><tr>
        <th onclick="sortTable(this)">Ticker</th><th onclick="sortTable(this)">Name</th>
        <th onclick="sortTable(this)">Börse</th><th onclick="sortTable(this)" style="text-align:right">Kurs</th>
        <th onclick="sortTable(this)" style="text-align:right">% Change</th>
        <th onclick="sortTable(this)" style="text-align:right">Vol. Ratio</th>
      </tr></thead><tbody id="all-body">{rows_html(df)}</tbody></table>
    </div>
  </div>
</div>
<div class="footer">
  <div>Daten: stooq.com · Kein Anlageberatungsersatz · Nur zur Information</div>
  <div>Automatisch generiert am {generated_at}</div>
</div>
<script>
function showTab(name,e){{
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  e.target.classList.add('active');
}}
function filterTable(){{
  const q=document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('.tab-panel tbody tr').forEach(row=>{{
    row.style.display=row.textContent.toLowerCase().includes(q)?'':'none';
  }});
}}
function sortTable(th){{
  const table=th.closest('table');
  const tbody=table.querySelector('tbody');
  const idx=[...th.parentElement.children].indexOf(th);
  const asc=th.dataset.sort!=='asc';
  th.parentElement.querySelectorAll('th').forEach(t=>delete t.dataset.sort);
  th.dataset.sort=asc?'asc':'desc';
  const rows=[...tbody.querySelectorAll('tr')];
  rows.sort((a,b)=>{{
    const av=a.cells[idx].textContent.replace(/[^0-9.\-]/g,'')||a.cells[idx].textContent;
    const bv=b.cells[idx].textContent.replace(/[^0-9.\-]/g,'')||b.cells[idx].textContent;
    const an=parseFloat(av),bn=parseFloat(bv);
    if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
    return asc?av.localeCompare(bv):bv.localeCompare(av);
  }});
  rows.forEach(r=>tbody.appendChild(r));
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    date_str     = datetime.today().strftime("%d.%m.%Y")
    generated_at = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr (UTC)")

    ticker_data = fetch_data(EUROPEAN_TICKERS)
    df          = build_screener(ticker_data, EUROPEAN_TICKERS)

    print(f"✅ {len(df)} Aktien verarbeitet")
    print(f"📈 Top Gainer: {df.iloc[0]['ticker']} (+{df.iloc[0]['pct_change']:.2f}%)")
    print(f"📉 Top Loser:  {df.iloc[-1]['ticker']} ({df.iloc[-1]['pct_change']:.2f}%)")

    os.makedirs("docs", exist_ok=True)
    html = generate_html(df, date_str, generated_at)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"💾 Dashboard gespeichert: docs/index.html")

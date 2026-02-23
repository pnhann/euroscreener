"""
European Stock EOD Screener v3
Datenquelle: stooq.com
Features: Unternehmensname, Land, Sektor, Filter, modernes Finance-UI
"""

import pandas as pd
from datetime import datetime, timedelta
import os, time, requests, io

# ─────────────────────────────────────────────
# STAMMDATEN: Ticker → (Name, Land, Sektor, stooq-Ticker)
# ─────────────────────────────────────────────
STOCKS = {
    # Deutschland
    "SAP.DE":    ("SAP SE",                      "Deutschland", "Technologie",   "sap.de"),
    "SIE.DE":    ("Siemens AG",                  "Deutschland", "Industrie",     "sie.de"),
    "ALV.DE":    ("Allianz SE",                  "Deutschland", "Finanzen",      "alv.de"),
    "MRK.DE":    ("Merck KGaA",                  "Deutschland", "Gesundheit",    "mrk.de"),
    "DTE.DE":    ("Deutsche Telekom AG",          "Deutschland", "Telekommunikation","dte.de"),
    "BAYN.DE":   ("Bayer AG",                    "Deutschland", "Gesundheit",    "bayn.de"),
    "BMW.DE":    ("BMW AG",                      "Deutschland", "Automobil",     "bmw.de"),
    "MBG.DE":    ("Mercedes-Benz Group AG",      "Deutschland", "Automobil",     "mbg.de"),
    "VOW3.DE":   ("Volkswagen AG",               "Deutschland", "Automobil",     "vow3.de"),
    "BAS.DE":    ("BASF SE",                     "Deutschland", "Chemie",        "bas.de"),
    "RWE.DE":    ("RWE AG",                      "Deutschland", "Energie",       "rwe.de"),
    "EON.DE":    ("E.ON SE",                     "Deutschland", "Energie",       "eon.de"),
    "DBK.DE":    ("Deutsche Bank AG",            "Deutschland", "Finanzen",      "dbk.de"),
    "CBK.DE":    ("Commerzbank AG",              "Deutschland", "Finanzen",      "cbk.de"),
    "ADS.DE":    ("Adidas AG",                   "Deutschland", "Konsumgüter",   "ads.de"),
    "IFX.DE":    ("Infineon Technologies AG",    "Deutschland", "Technologie",   "ifx.de"),
    "HEN3.DE":   ("Henkel AG & Co. KGaA",        "Deutschland", "Konsumgüter",   "hen3.de"),
    "MUV2.DE":   ("Munich Re AG",                "Deutschland", "Finanzen",      "muv2.de"),
    "MTX.DE":    ("MTU Aero Engines AG",         "Deutschland", "Industrie",     "mtx.de"),
    # Frankreich
    "MC.PA":     ("LVMH Moët Hennessy",          "Frankreich",  "Konsumgüter",   "mc.fr"),
    "OR.PA":     ("L'Oréal SA",                  "Frankreich",  "Konsumgüter",   "or.fr"),
    "TTE.PA":    ("TotalEnergies SE",            "Frankreich",  "Energie",       "tte.fr"),
    "SAN.PA":    ("Sanofi SA",                   "Frankreich",  "Gesundheit",    "san.fr"),
    "AIR.PA":    ("Airbus SE",                   "Frankreich",  "Industrie",     "air.fr"),
    "BNP.PA":    ("BNP Paribas SA",              "Frankreich",  "Finanzen",      "bnp.fr"),
    "AXA.PA":    ("AXA SA",                      "Frankreich",  "Finanzen",      "axa.fr"),
    "SU.PA":     ("Schneider Electric SE",       "Frankreich",  "Industrie",     "su.fr"),
    "RI.PA":     ("Pernod Ricard SA",            "Frankreich",  "Konsumgüter",   "ri.fr"),
    "SGO.PA":    ("Compagnie de Saint-Gobain",   "Frankreich",  "Industrie",     "sgo.fr"),
    "KER.PA":    ("Kering SA",                   "Frankreich",  "Konsumgüter",   "ker.fr"),
    "STM.PA":    ("STMicroelectronics NV",       "Frankreich",  "Technologie",   "stm.fr"),
    "VIV.PA":    ("Vivendi SE",                  "Frankreich",  "Telekommunikation","viv.fr"),
    "ENGI.PA":   ("Engie SA",                    "Frankreich",  "Energie",       "engi.fr"),
    "LR.PA":     ("Legrand SA",                  "Frankreich",  "Industrie",     "lr.fr"),
    "RNO.PA":    ("Renault SA",                  "Frankreich",  "Automobil",     "rno.fr"),
    "ORA.PA":    ("Orange SA",                   "Frankreich",  "Telekommunikation","ora.fr"),
    # Schweiz (stooq: .ch)
    "NESN.SW":   ("Nestlé SA",                   "Schweiz",     "Konsumgüter",   "nesn.ch"),
    "NOVN.SW":   ("Novartis AG",                 "Schweiz",     "Gesundheit",    "novn.ch"),
    "ZURN.SW":   ("Zurich Insurance Group AG",   "Schweiz",     "Finanzen",      "zurn.ch"),
    "SIKA.SW":   ("Sika AG",                     "Schweiz",     "Chemie",        "sika.ch"),
    "LONN.SW":   ("Lonza Group AG",              "Schweiz",     "Gesundheit",    "lonn.ch"),
    "CFR.SW":    ("Compagnie Financière Richemont","Schweiz",   "Konsumgüter",   "cfr.ch"),
    "HOLN.SW":   ("Holcim Ltd",                  "Schweiz",     "Industrie",     "holn.ch"),
    # UK (stooq: .uk)
    "HSBA.L":    ("HSBC Holdings plc",           "UK",          "Finanzen",      "hsba.uk"),
    "SHEL.L":    ("Shell plc",                   "UK",          "Energie",       "shel.uk"),
    "AZN.L":     ("AstraZeneca plc",             "UK",          "Gesundheit",    "azn.uk"),
    "ULVR.L":    ("Unilever plc",                "UK",          "Konsumgüter",   "ulvr.uk"),
    "BP.L":      ("BP plc",                      "UK",          "Energie",       "bp.uk"),
    "GSK.L":     ("GSK plc",                     "UK",          "Gesundheit",    "gsk.uk"),
    "RIO.L":     ("Rio Tinto plc",               "UK",          "Rohstoffe",     "rio.uk"),
    "VOD.L":     ("Vodafone Group plc",          "UK",          "Telekommunikation","vod.uk"),
    "REL.L":     ("RELX plc",                    "UK",          "Technologie",   "rel.uk"),
    "NG.L":      ("National Grid plc",           "UK",          "Energie",       "ng.uk"),
    "BARC.L":    ("Barclays plc",                "UK",          "Finanzen",      "barc.uk"),
    "LLOY.L":    ("Lloyds Banking Group plc",    "UK",          "Finanzen",      "lloy.uk"),
    "NWG.L":     ("NatWest Group plc",           "UK",          "Finanzen",      "nwg.uk"),
    "PRU.L":     ("Prudential plc",              "UK",          "Finanzen",      "pru.uk"),
    # Niederlande (stooq: .nl)
    "ASML.AS":   ("ASML Holding NV",             "Niederlande", "Technologie",   "asml.nl"),
    "HEIA.AS":   ("Heineken NV",                 "Niederlande", "Konsumgüter",   "heia.nl"),
    "PHIA.AS":   ("Philips NV",                  "Niederlande", "Gesundheit",    "phia.nl"),
    "ING.AS":    ("ING Groep NV",                "Niederlande", "Finanzen",      "ing.nl"),
    "AD.AS":     ("Koninklijke Ahold Delhaize",  "Niederlande", "Konsumgüter",   "ad.nl"),
    # Spanien (stooq: .es)
    "ITX.MC":    ("Industria de Diseño Textil (Inditex)","Spanien","Konsumgüter","itx.es"),
    "BBVA.MC":   ("Banco Bilbao Vizcaya Argentaria","Spanien",  "Finanzen",      "bbva.es"),
    "SAN.MC":    ("Banco Santander SA",          "Spanien",     "Finanzen",      "san.es"),
    "IBE.MC":    ("Iberdrola SA",                "Spanien",     "Energie",       "ibe.es"),
    "REP.MC":    ("Repsol SA",                   "Spanien",     "Energie",       "rep.es"),
    "TEF.MC":    ("Telefónica SA",               "Spanien",     "Telekommunikation","tef.es"),
    # Italien (stooq: .it)
    "ENI.MI":    ("Eni SpA",                     "Italien",     "Energie",       "eni.it"),
    "ENEL.MI":   ("Enel SpA",                    "Italien",     "Energie",       "enel.it"),
    "UCG.MI":    ("UniCredit SpA",               "Italien",     "Finanzen",      "ucg.it"),
    "RACE.MI":   ("Ferrari NV",                  "Italien",     "Automobil",     "race.it"),
    # Schweden (stooq: .se)
    "VOLV-B.ST": ("Volvo AB",                    "Schweden",    "Industrie",     "volv-b.se"),
    "ERIC-B.ST": ("Ericsson AB",                 "Schweden",    "Technologie",   "eric-b.se"),
    "HM-B.ST":   ("H&M Group AB",               "Schweden",    "Konsumgüter",   "hm-b.se"),
    "SAND.ST":   ("Sandvik AB",                  "Schweden",    "Industrie",     "sand.se"),
    # Dänemark (stooq: .dk)
    "NOVO-B.CO": ("Novo Nordisk A/S",            "Dänemark",    "Gesundheit",    "novo-b.dk"),
    "DSV.CO":    ("DSV A/S",                     "Dänemark",    "Industrie",     "dsv.dk"),
    # Norwegen (stooq: .no)
    "EQNR.OL":   ("Equinor ASA",                "Norwegen",    "Energie",       "eqnr.no"),
    "DNB.OL":    ("DNB Bank ASA",               "Norwegen",    "Finanzen",      "dnb.no"),
    # Finnland (stooq: .fi)
    "NOKIA.HE":  ("Nokia Oyj",                  "Finnland",    "Technologie",   "nokia.fi"),
    # Belgien (stooq: .be)
    "UCB.BR":    ("UCB SA",                     "Belgien",     "Gesundheit",    "ucb.be"),
    "ABI.BR":    ("Anheuser-Busch InBev SA/NV", "Belgien",     "Konsumgüter",   "abi.be"),
    # Österreich (stooq: .at)
    "OMV.VI":    ("OMV AG",                     "Österreich",  "Energie",       "omv.at"),
    "ERSTE.VI":  ("Erste Group Bank AG",        "Österreich",  "Finanzen",      "erst.at"),
}

CURRENCY_MAP = {
    "UK": "GBp", "Schweiz": "CHF", "Schweden": "SEK",
    "Norwegen": "NOK", "Dänemark": "DKK",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ─────────────────────────────────────────────
# Datenabruf stooq.com
# ─────────────────────────────────────────────
def fetch_ticker(session, stooq_ticker, d1, d2):
    url = "https://stooq.com/q/d/l/"
    params = {"s": stooq_ticker, "d1": d1, "d2": d2, "i": "d"}
    for attempt in range(2):
        try:
            r = session.get(url, params=params, timeout=10, headers=HEADERS)
            if r.status_code != 200 or len(r.content) < 50:
                return None
            df = pd.read_csv(io.StringIO(r.text))
            if df.empty or "Close" not in df.columns or len(df) < 2:
                return None
            df["Date"] = pd.to_datetime(df["Date"])
            return df.sort_values("Date").reset_index(drop=True)
        except Exception:
            time.sleep(1)
    return None


def fetch_data():
    end   = datetime.today()
    start = end - timedelta(days=40)
    d1    = start.strftime("%Y%m%d")
    d2    = end.strftime("%Y%m%d")

    print(f"Lade {len(STOCKS)} Aktien von stooq.com...")
    session = requests.Session()
    results = {}
    ok = 0

    for i, (ticker, (name, country, sector, stooq_t)) in enumerate(STOCKS.items()):
        df = fetch_ticker(session, stooq_t, d1, d2)
        if df is not None:
            results[ticker] = df
            ok += 1
        else:
            print(f"  Fehler: {ticker} ({stooq_t})")
        if (i + 1) % 20 == 0:
            time.sleep(1)

    print(f"  ✅ {ok}/{len(STOCKS)} Aktien geladen")
    return results


# ─────────────────────────────────────────────
# Screener aufbauen
# ─────────────────────────────────────────────
def build_screener(ticker_data):
    records = []
    for ticker, (name, country, sector, _) in STOCKS.items():
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

            currency = CURRENCY_MAP.get(country, "EUR")
            records.append({
                "ticker":     ticker,
                "name":       name,
                "country":    country,
                "sector":     sector,
                "currency":   currency,
                "close":      round(today_close, 2),
                "pct_change": round(pct_change, 2),
                "vol_ratio":  round(vol_ratio, 2),
            })
        except Exception as e:
            print(f"  Parse-Fehler {ticker}: {e}")

    df_out = pd.DataFrame(records)
    if df_out.empty:
        raise ValueError("Keine Daten verarbeitbar.")
    return df_out.sort_values("pct_change", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────
def rows_html(subset):
    html = ""
    for _, r in subset.iterrows():
        pct = r["pct_change"]
        sign = "pos" if pct >= 0 else "neg"
        arrow = "▲" if pct >= 0 else "▼"
        vol_badge = ""
        if r["vol_ratio"] >= 3:
            vol_badge = '<span class="badge hot">🔥</span>'
        elif r["vol_ratio"] >= 2:
            vol_badge = '<span class="badge warm">↑</span>'
        tv = tv_link(r['ticker'])
        html += f"""<tr data-country="{r['country']}" data-sector="{r['sector']}">
  <td><a href="{tv}" target="_blank" rel="noopener" class="chip chip-link">{r['ticker']}</a></td>
  <td class="td-name">{r['name']}</td>
  <td><span class="flag">{country_flag(r['country'])}</span> <span class="td-dim">{r['country']}</span></td>
  <td><span class="sector-tag s-{sector_slug(r['sector'])}">{r['sector']}</span></td>
  <td class="td-num">{r['close']:.2f} <span class="td-cur">{r['currency']}</span></td>
  <td class="td-num {sign} td-bold">{arrow} {abs(pct):.2f}%</td>
  <td class="td-num">{r['vol_ratio']:.1f}x {vol_badge}</td>
</tr>"""
    return html

def tv_link(ticker):
    exchange_map = {
        ".DE": "XETRA", ".PA": "EURONEXT", ".SW": "SIX", ".L": "LSE",
        ".AS": "EURONEXT", ".MC": "BME", ".MI": "MIL", ".ST": "OMX",
        ".CO": "OMXCOP", ".OL": "OSL", ".HE": "OMXHEX", ".BR": "EURONEXT", ".VI": "WBAG",
    }
    for suffix, exchange in exchange_map.items():
        if ticker.endswith(suffix):
            symbol = ticker[:-len(suffix)]
            return f"https://www.tradingview.com/chart/?symbol={exchange}%3A{symbol}"
    return f"https://www.tradingview.com/search/?query={ticker}"

def country_flag(c):
    flags = {"Deutschland":"🇩🇪","Frankreich":"🇫🇷","Schweiz":"🇨🇭","UK":"🇬🇧",
             "Niederlande":"🇳🇱","Spanien":"🇪🇸","Italien":"🇮🇹","Schweden":"🇸🇪",
             "Dänemark":"🇩🇰","Norwegen":"🇳🇴","Finnland":"🇫🇮","Belgien":"🇧🇪","Österreich":"🇦🇹"}
    return flags.get(c, "🏳️")

def sector_slug(s):
    return s.lower().replace("ü","ue").replace("ö","oe").replace("ä","ae").replace(" ","").replace("/","")


def generate_html(df, date_str, generated_at):
    gainers         = df[df["pct_change"] > 0].head(20)
    losers          = df[df["pct_change"] < 0].sort_values("pct_change").head(20)
    volume_top      = df[df["vol_ratio"] >= 1.5].sort_values("vol_ratio", ascending=False).head(20)
    market_avg      = df["pct_change"].mean()
    positive_count  = len(df[df["pct_change"] > 0])
    total_count     = len(df)
    top_g           = df.iloc[0]
    top_l           = df.iloc[-1]

    countries = sorted(df["country"].unique())
    sectors   = sorted(df["sector"].unique())

    country_opts = "".join(f'<option value="{c}">{country_flag(c)} {c}</option>' for c in countries)
    sector_opts  = "".join(f'<option value="{s}">{s}</option>' for s in sectors)

    # Sector-Farben CSS
    sector_colors = {
        "Technologie":"2563eb","Finanzen":"0891b2","Gesundheit":"059669",
        "Energie":"d97706","Konsumgüter":"7c3aed","Industrie":"475569",
        "Automobil":"dc2626","Chemie":"0d9488","Telekommunikation":"9333ea",
        "Rohstoffe":"92400e",
    }
    sector_css = "\n".join(
        f'.s-{sector_slug(s)} {{ background: #{c}22; color: #{c}; border-color: #{c}44; }}'
        for s, c in sector_colors.items()
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EU Screener – {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:        #070b0f;
  --surface:   #0d1117;
  --surface2:  #161b22;
  --surface3:  #1c2128;
  --border:    #21262d;
  --border2:   #30363d;
  --text:      #e6edf3;
  --text-dim:  #8b949e;
  --text-muted:#484f58;
  --green:     #3fb950;
  --red:       #f85149;
  --blue:      #58a6ff;
  --blue2:     #1f6feb;
  --gold:      #d29922;
  --gold2:     #f0a429;
  --purple:    #bc8cff;
  --font:      'Inter', system-ui, sans-serif;
  --mono:      'JetBrains Mono', monospace;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{ background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; line-height: 1.5; min-height: 100vh; }}

/* ── HEADER ── */
.hd {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 20px 32px;
}}
.hd-top {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}}
.logo {{ display: flex; align-items: center; gap: 10px; }}
.logo-mark {{
  width: 36px; height: 36px; border-radius: 8px;
  background: linear-gradient(135deg, var(--blue2), #0d419d);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; border: 1px solid rgba(88,166,255,.2);
}}
.logo-text h1 {{
  font-size: 16px; font-weight: 700; color: var(--text); letter-spacing: -.3px;
}}
.logo-text p {{ font-size: 11px; color: var(--text-dim); margin-top: 1px; letter-spacing: .5px; text-transform: uppercase; }}
.hd-meta {{
  display: flex; align-items: center; gap: 8px;
}}
.meta-chip {{
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 5px 12px;
  font-size: 11px; color: var(--text-dim); font-family: var(--mono);
}}
.live-dot {{
  width: 7px; height: 7px; border-radius: 50%; background: var(--green);
  box-shadow: 0 0 6px var(--green); animation: pulse 2s infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:.4 }} }}

/* ── KPI GRID ── */
.kpi-grid {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
}}
.kpi {{
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px 16px;
  position: relative; overflow: hidden;
}}
.kpi::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
}}
.kpi.g::before {{ background: var(--green); }}
.kpi.r::before {{ background: var(--red); }}
.kpi.b::before {{ background: var(--blue); }}
.kpi.o::before {{ background: var(--gold2); }}
.kpi-label {{ font-size: 10px; color: var(--text-muted); letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }}
.kpi-val {{ font-size: 24px; font-weight: 700; font-family: var(--mono); line-height: 1; }}
.kpi-val.g {{ color: var(--green); }} .kpi-val.r {{ color: var(--red); }}
.kpi-val.b {{ color: var(--blue); }} .kpi-val.o {{ color: var(--gold2); }}
.kpi-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}

/* ── TOOLBAR ── */
.toolbar {{
  display: flex; align-items: center; gap: 10px;
  padding: 16px 32px; background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}}
.search-wrap {{ position: relative; flex: 0 0 280px; }}
.search-wrap input {{
  width: 100%; background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 8px 12px 8px 34px;
  color: var(--text); font-family: var(--font); font-size: 13px;
  outline: none; transition: border-color .15s;
}}
.search-wrap input:focus {{ border-color: var(--blue); }}
.search-ico {{
  position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
  color: var(--text-muted); font-size: 13px;
}}
select {{
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 8px 28px 8px 10px;
  color: var(--text); font-family: var(--font); font-size: 12px;
  outline: none; cursor: pointer; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%238b949e' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 8px center;
  transition: border-color .15s;
}}
select:focus {{ border-color: var(--blue); }}
.toolbar-sep {{ width: 1px; height: 24px; background: var(--border2); }}
.count-info {{ font-size: 12px; color: var(--text-muted); margin-left: auto; font-family: var(--mono); }}

/* ── TABS ── */
.tabs-row {{
  display: flex; gap: 2px; padding: 12px 32px 0;
  background: var(--surface); border-bottom: 1px solid var(--border);
}}
.tab {{
  padding: 8px 18px; cursor: pointer; font-size: 13px; font-weight: 500;
  color: var(--text-dim); border-bottom: 2px solid transparent;
  margin-bottom: -1px; transition: all .15s; border-radius: 4px 4px 0 0;
  white-space: nowrap;
}}
.tab:hover {{ color: var(--text); background: var(--surface2); }}
.tab.active {{ color: var(--blue); border-bottom-color: var(--blue); }}

/* ── MAIN ── */
.main {{ padding: 24px 32px; }}
.panel {{ display: none; }} .panel.active {{ display: block; }}

/* ── TABLE ── */
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden;
}}
.card-hd {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid var(--border);
  background: var(--surface2);
}}
.card-title {{ font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
.n-badge {{
  background: var(--surface3); border: 1px solid var(--border2);
  border-radius: 20px; padding: 1px 8px; font-size: 11px;
  color: var(--text-dim); font-family: var(--mono);
}}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{
  padding: 9px 14px; text-align: left; font-size: 10px;
  color: var(--text-muted); letter-spacing: 1.5px; text-transform: uppercase;
  background: var(--surface2); cursor: pointer; user-select: none;
  white-space: nowrap; transition: color .15s; font-weight: 500;
  border-bottom: 1px solid var(--border);
}}
thead th:hover {{ color: var(--text); }}
tbody tr {{
  border-top: 1px solid var(--border);
  transition: background .1s;
}}
tbody tr:hover {{ background: rgba(88,166,255,.04); }}
tbody tr.hidden {{ display: none; }}
td {{ padding: 10px 14px; vertical-align: middle; }}
.chip-link {
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.chip-link:hover {
  background: #388bfd33;
  color: #79c0ff;
}
.chip {{
  background: rgba(88,166,255,.1); border: 1px solid rgba(88,166,255,.2);
  color: var(--blue); border-radius: 5px; padding: 2px 7px;
  font-size: 11px; font-family: var(--mono); white-space: nowrap; font-weight: 500;
}}
.td-name {{ color: var(--text); font-size: 12px; font-weight: 500; max-width: 220px; }}
.td-dim  {{ color: var(--text-dim); font-size: 11px; }}
.td-cur  {{ color: var(--text-muted); font-size: 10px; }}
.td-num  {{ text-align: right; font-family: var(--mono); font-size: 12px; }}
.td-bold {{ font-weight: 600; }}
.flag    {{ font-size: 14px; }}
.pos {{ color: var(--green); }} .neg {{ color: var(--red); }}
.sector-tag {{
  display: inline-block; border-radius: 4px; padding: 2px 7px;
  font-size: 10px; font-weight: 500; border: 1px solid;
  white-space: nowrap;
}}
{sector_css}
.badge {{ border-radius: 4px; padding: 1px 5px; font-size: 10px; margin-left: 4px; }}
.hot  {{ background: rgba(248,81,73,.15); color: var(--red); border: 1px solid rgba(248,81,73,.25); }}
.warm {{ background: rgba(210,153,34,.15); color: var(--gold2); border: 1px solid rgba(210,153,34,.25); }}

/* ── FOOTER ── */
.ft {{
  padding: 16px 32px; border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  font-size: 11px; color: var(--text-muted); background: var(--surface);
}}

@media (max-width: 768px) {{
  .hd, .toolbar, .tabs-row, .main, .ft {{ padding-left: 16px; padding-right: 16px; }}
  .kpi-grid {{ grid-template-columns: repeat(2,1fr); }}
  .search-wrap {{ flex: 1 1 100%; }}
  .td-name {{ max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
}}
</style>
</head>
<body>

<div class="hd">
  <div class="hd-top">
    <div class="logo">
      <div class="logo-mark">🇪🇺</div>
      <div class="logo-text">
        <h1>European EOD Screener</h1>
        <p>STOXX 600 · End of Day · Swing Trading</p>
      </div>
    </div>
    <div class="hd-meta">
      <div class="live-dot"></div>
      <div class="meta-chip">📅 {date_str}</div>
      <div class="meta-chip">{total_count} Aktien</div>
    </div>
  </div>
  <div class="kpi-grid">
    <div class="kpi g">
      <div class="kpi-label">Top Gainer</div>
      <div class="kpi-val g">+{top_g['pct_change']:.2f}%</div>
      <div class="kpi-sub">{top_g['name']}</div>
    </div>
    <div class="kpi r">
      <div class="kpi-label">Top Loser</div>
      <div class="kpi-val r">{top_l['pct_change']:.2f}%</div>
      <div class="kpi-sub">{top_l['name']}</div>
    </div>
    <div class="kpi b">
      <div class="kpi-label">Marktbreite</div>
      <div class="kpi-val b">{positive_count}/{total_count}</div>
      <div class="kpi-sub">Aktien im Plus</div>
    </div>
    <div class="kpi o">
      <div class="kpi-label">Ø Veränderung</div>
      <div class="kpi-val o">{"+" if market_avg>=0 else ""}{market_avg:.2f}%</div>
      <div class="kpi-sub">Marktdurchschnitt</div>
    </div>
  </div>
</div>

<div class="toolbar">
  <div class="search-wrap">
    <span class="search-ico">🔍</span>
    <input id="q" type="text" placeholder="Suche nach Ticker, Name, Sektor…" oninput="applyFilters()">
  </div>
  <div class="toolbar-sep"></div>
  <select id="f-country" onchange="applyFilters()">
    <option value="">🌍 Alle Länder</option>
    {country_opts}
  </select>
  <select id="f-sector" onchange="applyFilters()">
    <option value="">📂 Alle Sektoren</option>
    {sector_opts}
  </select>
  <span class="count-info" id="row-count">{total_count} Ergebnisse</span>
</div>

<div class="tabs-row">
  <div class="tab active" onclick="showTab('all',this)">📋 Alle Aktien</div>
  <div class="tab" onclick="showTab('gainers',this)">📈 Top Gainer</div>
  <div class="tab" onclick="showTab('losers',this)">📉 Top Loser</div>
  <div class="tab" onclick="showTab('volume',this)">🔥 Volumen</div>
</div>

<div class="main">

  <div id="p-all" class="panel active">
    <div class="card">
      <div class="card-hd">
        <div class="card-title">Alle Aktien <span class="n-badge" id="cnt-all">{total_count}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Sortierbar per Klick auf Spalte</div>
      </div>
      <table id="t-all">
        <thead><tr>
          <th onclick="sortT('t-all',0)">Ticker</th>
          <th onclick="sortT('t-all',1)">Unternehmen</th>
          <th onclick="sortT('t-all',2)">Land</th>
          <th onclick="sortT('t-all',3)">Sektor</th>
          <th onclick="sortT('t-all',4)" style="text-align:right">Kurs</th>
          <th onclick="sortT('t-all',5)" style="text-align:right">% Change</th>
          <th onclick="sortT('t-all',6)" style="text-align:right">Vol. Ratio</th>
        </tr></thead>
        <tbody>{rows_html(df)}</tbody>
      </table>
    </div>
  </div>

  <div id="p-gainers" class="panel">
    <div class="card">
      <div class="card-hd">
        <div class="card-title">📈 Top Gainer <span class="n-badge">{len(gainers)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Stärkste Aufwärtsbewegungen heute</div>
      </div>
      <table id="t-gainers">
        <thead><tr>
          <th onclick="sortT('t-gainers',0)">Ticker</th>
          <th onclick="sortT('t-gainers',1)">Unternehmen</th>
          <th onclick="sortT('t-gainers',2)">Land</th>
          <th onclick="sortT('t-gainers',3)">Sektor</th>
          <th onclick="sortT('t-gainers',4)" style="text-align:right">Kurs</th>
          <th onclick="sortT('t-gainers',5)" style="text-align:right">% Change</th>
          <th onclick="sortT('t-gainers',6)" style="text-align:right">Vol. Ratio</th>
        </tr></thead>
        <tbody>{rows_html(gainers)}</tbody>
      </table>
    </div>
  </div>

  <div id="p-losers" class="panel">
    <div class="card">
      <div class="card-hd">
        <div class="card-title">📉 Top Loser <span class="n-badge">{len(losers)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Stärkste Abwärtsbewegungen heute</div>
      </div>
      <table id="t-losers">
        <thead><tr>
          <th onclick="sortT('t-losers',0)">Ticker</th>
          <th onclick="sortT('t-losers',1)">Unternehmen</th>
          <th onclick="sortT('t-losers',2)">Land</th>
          <th onclick="sortT('t-losers',3)">Sektor</th>
          <th onclick="sortT('t-losers',4)" style="text-align:right">Kurs</th>
          <th onclick="sortT('t-losers',5)" style="text-align:right">% Change</th>
          <th onclick="sortT('t-losers',6)" style="text-align:right">Vol. Ratio</th>
        </tr></thead>
        <tbody>{rows_html(losers)}</tbody>
      </table>
    </div>
  </div>

  <div id="p-volume" class="panel">
    <div class="card">
      <div class="card-hd">
        <div class="card-title">🔥 Volumen-Anomalien <span class="n-badge">{len(volume_top)}</span></div>
        <div style="font-size:11px;color:var(--text-dim)">Volumen ≥ 1.5× 20-Tage-Durchschnitt</div>
      </div>
      <table id="t-volume">
        <thead><tr>
          <th onclick="sortT('t-volume',0)">Ticker</th>
          <th onclick="sortT('t-volume',1)">Unternehmen</th>
          <th onclick="sortT('t-volume',2)">Land</th>
          <th onclick="sortT('t-volume',3)">Sektor</th>
          <th onclick="sortT('t-volume',4)" style="text-align:right">Kurs</th>
          <th onclick="sortT('t-volume',5)" style="text-align:right">% Change</th>
          <th onclick="sortT('t-volume',6)" style="text-align:right">Vol. Ratio</th>
        </tr></thead>
        <tbody>{rows_html(volume_top)}</tbody>
      </table>
    </div>
  </div>

</div>

<div class="ft">
  <div>Daten: stooq.com · Kein Anlageberatungsersatz · Nur zur Information</div>
  <div>Generiert: {generated_at}</div>
</div>

<script>
function showTab(name, el) {{
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('p-' + name).classList.add('active');
  el.classList.add('active');
}}

function applyFilters() {{
  const q       = document.getElementById('q').value.toLowerCase();
  const country = document.getElementById('f-country').value;
  const sector  = document.getElementById('f-sector').value;
  let visible   = 0;
  document.querySelectorAll('#t-all tbody tr').forEach(row => {{
    const text = row.textContent.toLowerCase();
    const rc   = row.dataset.country;
    const rs   = row.dataset.sector;
    const show = (!q || text.includes(q))
              && (!country || rc === country)
              && (!sector  || rs === sector);
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('row-count').textContent = visible + ' Ergebnisse';
  document.getElementById('cnt-all').textContent   = visible;
}}

function sortT(tableId, colIdx) {{
  const table = document.getElementById(tableId);
  const tbody = table.querySelector('tbody');
  const th    = table.querySelectorAll('thead th')[colIdx];
  const asc   = th.dataset.dir !== 'asc';
  table.querySelectorAll('thead th').forEach(t => delete t.dataset.dir);
  th.dataset.dir = asc ? 'asc' : 'desc';
  th.textContent = th.textContent.replace(/ [▲▼]$/,'') + (asc ? ' ▲' : ' ▼');
  const rows = [...tbody.querySelectorAll('tr')];
  rows.sort((a, b) => {{
    const av = a.cells[colIdx].textContent.replace(/[^0-9.\-]/g,'');
    const bv = b.cells[colIdx].textContent.replace(/[^0-9.\-]/g,'');
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
    return asc
      ? a.cells[colIdx].textContent.localeCompare(b.cells[colIdx].textContent)
      : b.cells[colIdx].textContent.localeCompare(a.cells[colIdx].textContent);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    date_str     = datetime.today().strftime("%d.%m.%Y")
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M Uhr (UTC)")

    ticker_data = fetch_data()
    df          = build_screener(ticker_data)

    print(f"✅ {len(df)} Aktien verarbeitet")
    print(f"📈 Top Gainer: {df.iloc[0]['ticker']} {df.iloc[0]['name']} (+{df.iloc[0]['pct_change']:.2f}%)")
    print(f"📉 Top Loser:  {df.iloc[-1]['ticker']} {df.iloc[-1]['name']} ({df.iloc[-1]['pct_change']:.2f}%)")

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(df, date_str, generated_at))
    print("💾 docs/index.html gespeichert")

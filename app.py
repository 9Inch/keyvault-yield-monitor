import streamlit as st
import oracledb
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import requests
import smtplib
from email.message import EmailMessage
import time

# =============== PAGE CONFIG ===============
st.set_page_config(
    page_title="KeyVault Yield Monitor - M Edition",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# =============== ULTIMATE BMW M CSS ===============
st.markdown("""
<style>
    [data-testid="stDeployButton"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 96% !important;}
    .stApp {
        background: linear-gradient(135deg, #0a0e17 0%, #080c12 50%, #0d1117 100%),
                    url('https://i.imgur.com/2j5f0hE.png') repeat;
        background-size: cover, 400px 400px;
        background-attachment: fixed;
    }
    section[data-testid="stSidebar"] {
        width: 430px !important; background: #000000 !important;
        border-right: 6px solid #1e40af !important; box-shadow: 30px 0 100px rgba(30,64,175,0.7) !important;
        padding-top: 2.5rem !important;
    }
    section[data-testid="stSidebar"] * {color: #e2e8f0 !important;}
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #1e40af, #2563eb) !important;
        border: 2px solid #60a5fa !important; color: white !important; font-weight: bold !important;
        box-shadow: 0 0 20px rgba(96,165,250,0.4) !important;
    }
    .stButton>button[kind="primary"]:hover {
        background: #60a5fa !important; box-shadow: 0 0 30px rgba(96,165,250,0.8) !important;
        transform: translateY(-2px);
    }
    .title-main {
        font-size: 6.8rem !important; font-weight: 900 !important;
        background: linear-gradient(90deg, #1e40af, #60a5fa, #3b82f6, #60a5fa, #1e40af);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        letter-spacing: -4px; text-shadow: 0 0 40px rgba(30,64,175,0.6);
    }
    .title-sub {font-size: 1.6rem !important; color: #94a3b8 !important; letter-spacing: 6px; text-transform: uppercase; font-weight: 700;}
    .yield-card {
        height: 420px !important; padding: 3.2rem 2.2rem !important; border-radius: 40px !important;
        text-align: center !important; box-shadow: 0 20px 60px rgba(0,0,0,0.9) !important;
        transition: all 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        background: var(--gradient) !important; display: flex !important; flex-direction: column !important;
        justify-content: center !important; align-items: center !important;
        border: 3px solid rgba(30,64,175,0.4) !important; backdrop-filter: blur(20px) !important;
        position: relative !important; overflow: hidden !important;
    }
    .yield-card::before {
        content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(30,64,175,0.15) 0%, transparent 70%);
        animation: rotate 20s linear infinite; pointer-events: none;
    }
    @keyframes rotate {0% {transform: rotate(0deg);} 100% {transform: rotate(360deg);}}
    .yield-card:hover {
        transform: translateY(-30px) scale(1.08) !important;
        box-shadow: 0 60px 140px rgba(30,64,175,0.8) !important; border: 3px solid #60a5fa !important;
    }
    .station-name {font-size: 3.8rem !important; font-weight: 900 !important; margin-bottom: 0.8rem !important; text-shadow: 0 0 20px rgba(30,64,175,0.5);}
    .yield-label {font-size: 2.5rem !important; opacity: 0.9 !important;}
    .yield-value {font-size: 5.2rem !important; font-weight: 900 !important; letter-spacing: -4px;}
    .yield-output {font-size: 3.6rem !important; font-weight: 700;}
    .stToast {background-color: #0f172a !important; color: #e2e8f0 !important; border: 1px solid #1e40af !important; border-radius: 12px !important;}
</style>
""", unsafe_allow_html=True)

# TITLE + CLOCK
st.markdown(
    """<div style="text-align: center;">
    <h1 class="title-main">KeyVault Yield Monitor</h1>
    <p class="title-sub">Real-time Production Dashboard</p>
    </div>""",
    unsafe_allow_html=True
)

clock_placeholder = st.empty()
def update_clock():
    now = datetime.now()
    clock_text = f"{now.strftime('%d %B %Y')} • Shift 08:00 → Current • {now.strftime('%H:%M')}"
    with clock_placeholder.container():
        st.markdown(
            f"""<div style="text-align: center; margin: 0.5px 0 30px 0; font-size: 1.6rem; font-weight: 600;
                background: linear-gradient(90deg, #1e40af, #60a5fa, #3b82f6, #60a5fa, #1e40af);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
                text-shadow: 0 0 60px rgba(96,165,250,0.9); letter-spacing: 10px;">
                {clock_text}
            </div>""", unsafe_allow_html=True
        )
update_clock()
st_autorefresh(interval=60_000, key="clock")

# CONNECTION
oracledb.init_oracle_client(lib_dir=r"C:\oracle\ODAC64\instantclient")

@st.cache_resource(show_spinner=False)
def init_connection(u, p):
    try: return oracledb.connect(user=u, password=p, host="10.51.130.182", port=1521, service_name="KVDB")
    except Exception as e: st.error(f"Connection failed: {e}"); return None

@st.cache_data(ttl=30)
def run_query(_conn, q):
    try: return pd.read_sql(q, _conn)
    except: return pd.DataFrame()

# TG&MAIL SETUP
TELEGRAM_TOKEN = "8209829432:AAHruz1iwFPYJMDqY12I8ygu4a_bcOIBBsU"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
CHAT_IDS = ["1697324826", "-5097867015"]
FROM_EMAIL = "CCET_CP1_SPQ@calcomp.co.th"

if "email_recipients" not in st.session_state:
    st.session_state.email_recipients = "apinut_n@calcomp.co.th"  # default

def send_telegram(m):
    if st.session_state.get("telegram_enabled", True):
        for cid in CHAT_IDS:
            try: requests.post(TELEGRAM_URL, data={"chat_id": cid, "text": m, "parse_mode": "HTML"}, timeout=10)
            except: pass

def send_email(sub, body, recipient=None):
    if st.session_state.get("email_enabled", True):
        recipients = [email.strip() for email in st.session_state.email_recipients.split(",") if email.strip()]
        if not recipients:
            st.warning("No email recipients configured!")
            return
        msg = EmailMessage()
        msg['From'] = FROM_EMAIL
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = sub
        msg.add_alternative(body, subtype='html')
        try:
            smtplib.SMTP("mailpe.calcomp.co.th", 25, timeout=20).send_message(msg)
            st.toast(f"Email sent to {len(recipients)} recipient(s)!", icon="✅")
        except Exception as e:
            st.error(f"Email failed: {e}")

# REPORT&ALERT
def send_hourly_report(conn, now: datetime):
    shift_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8: shift_start -= timedelta(days=1)
    last_end = now.replace(minute=0, second=0, microsecond=0)
    last_start = last_end - timedelta(hours=1)
    period = f"{last_start:%H}:00 - {last_end:%H}:00"
    cum_df = pd.read_sql(f"SELECT STATION, COUNT(*) TOTAL, SUM(CASE WHEN DEF_ITEM='OK' THEN 1 ELSE 0 END) OK FROM dqc342 WHERE TEST_DTTM >= TO_DATE('{shift_start:%Y-%m-%d %H:%M:%S}', 'YYYY-MM-DD HH24:MI:SS') AND TEST_DTTM < TO_DATE('{now:%Y-%m-%d %H:%M:%S}', 'YYYY-MM-DD HH24:MI:SS') GROUP BY STATION", conn)
    hourly_df = pd.read_sql(f"SELECT STATION, COUNT(*) TOTAL, SUM(CASE WHEN DEF_ITEM='OK' THEN 1 ELSE 0 END) OK FROM dqc342 WHERE TEST_DTTM >= TO_DATE('{last_start:%Y-%m-%d %H:%M:%S}', 'YYYY-MM-DD HH24:MI:SS') AND TEST_DTTM < TO_DATE('{last_end:%Y-%m-%d %H:%M:%S}', 'YYYY-MM-DD HH24:MI:SS') GROUP BY STATION", conn)
    stations_order = ["PCA ICT", "PCA FCT1", "RC4", "VMI2", "PCA FCT2", "V2"]
    def calc(df):
        if df.empty: return {}
        df['YIELD'] = (df['OK'] / df['TOTAL'] * 100).round(2)
        df['OK_PCS'] = df['OK']
        return df.set_index('STATION')[['YIELD', 'OK_PCS']].to_dict('index')
    cum = calc(cum_df); hourly = calc(hourly_df)
    low = any(cum.get(s, {}).get('YIELD', 100) < 95 and cum.get(s, {}).get('OK_PCS', 0) > 10 for s in stations_order) or \
          any(hourly.get(s, {}).get('YIELD', 100) < 95 and hourly.get(s, {}).get('OK_PCS', 0) > 0 for s in stations_order)
    msg = f"""KeyVault Report\n{now:%d %B %Y} | {now:%H:%M}\n\nCumulative Yield\n""" + \
          "\n".join([f"• {s}: {cum[s]['YIELD']:.2f}% ({int(cum[s]['OK_PCS']):,} pcs)" for s in stations_order if s in cum]) + \
          f"\n\nLast Hour ({period})\n" + \
          "\n".join([f"• {s}: {hourly[s]['YIELD']:.2f}%" for s in stations_order if s in hourly and hourly[s]['OK_PCS'] > 0]) + \
          f"\n\n{'LOW YIELD ALERT' if low else 'ALL GOOD'}"
    send_telegram(msg)
    if st.session_state.get("email_enabled", True):
        html_body = f"<h2>KeyVault Report - {now.strftime('%d %B %Y %H:%M')}</h2><pre>{msg}</pre>"
        send_email(f"KeyVault Report - {now.strftime('%d %B %Y')}", html_body)

last_alert_time = {}
def check_realtime_alert(conn):
    global last_alert_time
    now = datetime.now()
    shift = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8: shift -= timedelta(days=1)
    try:
        df = pd.read_sql(f"SELECT STATION, COUNT(*) TOTAL, SUM(CASE WHEN DEF_ITEM='OK' THEN 1 ELSE 0 END) OK FROM dqc342 WHERE TEST_DTTM >= TO_DATE('{shift:%Y-%m-%d 08:00:00}', 'YYYY-MM-DD HH24:MI:SS') GROUP BY STATION HAVING COUNT(*)>10", conn)
        if df.empty: return
        df['YIELD'] = (df['OK'] / df['TOTAL'] * 100).round(2)
        for _, r in df.iterrows():
            station = r.STATION
            current_yield = r.YIELD
            key = f"{shift:%Y%m%d}_{station}"
            if key not in last_alert_time:
                last_alert_time[key] = {'yield': current_yield, 'alerted': False}
            prev_yield = last_alert_time[key]['yield']
            alerted = last_alert_time[key]['alerted']
            if current_yield < 95 and not alerted:
                send_telegram(f"""REAL-TIME ALERT\nStation: {station}\nYield dropped to {current_yield:.2f}% (from {prev_yield:.2f}%)\nOK: {int(r.OK):,} pcs | {now:%H:%M}\nImmediate action required!""")
                last_alert_time[key]['alerted'] = True
            if current_yield >= 95:
                last_alert_time[key]['alerted'] = False
            last_alert_time[key]['yield'] = current_yield
    except: pass

# SIDEBAR
if "connected" not in st.session_state: st.session_state.connected = False
if "last_report_hour" not in st.session_state: st.session_state.last_report_hour = -1

with st.sidebar:
    try: st.image("assets/logo.png", use_container_width=True)
    except: st.markdown("<h1 style='text-align:center; color:#60a5fa;'>KEYVAULT</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if not st.session_state.connected:
        st.markdown("### Database Connection")
        user = st.text_input("Username", type="password")
        pwd = st.text_input("Password", type="password")
        if st.button("Connect", type="primary", use_container_width=True):
            conn = init_connection(user, pwd)
            if conn:
                st.session_state.conn = conn
                st.session_state.connected = True
                st.success("Connected successfully!")
                st.rerun()
    else:
        st.success(f"Connected as **{st.session_state.conn.username.upper()}**")
        if st.button("Disconnect", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    jo = st.text_input("Search JO Number", placeholder="e.g. 112345701")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Search", type="primary", use_container_width=True) and jo.strip():
            st.session_state.jo_number = jo.strip().upper()
            st.session_state.jo_mode = True
            st.rerun()
    with c2:
        if st.button("Clear", use_container_width=True):
            st.session_state.jo_number = ""
            st.session_state.jo_mode = False
            st.rerun()

    st.checkbox("Telegram Alerts", value=True, key="telegram_enabled")
    st.checkbox("Email Reports", value=True, key="email_enabled")

    if st.button("Send Test Report", type="primary", use_container_width=True):
        send_hourly_report(st.session_state.conn, datetime.now())
        st.toast("Test report sent!", icon="✅")

    with st.expander("Setup Email Recipients", expanded=False):
        new_emails = st.text_area(
            "Email Recipients (คั่นด้วย comma)",
            value=st.session_state.email_recipients,
            height=120,
            help="เช่น: user1@calcomp.co.th, user2@calcomp.co.th"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Email List", type="primary", use_container_width=True):
                st.session_state.email_recipients = new_emails.strip()
                st.success("Email list updated!")
                st.rerun()
        with col2:
            if st.button("Reset to Default", use_container_width=True):
                st.session_state.email_recipients = "apinut_n@calcomp.co.th"
                st.success("Reset complete!")
                st.rerun()

    st.date_input("Production Date", value=datetime.now().date(), key="selected_date")

# MAIN DASH
if not st.session_state.connected:
    st.info("Please connect to database from sidebar.")
    st.stop()

_ = st_autorefresh(interval=60_000, key="data_refresh")
now = datetime.now()

# REPORT
if now.minute == 0 and now.second < 5 and st.session_state.last_report_hour != now.hour:
    send_hourly_report(st.session_state.conn, now)
    st.session_state.last_report_hour = now.hour
    st.toast("Hourly report sent!", icon="✅")

check_realtime_alert(st.session_state.conn)

d = st.session_state.get("selected_date", datetime.now().date())
if st.session_state.get("jo_mode") and st.session_state.get("jo_number"):
    filt = f"AND TRIM(UPPER(JO_NO)) = '{st.session_state.jo_number}'"
else:
    filt = f"AND TRUNC(TEST_DTTM) = TO_DATE('{d:%Y-%m-%d}', 'YYYY-MM-DD')"

df = run_query(st.session_state.conn,
    f"SELECT STATION, COUNT(*) TOTAL, SUM(CASE WHEN DEF_ITEM='OK' THEN 1 ELSE 0 END) OK FROM dqc342 WHERE 1=1 {filt} GROUP BY STATION")

if df.empty:
    st.warning("No production data yet. Waiting for first test...")
else:
    df['YIELD_%'] = (df['OK'] / df['TOTAL'] * 100).round(2)
    df['OK_PCS'] = df['OK']
    df = df.set_index('STATION')
    data = df[['YIELD_%', 'OK_PCS']].to_dict('index')

    # DETAIL SUP DASH
    if st.session_state.get("selected_station"):
        station = st.session_state.selected_station
        if st.button("Back to Dashboard"):
            st.session_state.selected_station = None
            st.rerun()
        st.markdown(f"# {station} - Hourly Yield Details")
        h_query = f"""SELECT TO_CHAR(TEST_DTTM, 'YYYY-MM-DD HH24') AS HOUR,
                     COUNT(*) TOTAL, SUM(CASE WHEN DEF_ITEM='OK' THEN 1 ELSE 0 END) OK
                     FROM dqc342 WHERE STATION = '{station}' {filt}
                     GROUP BY TO_CHAR(TEST_DTTM, 'YYYY-MM-DD HH24') ORDER BY HOUR"""
        hdf = run_query(st.session_state.conn, h_query)
        if not hdf.empty:
            hdf['YIELD_%'] = (hdf['OK'] / hdf['TOTAL'] * 100).round(2)
            hdf['FAIL'] = hdf['TOTAL'] - hdf['OK']
            st.dataframe(hdf[['HOUR', 'TOTAL', 'OK', 'FAIL', 'YIELD_%']], use_container_width=True, hide_index=True)
            chart = alt.Chart(hdf).mark_line(strokeWidth=6, color='#1e40af').encode(
                x='HOUR:O', y=alt.Y('YIELD_%:Q', scale=alt.Scale(domain=[80, 100])),
                tooltip=['HOUR', 'YIELD_%', 'OK', 'FAIL']
            ).properties(height=520, title=f"Yield Trend - {station}")
            points = chart.mark_circle(size=140, color='#60a5fa')
            low = chart.transform_filter(alt.datum.YIELD_ < 95).mark_circle(size=200, color='#ef4444')
            st.altair_chart(chart + points + low, use_container_width=True)
        else:
            st.warning("No hourly data available.")
        st.stop()

    # CARD
    def get_card_gradient(y):
        if y is None or y == 0: return "linear-gradient(135deg, #1a202c, #2d3748)"
        if y >= 99.5: return "linear-gradient(135deg, #22c55e, #16a34a)"
        if y >= 98:   return "linear-gradient(135deg, #16a34a, #15803d)"
        if y >= 95:   return "linear-gradient(135deg, #facc15, #ca8a04)"
        return "linear-gradient(135deg, #ef4444, #dc2626)"

    def render_card(station, y=None, pcs=0):
        grad = get_card_gradient(y)
        status = "NO PRODUCTION" if pcs == 0 else f"{y:.2f}%"
        label = "STATUS" if pcs == 0 else "YIELD"
        out = "" if pcs == 0 else f"OUTPUT: {pcs:,} pcs"
        return f'<div class="yield-card" style="--gradient: {grad};"><div class="station-name">{station}</div><div class="yield-label">{label}</div><div class="yield-value">{status}</div><div class="yield-output">{out}</div></div>'

    stations = ["PCA ICT", "PCA FCT1", "RC4", "VMI2", "PCA FCT2", "V2"]
    for i in range(0, len(stations), 3):
        cols = st.columns(3, gap="large")
        for j, s in enumerate(stations[i:i+3]):
            with cols[j]:
                d = data.get(s, {})
                y = d.get('YIELD_%')
                p = int(d.get('OK_PCS', 0))
                st.markdown(render_card(s, y, p), unsafe_allow_html=True)
                if st.button("View Detail", key=f"detail_{s}", use_container_width=True):
                    st.session_state.selected_station = s
                    st.rerun()
    if 'last_data_refresh' not in st.session_state:
        st.session_state.last_data_refresh = time.time()
    if time.time() - st.session_state.last_data_refresh > 60:
        st.session_state.last_data_refresh = time.time()
        st.rerun()

st.markdown("---")
st.caption("© KeyVault Yield Monitor • Powered by APN_888")
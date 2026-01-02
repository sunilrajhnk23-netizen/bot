import streamlit as st
import pandas as pd
import numpy as np
import datetime
from kiteconnect import KiteConnect

from ta.momentum import RSIIndicator, WilliamsRIndicator
from ta.volatility import BollingerBands
from ta.trend import ADXIndicator, SMAIndicator

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config("NIFTY Options Strategy – KITE", layout="wide")

# =====================================================
# KITE LOGIN (PASTE DAILY TOKEN)
# =====================================================
API_KEY = "2fny2gd8v1yxolco"
ACCESS_TOKEN = "DE6nFxNEhJon0EH2IgrfBOSzczKVFXhf"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# =====================================================
# LOAD STOCK LIST
# =====================================================
@st.cache_data
def load_stocks():
    df = pd.read_csv("Stock1.csv")
    return df["Stock"].dropna().unique().tolist()

stocks = load_stocks()

# =====================================================
# INSTRUMENT TOKEN MAP
# =====================================================
@st.cache_data
def get_instrument_tokens():
    instruments = kite.instruments("NSE")
    return {
        i["tradingsymbol"]: i["instrument_token"]
        for i in instruments
    }

token_map = get_instrument_tokens()

# =====================================================
# FETCH 5-MIN DATA FROM KITE
# =====================================================
@st.cache_data
def fetch_data(symbol):
    try:
        token = token_map.get(symbol)
        if token is None:
            return None

        to_dt = datetime.datetime.now()
        from_dt = to_dt - datetime.timedelta(days=5)

        data = kite.historical_data(
            instrument_token=token,
            from_date=from_dt,
            to_date=to_dt,
            interval="5minute"
        )

        df = pd.DataFrame(data)
        if df.empty:
            return None

        df.rename(columns={
            "date": "Datetime",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        }, inplace=True)

        df["Stock"] = symbol
        return df

    except Exception as e:
        st.warning(f"{symbol}: {e}")
        return None

# =====================================================
# INDICATORS
# =====================================================
def add_indicators(df):
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    bb60 = BollingerBands(close, 60)
    bb105 = BollingerBands(close, 105)
    bb150 = BollingerBands(close, 150)

    df["BB60"] = (bb60.bollinger_hband() - bb60.bollinger_lband()) / close * 100
    df["BB105"] = (bb105.bollinger_hband() - bb105.bollinger_lband()) / close * 100
    df["BB150"] = (bb150.bollinger_hband() - bb150.bollinger_lband()) / close * 100

    df["RSI20"] = RSIIndicator(close, 20).rsi()
    df["WILLR28"] = WilliamsRIndicator(high, low, close, 28).williams_r()

    dmi6 = ADXIndicator(high, low, close, 6)
    dmi20 = ADXIndicator(high, low, close, 20)

    df["+DI6"] = dmi6.adx_pos()
    df["-DI6"] = dmi6.adx_neg()
    df["+DI20"] = dmi20.adx_pos()
    df["-DI20"] = dmi20.adx_neg()

    df["MA8"] = SMAIndicator(close, 8).sma_indicator()
    return df

# =====================================================
# MAIN PIPELINE
# =====================================================
frames = []

for stock in stocks:
    data = fetch_data(stock)
    if data is not None:
        frames.append(add_indicators(data))

if not frames:
    st.error("No data fetched from Kite API")
    st.stop()

df = pd.concat(frames, ignore_index=True)

# =====================================================
# TIME FILTER
# =====================================================
df["Time"] = df["Datetime"].dt.time
df = df[df["Time"] >= datetime.time(10, 0)]

# =====================================================
# CALL CONDITIONS
# =====================================================
df["CALL_ENTRY"] = (
    (df["BB60"] <= 35) &
    (df["RSI20"].between(65, 100)) &
    (df["WILLR28"].between(-20, 0)) &
    (df["+DI6"] >= 40) & (df["-DI6"] <= 12) &
    (df["+DI20"] >= 35) & (df["-DI20"] <= 15)
)

# =====================================================
# PUT CONDITIONS
# =====================================================
df["PUT_ENTRY"] = (
    (df["BB60"] <= 35) &
    (df["RSI20"].between(1, 40)) &
    (df["WILLR28"].between(-100, -80)) &
    (df["-DI6"] >= 35) & (df["+DI6"] <= 15) &
    (df["-DI20"] >= 30) & (df["+DI20"] <= 15)
)

# =====================================================
# EXIT CONDITIONS
# =====================================================
df["CALL_EXIT"] = (
    (abs(df["+DI20"] - df["-DI20"]) < 10) |
    (df["Close"] < df["MA8"])
)

df["PUT_EXIT"] = (
    (abs(df["+DI20"] - df["-DI20"]) < 10) |
    (df["Close"] > df["MA8"])
)

# =====================================================
# DASHBOARD
# =====================================================
st.title("📊 NIFTY CALL & PUT Strategy – KITE API")

cols = [
    "Stock", "BB60", "BB105", "BB150",
    "WILLR28", "RSI20",
    "+DI6", "-DI6", "+DI20", "-DI20"
]

tab1, tab2 = st.tabs(["📈 CALL SIDE", "📉 PUT SIDE"])

with tab1:
    st.subheader("CALL – ACTIVE SIGNALS")
    st.dataframe(
        df[df["CALL_ENTRY"] & ~df["CALL_EXIT"]][cols].sort_values("BB60"),
        use_container_width=True
    )

with tab2:
    st.subheader("PUT – ACTIVE SIGNALS")
    st.dataframe(
        df[df["PUT_ENTRY"] & ~df["PUT_EXIT"]][cols].sort_values("BB60"),
        use_container_width=True
    )

st.caption("📡 Data: Kite Connect | ⏱ From 10:00 AM | 🔁 Intraday Scanner")

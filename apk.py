import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. 網頁配置與匯率獲取 ---
st.set_page_config(page_title="專業投資監測 | 多幣別版", layout="wide")

@st.cache_data(ttl=3600)  # 匯率每小時更新一次即可
def get_usd_twd():
    try:
        data = yf.download("TWD=X", period="1d", progress=False)
        return data['Close'].iloc[-1]
    except:
        return 32.5  # 萬一抓不到，給一個預設參考值

usd_twd = get_usd_twd()

# --- 2. Session State ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "IONQ", "shares": 30.0, "cost": 45.498},
        {"ticker": "EOSE", "shares": 100.0, "cost": 11.747},
        {"ticker": "ONDS", "shares": 110.0, "cost": 10.043}
    ]

# --- 3. 側邊欄與幣別切換 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    currency = st.radio("顯示幣別", ["USD (美金)", "TWD (台幣)"], horizontal=True)
    rate = usd_twd if "TWD" in currency else 1.0
    symbol = "NT$" if "TWD" in currency else "$"
    
    st.info(f"當前匯率參考 1 USD = {usd_twd:.2f} TWD")
    
    st.divider()
    st.header("🛠 管理持股")
    # (此處保留原有的新增/刪除表單邏輯...)
    with st.form("add_stock"):
        t_input = st.text_input("代碼").upper()
        s_input = st.number_input("股數", min_value=0.0)
        c_input = st.number_input("成本 (USD)", min_value=0.0)
        if st.form_submit_button("新增/更新"):
            # 更新邏輯與之前相同
            st.session_state.portfolio = [i for i in st.session_state.portfolio if i['ticker'] != t_input]
            st.session_state.portfolio.append({"ticker": t_input, "shares": s_input, "cost": c_input})
            st.rerun()

# --- 4. 數據獲取與處理 ---
if st.session_state.portfolio:
    tickers = [item['ticker'] for item in st.session_state.portfolio]
    raw_data = yf.download(tickers, period="5d", interval="15m", group_by='ticker', progress=False)
    
    results = []
    total_cost_usd = 0.0
    total_market_usd = 0.0
    
    # 建立一個字典存儲每支股票的歷史數據，方便畫個股圖
    stock_histories = {}

    for item in st.session_state.portfolio:
        t = item['ticker']
        df = raw_data[t] if len(tickers) > 1 else raw_data
        df = df.dropna()
        
        current_price = df['Close'].iloc[-1]
        market_val = current_price * item['shares']
        cost_val = item['cost'] * item['shares']
        
        total_cost_usd += cost_val
        total_market_usd += market_val
        stock_histories[t] = df['Close']
        
        results.append({
            "股票": t, "股數": item['shares'],
            "成本": item['cost'] * rate,
            "現價": current_price * rate,
            "市值": market_val * rate,
            "損益": (market_val - cost_val) * rate,
            "百分比": ((market_val - cost_val) / cost_val * 100) if cost_val != 0 else 0
        })

    # --- 5. UI 顯示 ---
    m1, m2, m3 = st.columns(3)
    m1.metric("總市值", f"{symbol}{total_market_usd * rate:,.0f}")
    m2.metric("總損益", f"{symbol}{(total_market_usd - total_cost_usd) * rate:,.0f}", f"{((total_market_usd - total_cost_usd)/total_cost_usd*100):.2f}%")
    m3.metric("總成本", f"{symbol}{total_cost_usd * rate:,.0f}")

    tabs = st.tabs(["📈 趨勢分析", "📋 持股清單"])
    
    with tabs[0]:
        col_a, col_b = st.columns([1, 3])
        with col_a:
            selected_stock = st.selectbox("選擇查看趨勢", ["投資組合總額"] + tickers)
        
        if selected_stock == "投資組合總額":
            # 計算總市值走勢
            portfolio_ts = pd.DataFrame()
            for item in st.session_state.portfolio:
                s_ts = stock_histories[item['ticker']] * item['shares']
                portfolio_ts = s_ts if portfolio_ts.empty else portfolio_ts.add(s_ts, fill_value=0)
            fig = px.area(portfolio_ts * rate, title="投資組合總價值走勢")
        else:
            # 個股趨勢圖
            fig = px.line(stock_histories[selected_stock] * rate, title=f"{selected_stock} 價格走勢 ({currency})")
        
        fig.update_layout(template="plotly_dark", yaxis_title=f"價值 ({currency})")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.dataframe(pd.DataFrame(results).style.format(precision=2), use_container_width=True)
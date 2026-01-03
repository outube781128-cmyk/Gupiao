import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. 網頁配置與自定義 CSS ---
st.set_page_config(page_title="NEON Portfolio Terminal", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; }
    .logo-img { border-radius: 50%; border: 2px solid #00ffcc; margin-right: 10px; }
    h3 { color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始數據 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "NVDA", "shares": 10.0, "cost": 100.0, "domain": "nvidia.com"},
        {"ticker": "AAPL", "shares": 5.0, "cost": 180.0, "domain": "apple.com"},
        {"ticker": "TSLA", "shares": 2.0, "cost": 250.0, "domain": "tesla.com"}
    ]

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("🛰️ 控制中心")
    with st.expander("➕ 新增資產", expanded=False):
        with st.form("add_form"):
            t = st.text_input("股票代碼 (例如: NVDA)").upper().strip()
            d = st.text_input("公司官網 (例如: nvidia.com)", help="用於獲取 Logo")
            s = st.number_input("股數", min_value=0.0)
            c = st.number_input("成本(USD)", min_value=0.0)
            if st.form_submit_button("寫入數據") and t:
                st.session_state.portfolio = [i for i in st.session_state.portfolio if i['ticker'] != t]
                st.session_state.portfolio.append({"ticker": t, "shares": s, "cost": c, "domain": d})
                st.rerun()

    if st.session_state.portfolio:
        with st.expander("🗑️ 移除項目"):
            dt = st.selectbox("選擇標的", [i['ticker'] for i in st.session_state.portfolio])
            if st.button("確認銷毀"):
                st.session_state.portfolio = [i for i in st.session_state.portfolio if i['ticker'] != dt]
                st.rerun()

# --- 4. 數據核心運算 ---
if st.session_state.portfolio:
    tickers = [item['ticker'] for item in st.session_state.portfolio]
    
    try:
        with st.spinner('📡 數據同步中...'):
            raw_data = yf.download(tickers + ["TWD=X"], period="5d", interval="15m", group_by='ticker', progress=False)
            usdtwd = raw_data["TWD=X"]["Close"].iloc[-1]
        
        results = []
        total_market_usd = 0.0
        total_cost_usd = 0.0
        portfolio_trend = None

        for item in st.session_state.portfolio:
            t = item['ticker']
            ticker_df = raw_data[t] if len(tickers) + 1 > 1 else raw_data
            if ticker_df.empty: continue

            curr_price = ticker_df['Close'].iloc[-1]
            mkt_val = curr_price * item['shares']
            cost_val = item['cost'] * item['shares']
            
            total_market_usd += mkt_val
            total_cost_usd += cost_val

            stock_series = ticker_df['Close'] * item['shares']
            portfolio_trend = stock_series if portfolio_trend is None else portfolio_trend.add(stock_series, fill_value=0)

            results.append({
                "Logo": f"https://logo.clearbit.com/{item['domain']}",
                "Ticker": t, "Price": curr_price, "Value(USD)": mkt_val,
                "Profit": mkt_val - cost_val, "P%": ((mkt_val - cost_val)/cost_val*100)
            })

        # --- 5. UI 佈局 ---
        st.title("⚡ 核心投資監控終端")
        
        # KPI 區
        c1, c2, c3 = st.columns(3)
        c1.metric("總市值 (USD)", f"${total_market_usd:,.0f}")
        c2.metric("總市值 (TWD)", f"NT$ {total_market_usd * usdtwd:,.0f}")
        c3.metric("總損益", f"${total_market_usd - total_cost_usd:,.2f}", f"{(total_market_usd - total_cost_usd)/total_cost_usd*100:.2f}%")

        tab1, tab2 = st.tabs(["📊 組合分析", "🔍 個股診斷"])
        
        with tab1:
            st.subheader("📋 持股監控清單")
            # 建立帶有 Logo 的顯示列
            for res in results:
                col_logo, col_txt = st.columns([1, 15])
                with col_logo:
                    st.image(res['Logo'], width=40)
                with col_txt:
                    # 使用 markdown 讓文字對齊 Logo
                    color = "#00ffcc" if res['Profit'] >= 0 else "#ff4b4b"
                    st.markdown(f"**{res['Ticker']}** | 市價: ${res['Price']:.2f} | 市值: ${res['Value(USD)']:,.0f} | <span style='color:{color}'>損益: ${res['Profit']:,.2f} ({res['P%']:.2f}%)</span>", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("資產權重比例")
            fig_pie = px.pie(pd.DataFrame(results), values='Value(USD)', names='Ticker', hole=0.7, color_discrete_sequence=px.colors.sequential.Cyan_r)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab2:
            st.subheader("個別標的深度追蹤")
            selected_item = st.selectbox("請選擇代碼", st.session_state.portfolio, format_func=lambda x: x['ticker'])
            
            # 頂部個股 Logo 與標題
            logo_col, title_col = st.columns([1, 10])
            with logo_col:
                st.image(f"https://logo.clearbit.com/{selected_item['domain']}", width=60)
            with title_col:
                st.markdown(f"## {selected_item['ticker']} - {selected_item['domain']}")

            detail_df = raw_data[selected_item['ticker']] if len(tickers) + 1 > 1 else raw_data
            fig_detail = go.Figure(go.Candlestick(
                x=detail_df.index, open=detail_df['Open'], high=detail_df['High'],
                low=detail_df['Low'], close=detail_df['Close']
            ))
            fig_detail.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_detail, use_container_width=True)

    except Exception as e:
        st.error(f"解析失敗: {e}")
else:
    st.info("🛰️ 等待指令中...")
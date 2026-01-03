import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. 網頁配置與科技感 CSS ---
st.set_page_config(page_title="NEON Real-time Terminal", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; }
    .logo-img { border-radius: 50%; border: 2px solid #00ffcc; margin-right: 15px; }
    .stock-card { 
        background-color: #1a1c24; 
        padding: 15px; 
        border-radius: 12px; 
        margin-bottom: 10px;
        border: 1px solid #2d2e38;
        display: flex;
        align-items: center;
    }
    .refresh-text { color: #00ffcc; font-size: 12px; text-align: right; font-weight: bold; }
    h3 { color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 自動刷新設置 (每 60 秒刷新一次) ---
st_autorefresh(interval=60000, key="data_refresh_counter")

# --- 3. 數據管理 (Session State) ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "IONQ", "shares": 30.0, "cost": 45.498},
        {"ticker": "EOSE", "shares": 100.0, "cost": 11.747},
        {"ticker": "ONDS", "shares": 110.0, "cost": 10.043}
    ]

# --- 4. 側邊欄：管理面板 ---
with st.sidebar:
    st.header("🛰️ 控制中心")
    with st.expander("➕ 新增/更新資產", expanded=False):
        with st.form("add_form"):
            t = st.text_input("股票代碼 (如: TSLA)").upper().strip()
            s = st.number_input("持有股數", min_value=0.0)
            c = st.number_input("平均成本 (USD)", min_value=0.0)
            if st.form_submit_button("寫入終端") and t:
                st.session_state.portfolio = [i for i in st.session_state.portfolio if i['ticker'] != t]
                st.session_state.portfolio.append({"ticker": t, "shares": s, "cost": c})
                st.rerun()

    if st.session_state.portfolio:
        with st.expander("🗑️ 移除資產項目"):
            dt = st.selectbox("選擇標的", [i['ticker'] for i in st.session_state.portfolio])
            if st.button("確認銷毀記錄"):
                st.session_state.portfolio = [i for i in st.session_state.portfolio if i['ticker'] != dt]
                st.rerun()
    
    st.divider()
    if st.button("🔴 重置系統"):
        st.session_state.portfolio = []
        st.rerun()

# --- 5. 數據核心運算 ---
if st.session_state.portfolio:
    tickers_list = [item['ticker'] for item in st.session_state.portfolio]
    
    try:
        with st.spinner('📡 數據同步中...'):
            # 同時獲取股價與匯率
            raw_data = yf.download(tickers_list + ["TWD=X"], period="5d", interval="15m", group_by='ticker', progress=False)
            usdtwd = raw_data["TWD=X"]["Close"].iloc[-1]
            
            # 自動 Logo 搜尋邏輯
            logo_dict = {}
            for t in tickers_list:
                try:
                    # 使用 cache 機制避免重複請求
                    ticker_info = yf.Ticker(t).info
                    website = ticker_info.get('website', '').replace('https://', '').replace('http://', '').split('/')[0]
                    if website:
                        logo_dict[t] = f"https://logo.clearbit.com/{website}"
                    else:
                        logo_dict[t] = f"https://ui-avatars.com/api/?name={t}&background=00ffcc&color=000"
                except:
                    logo_dict[t] = f"https://ui-avatars.com/api/?name={t}&background=00ffcc&color=000"

        results = []
        total_market_usd = 0.0
        total_cost_usd = 0.0
        portfolio_trend = None

        for item in st.session_state.portfolio:
            t = item['ticker']
            ticker_df = raw_data[t] if len(tickers_list) + 1 > 1 else raw_data
            if ticker_df.empty: continue

            curr_price = ticker_df['Close'].iloc[-1]
            mkt_val = curr_price * item['shares']
            cost_val = item['cost'] * item['shares']
            profit = mkt_val - cost_val
            
            total_market_usd += mkt_val
            total_cost_usd += cost_val

            # 累積趨勢
            stock_series = ticker_df['Close'] * item['shares']
            portfolio_trend = stock_series if portfolio_trend is None else portfolio_trend.add(stock_series, fill_value=0)

            results.append({
                "Logo": logo_dict.get(t),
                "Ticker": t, "Price": curr_price, "Value(USD)": mkt_val,
                "Profit": profit, "P%": (profit/cost_val*100) if cost_val != 0 else 0
            })

        # --- 6. UI 佈局 ---
        c_head, c_refresh = st.columns([3, 1])
        with c_head:
            st.title("⚡ 核心投資監控終端")
        with c_refresh:
            st.markdown(f"<p class='refresh-text'>LIVE • {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
        
        # KPI 指標區
        m1, m2, m3 = st.columns(3)
        total_profit = total_market_usd - total_cost_usd
        profit_pct = (total_profit / total_cost_usd * 100) if total_cost_usd != 0 else 0
        
        m1.metric("總市值 (USD)", f"${total_market_usd:,.0f}")
        m2.metric("總市值 (TWD)", f"NT$ {total_market_usd * usdtwd:,.0f}")
        m3.metric("淨損益", f"${total_profit:,.2f}", f"{profit_pct:.2f}%")

        tab1, tab2 = st.tabs(["📊 組合分析", "🔍 個股診斷"])
        
        with tab1:
            st.subheader("📋 實時持股監控")
            for res in results:
                color = "#00ffcc" if res['Profit'] >= 0 else "#ff4b4b"
                st.markdown(f"""
                <div class="stock-card">
                    <img src="{res['Logo']}" width="40" class="logo-img">
                    <div style="flex-grow:1;">
                        <span style="font-size:18px; font-weight:bold; color:white;">{res['Ticker']}</span><br>
                        <span style="color:#888; font-size:14px;">市價: ${res['Price']:.2f}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:white; font-weight:bold;">${res['Value(USD)']:,.0f}</span><br>
                        <span style="color:{color}; font-size:14px;">{res['P%']:.2f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            # 修正後的圓餅圖
            st.subheader("資產權重比例")
            fig_pie = px.pie(
                pd.DataFrame(results), 
                values='Value(USD)', 
                names='Ticker', 
                hole=0.7, 
                color_discrete_sequence=px.colors.qualitative.Safe # 使用穩定的顏色集
            )
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab2:
            selected_t = st.selectbox("選擇要分析的標的", tickers_list)
            l_col, t_col = st.columns([1, 15])
            with l_col:
                st.image(logo_dict.get(selected_t), width=60)
            with t_col:
                st.markdown(f"## {selected_t} 深度診斷")

            detail_df = raw_data[selected_t] if len(tickers_list) + 1 > 1 else raw_data
            fig_detail = go.Figure(go.Candlestick(
                x=detail_df.index, open=detail_df['Open'], high=detail_df['High'],
                low=detail_df['Low'], close=detail_df['Close']
            ))
            fig_detail.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_detail, use_container_width=True)

    except Exception as e:
        st.error(f"系統故障: {e}")
else:
    st.info("🛰️ 等待指令中... 請在左側面板新增您的資產佈局。")
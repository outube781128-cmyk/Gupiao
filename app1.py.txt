import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. 網頁配置 ---
st.set_page_config(page_title="專業級投資監測 App (美金/台幣)", layout="wide")
st.title("📊 投資組合即時追蹤系統")

# --- 2. 初始數據 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 3. 側邊欄：管理功能 ---
with st.sidebar:
    st.header("🛠 投資組合管理")
    
    with st.form("add_stock_form"):
        st.subheader("新增或更新持股")
        new_ticker = st.text_input("股票代碼 (如: NVDA, TSLA)").upper().strip()
        new_shares = st.number_input("持有股數", min_value=0.0, step=1.0)
        new_cost = st.number_input("平均成本 (USD)", min_value=0.0, step=0.01)
        submit_btn = st.form_submit_button("執行更新")
        
        if submit_btn and new_ticker:
            found = False
            for item in st.session_state.portfolio:
                if item['ticker'] == new_ticker:
                    item['shares'], item['cost'] = new_shares, new_cost
                    found = True
                    break
            if not found:
                st.session_state.portfolio.append({"ticker": new_ticker, "shares": new_shares, "cost": new_cost})
            st.success(f"已更新 {new_ticker}")
            st.rerun()

    if st.session_state.portfolio:
        st.subheader("移除持股")
        current_tickers = [item['ticker'] for item in st.session_state.portfolio]
        delete_ticker = st.selectbox("選擇要刪除的股票", current_tickers)
        if st.button("🗑 點我刪除選中股票"):
            st.session_state.portfolio = [item for item in st.session_state.portfolio if item['ticker'] != delete_ticker]
            st.warning(f"已刪除 {delete_ticker}")
            st.rerun()

    st.divider()
    if st.button("🔴 清空所有持股"):
        st.session_state.portfolio = []
        st.rerun()

# --- 4. 數據抓取與匯率換算 ---
if st.session_state.portfolio:
    tickers = [item['ticker'] for item in st.session_state.portfolio]
    
    try:
        with st.spinner('正在獲取市場行情與匯率...'):
            # 抓取股票數據 + 美金兌台幣匯率 (USDTWD=X)
            all_data = yf.download(tickers + ["TWD=X"], period="5d", interval="15m", group_by='ticker', progress=False)
            
            # 取得最新匯率
            usdtwd = all_data["TWD=X"]["Close"].iloc[-1]
            st.sidebar.info(f"💱 當前匯率: 1 USD = {usdtwd:.2f} TWD")
        
        if all_data.empty:
            st.error("無法取得數據。")
            st.stop()

        results = []
        total_cost_usd = 0.0
        total_market_value_usd = 0.0
        portfolio_trend = None

        for item in st.session_state.portfolio:
            t = item['ticker']
            ticker_df = all_data[t] if len(tickers) + 1 > 1 else all_data
            
            if ticker_df.empty or 'Close' not in ticker_df:
                continue

            current_price_usd = ticker_df['Close'].iloc[-1]
            market_value_usd = current_price_usd * item['shares']
            cost_basis_usd = item['cost'] * item['shares']
            profit_usd = market_value_usd - cost_basis_usd
            profit_pct = (profit_usd / cost_basis_usd * 100) if cost_basis_usd != 0 else 0
            
            total_cost_usd += cost_basis_usd
            total_market_value_usd += market_value_usd
            
            # 累積趨勢圖數據
            stock_series = ticker_df['Close'] * item['shares']
            portfolio_trend = stock_series if portfolio_trend is None else portfolio_trend.add(stock_series, fill_value=0)

            results.append({
                "股票": t, 
                "股數": item['shares'], 
                "成本(USD)": item['cost'],
                "市值(USD)": round(market_value_usd, 2),
                "市值(TWD)": round(market_value_usd * usdtwd, 0),
                "損益(USD)": round(profit_usd, 2), 
                "損益(TWD)": round(profit_usd * usdtwd, 0),
                "百分比": f"{profit_pct:.2f}%"
            })

        # --- 5. 儀表板顯示 ---
        total_profit_usd = total_market_value_usd - total_cost_usd
        total_profit_pct = (total_profit_usd / total_cost_usd * 100) if total_cost_usd != 0 else 0

        # 美金顯示
        st.subheader("🇺🇸 美金資產概況")
        m1, m2, m3 = st.columns(3)
        m1.metric("總市值 (USD)", f"${total_market_value_usd:,.2f}")
        m2.metric("總損益 (USD)", f"${total_profit_usd:,.2f}", f"{total_profit_pct:.2f}%")
        m3.metric("總成本 (USD)", f"${total_cost_usd:,.2f}")

        # 台幣顯示 (加強視覺效果)
        st.subheader("🇹🇼 台幣資產概況 (換算後)")
        c1, c2, c3 = st.columns(3)
        c1.metric("總市值 (TWD)", f"NT$ {total_market_value_usd * usdtwd:,.0f}")
        c2.metric("總損益 (TWD)", f"NT$ {total_profit_usd * usdtwd:,.0f}")
        c3.metric("總成本 (TWD)", f"NT$ {total_cost_usd * usdtwd:,.0f}")

        st.divider()

        # 分頁功能
        tab1, tab2, tab3 = st.tabs(["📈 趨勢分析", "🍰 資產配置", "📋 持股清單"])
        
        with tab1:
            if portfolio_trend is not None:
                fig_trend = go.Figure(go.Scatter(x=portfolio_trend.index, y=portfolio_trend.values, mode='lines', line=dict(color='#00ffcc')))
                fig_trend.update_layout(height=400, template="plotly_dark", title="資產價值走勢 (USD)")
                st.plotly_chart(fig_trend, use_container_width=True)
        
        with tab2:
            df_results = pd.DataFrame(results)
            fig_pie = px.pie(df_results, values='市值(USD)', names='股票', hole=0.4)
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with tab3:
            st.dataframe(pd.DataFrame(results), use_container_width=True)

    except Exception as e:
        st.error(f"錯誤: {e}")
else:
    st.info("💡 目前沒有持股。請從左側側邊欄輸入股票來開始追蹤！")
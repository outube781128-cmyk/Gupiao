import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. 網頁配置 ---
st.set_page_config(page_title="專業級投資監測 App", layout="wide")
st.title("📊 投資組合即時追蹤系統")

# --- 2. 初始數據與 Session State ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "IONQ", "shares": 30.0, "cost": 45.498},
        {"ticker": "EOSE", "shares": 100.0, "cost": 11.747},
        {"ticker": "ONDS", "shares": 10.0, "cost": 10.043}
    ]

# --- 3. 側邊欄：管理功能 ---
with st.sidebar:
    st.header("🛠 投資組合管理")
    with st.form("add_stock_form"):
        new_ticker = st.text_input("股票代碼 (例如: TSLA, NVDA)").upper().strip()
        new_shares = st.number_input("持有股數", min_value=0.0, step=1.0)
        new_cost = st.number_input("平均成本 (USD)", min_value=0.0, step=0.01)
        submit_btn = st.form_submit_button("更新 / 新增持股")
        
        if submit_btn and new_ticker:
            # 更新邏輯
            found = False
            for item in st.session_state.portfolio:
                if item['ticker'] == new_ticker:
                    item['shares'], item['cost'] = new_shares, new_cost
                    found = True
                    break
            if not found:
                st.session_state.portfolio.append({"ticker": new_ticker, "shares": new_shares, "cost": new_cost})
            st.success(f"已成功更新 {new_ticker}")

    if st.button("🔴 重置所有數據"):
        del st.session_state.portfolio
        st.rerun()

# --- 4. 數據抓取與核心計算 ---
if st.session_state.portfolio:
    tickers = [item['ticker'] for item in st.session_state.portfolio]
    
    try:
        # 下載數據 (5天內 15分鐘 K線)
        with st.spinner('正在獲取最新市場行情...'):
            raw_data = yf.download(tickers, period="5d", interval="15m", group_by='ticker', progress=False)
        
        if raw_data.empty:
            st.error("無法取得數據，請確認網路連接或代碼是否正確。")
            st.stop()

        results = []
        total_cost = 0.0
        total_market_value = 0.0
        portfolio_trend = None

        for item in st.session_state.portfolio:
            t = item['ticker']
            
            # 處理單一與多個股票抓取時 DataFrame 結構不同的問題
            ticker_df = raw_data[t] if len(tickers) > 1 else raw_data
            
            if ticker_df.empty or 'Close' not in ticker_df:
                st.warning(f"找不到代碼 {t} 的數據，已跳過。")
                continue

            current_price = ticker_df['Close'].iloc[-1]
            market_value = current_price * item['shares']
            cost_basis = item['cost'] * item['shares']
            profit = market_value - cost_basis
            profit_pct = (profit / cost_basis * 100) if cost_basis != 0 else 0
            
            total_cost += cost_basis
            total_market_value += market_value
            
            # 累積趨勢圖數據
            stock_series = ticker_df['Close'] * item['shares']
            if portfolio_trend is None:
                portfolio_trend = stock_series
            else:
                portfolio_trend = portfolio_trend.add(stock_series, fill_value=0)

            results.append({
                "股票": t, "股數": item['shares'], "平均成本": item['cost'],
                "目前市價": round(current_price, 2), "市值": round(market_value, 2),
                "損益": round(profit, 2), "百分比": f"{profit_pct:.2f}%"
            })

        # --- 5. 儀表板顯示 ---
        total_profit = total_market_value - total_cost
        total_profit_pct = (total_profit / total_cost * 100) if total_cost != 0 else 0

        # KPI 指標排版
        m1, m2, m3 = st.columns(3)
        m1.metric("總資產市值", f"${total_market_value:,.2f}")
        m2.metric("總損益額", f"${total_profit:,.2f}", f"{total_profit_pct:.2f}%")
        m3.metric("投入總成本", f"${total_cost:,.2f}")

        st.divider()

        # 分頁功能
        tab1, tab2, tab3 = st.tabs(["📈 趨勢分析", "🍰 資產配置", "📋 持股清單"])

        with tab1:
            st.subheader("投資組合總價值走勢 (近5日)")
            if portfolio_trend is not None:
                fig_trend = go.Figure(go.Scatter(
                    x=portfolio_trend.index, 
                    y=portfolio_trend.values, 
                    mode='lines', 
                    name='總市值',
                    line=dict(color='#00ffcc', width=2)
                ))
                fig_trend.update_layout(
                    height=450, 
                    template="plotly_dark",
                    xaxis_title="時間",
                    yaxis_title="市值 (USD)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_trend, use_container_width=True)

        with tab2:
            st.subheader("各標的權重比例")
            df_results = pd.DataFrame(results)
            fig_pie = px.pie(
                df_results, 
                values='市值', 
                names='股票', 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(template="plotly_dark", height=450)
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab3:
            st.subheader("詳細持股明細")
            # 格式化顯示
            st.dataframe(
                pd.DataFrame(results).style.applymap(
                    lambda x: 'color: #ff4b4b' if '-' in str(x) else 'color: #00ff00', 
                    subset=['損益', '百分比']
                ), 
                use_container_width=True
            )

    except Exception as e:
        st.error(f"系統發生非預期錯誤: {e}")
else:
    st.info("目前投資組合為空，請使用左側工具列新增股票。")
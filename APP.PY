import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 初始化
dl = DataLoader()

st.set_page_config(layout="wide", page_title="台股成交量密集區分析工具")

# --- 側邊欄設定 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330")
start_date = st.sidebar.date_input("開始日期", value=pd.to_datetime("2026-02-01"))
bin_size = st.sidebar.slider("價格區間精細度 (Bins)", 20, 100, 50)

# --- 資料處理邏輯 ---
def process_and_calculate_vp(df, bins=50):
    # 1. 欄位自動對齊 (Map FinMind columns to standard names)
    rename_map = {
        'max': 'high',
        'min': 'low',
        'Trading_Volume': 'Volume'
    }
    df = df.rename(columns=rename_map)
    
    # 2. 計算成交量分佈
    df['price_bin'] = pd.cut(df['close'], bins=bins)
    vp = df.groupby('price_bin', observed=True)['Volume'].sum().reset_index()
    vp['price_mid'] = vp['price_bin'].apply(lambda x: x.mid)
    return df, vp

# --- 主程式 ---
try:
    # 抓取資料
    df_raw = dl.taiwan_stock_daily(
        stock_id=stock_id,
        start_date=start_date.strftime('%Y-%m-%d')
    )

    if df_raw is None or df_raw.empty:
        st.warning("⚠️ 此區間查無資料，請檢查日期設定（避開假日或設定更早的日期）。")
    else:
        # 處理資料
        df, vp_data = process_and_calculate_vp(df_raw, bin_size)
        poc_price = vp_data.loc[vp_data['Volume'].idxmax(), 'price_mid']

        st.title(f"📊 {stock_id} 成交量集結區間分析")

        # --- 繪圖 ---
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                           column_widths=[0.75, 0.25], horizontal_spacing=0.03,
                           subplot_titles=("K線走勢", "成交量分佈 (Volume Profile)"))

        # 左圖：K線
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'],
                                     low=df['low'], close=df['close'], name="K線"), row=1, col=1)

        # 右圖：橫向成交量
        fig.add_trace(go.Bar(x=vp_data['Volume'], y=vp_data['price_mid'], 
                             orientation='h', name='成交量',
                             marker_color='rgba(100, 150, 255, 0.6)'), row=1, col=2)

        # 標註 POC
        fig.add_hline(y=poc_price, line_dash="dash", line_color="red", 
                      annotation_text=f"大量區: {poc_price}", row=1, col=1)

        fig.update_layout(height=700, showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

      # --- 數據面板：中文化與美化優化版 ---
        st.subheader("💡 關鍵分析看板")
        col_metric, col_table = st.columns([1, 2])
        
        with col_metric:
            st.metric("當前最大量成交價 (POC)", f"{poc_price:.2f} 元")
            st.write("---")
            st.caption("註：紅虛線代表此區間內成交量最集中的位置，通常具有強大的支撐或壓力力道。")
            
        with col_table:
            st.write("📋 **成交量最集中價格區間排名**")
            
            # 取得前三大區間資料
            top_3_df = vp_data.nlargest(3, 'Volume').copy()
            
            # 格式化表格內容：
            # 1. 價格區間轉為中文字串 (1764.57 ~ 1775.32)
            top_3_df['價格區間'] = top_3_df['price_bin'].apply(lambda x: f"{x.left:.2f} ~ {x.right:.2f}")
            
            # 2. 成交量轉為「萬張」或加上千分位，並改中文名
            top_3_df['累積成交量 (張)'] = top_3_df['Volume'].apply(lambda x: f"{int(x):,}")
            
            # 3. 排除掉不必要的欄位與 Index 序號
            display_df = top_3_df[['價格區間', '累積成交量 (張)']].reset_index(drop=True)
            
            # 顯示表格 (使用 st.dataframe 或 st.table)
            st.table(display_df)

except Exception as e:
    st.error(f"執行出錯: {e}")
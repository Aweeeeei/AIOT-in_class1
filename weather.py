import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 設定頁面標題與佈局
st.set_page_config(page_title="台灣各地天氣預報", layout="centered")
st.title("🌦️ 台灣各地天氣預報 (36小時)")

# 資料庫連線函式
def get_connection():
    return sqlite3.connect("data.db")

# 格式化時間函式 (將 2025-12-04 18:00:00 轉為 12/4 18:00)
def format_time_display(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return f"{dt.month}/{dt.day} {dt.hour:02d}:{dt.minute:02d}"
    except ValueError:
        return time_str

# 主程式邏輯
def main():
    conn = get_connection()

    # 1. 讀取所有唯一的「地點」供使用者選擇
    try:
        locations_df = pd.read_sql("SELECT DISTINCT location FROM forecasts", conn)
        location_list = locations_df['location'].tolist()
    except Exception as e:
        st.error(f"讀取資料庫失敗，請確認是否已執行 get_weather.py 產生 data.db。錯誤訊息: {e}")
        return

    # 2. 讀取所有唯一的「開始時間」並進行排序
    # 我們需要原始時間字串來查詢資料庫，但顯示給使用者看的是格式化後的時間
    try:
        times_df = pd.read_sql("SELECT DISTINCT start_time, end_time FROM forecasts ORDER BY start_time", conn)
        
        # 建立一個 對應字典 { "顯示文字": "原始時間字串" }
        # 例如: { "12/4 18:00": "2025-12-04 18:00:00" }
        time_options = {}
        for _, row in times_df.iterrows():
            display_text = format_time_display(row['start_time'])
            # 為了讓選項更清楚，可以選擇是否要加上結束時間，這裡依照你的需求只顯示起始時間
            time_options[display_text] = row['start_time']
            
    except Exception as e:
        st.error(f"讀取時間資料失敗: {e}")
        return

    # --- 側邊欄選項 ---
    with st.sidebar:
        st.header("🔍 查詢條件")
        
        # 地點選擇
        selected_location = st.selectbox("選擇縣市", location_list)
        
        # 時間選擇 (直接使用格式化後的 keys)
        selected_display_time = st.selectbox("選擇預報時段 (起始時間)", list(time_options.keys()))
        
        # 透過字典找回原始的時間字串，用於 SQL 查詢
        selected_start_time_raw = time_options[selected_display_time]

    # --- 撈取特定資料 ---
    query = """
    SELECT * FROM forecasts 
    WHERE location = ? AND start_time = ?
    """
    df_result = pd.read_sql(query, conn, params=(selected_location, selected_start_time_raw))

    if not df_result.empty:
        data = df_result.iloc[0]
        
        # 顯示時段資訊
        end_time_display = format_time_display(data['end_time'])
        st.info(f"📅 預報有效時段: **{selected_display_time}** 至 **{end_time_display}**")

        # --- 顯示主要天氣指標 ---
        # 使用 columns 讓版面並排顯示
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(label="天氣現象", value=data['weather_condition'])
            st.metric(label="降雨機率", value=f"{data['rain_prob']}%")
            
        with col2:
            # 溫度顯示為區間
            temp_range = f"{data['min_temp']}°C - {data['max_temp']}°C"
            st.metric(label="氣溫", value=temp_range)
            st.metric(label="舒適度", value=data['comfort_index'])

        st.divider()
        
        # (選用) 顯示同一時段全台摘要 Table
        with st.expander(f"查看 {selected_display_time} 全台概況"):
            all_loc_query = "SELECT location, weather_condition, min_temp, max_temp FROM forecasts WHERE start_time = ?"
            df_all = pd.read_sql(all_loc_query, conn, params=(selected_start_time_raw,))
            st.dataframe(df_all, hide_index=True)

    else:
        st.warning("查無此條件的資料。")

    conn.close()

if __name__ == "__main__":
    main()
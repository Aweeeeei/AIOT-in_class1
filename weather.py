import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json
import urllib.request
from datetime import datetime

# 設定頁面 (設為 wide 模式地圖會比較大比較好看)
st.set_page_config(page_title="台灣天氣地圖", layout="wide")
st.title("🗺️ 台灣各地天氣預報地圖")

# --- 1. 取得台灣縣市 GeoJSON ---
@st.cache_data
def get_taiwan_geojson():
    # 使用網路上開源的台灣縣市 GeoJSON (來源: g0v/twgeojson)
    # 這個版本的縣市名稱格式 (e.g., "臺北市") 與氣象局一致
    url = "https://raw.githubusercontent.com/donma/Taiwan.json/master/Taiwan_County.json"
    try:
        with urllib.request.urlopen(url) as response:
            geojson = json.loads(response.read().decode())
        return geojson
    except Exception as e:
        st.error(f"無法下載地圖資料: {e}")
        return None

# --- 2. 資料庫連線與處理 ---
def get_connection():
    return sqlite3.connect("data.db")

def format_time_display(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return f"{dt.month}/{dt.day} {dt.hour:02d}:{dt.minute:02d}"
    except ValueError:
        return time_str

def load_data():
    conn = get_connection()
    try:
        # 讀取所有資料
        df = pd.read_sql("SELECT * FROM forecasts", conn)
        
        # 資料型態轉換：將溫度與降雨機率轉為數字，以便地圖上色
        df['min_temp'] = pd.to_numeric(df['min_temp'])
        df['max_temp'] = pd.to_numeric(df['max_temp'])
        df['rain_prob'] = pd.to_numeric(df['rain_prob'])
        
        # 建立一個整合的欄位用於 Hover 顯示 (HTML 格式)
        # 這裡我們預先組好字串，也可以直接透過 plotly 設定
        df['hover_info'] = (
            "天氣: " + df['weather_condition'] + "<br>" +
            "氣溫: " + df['min_temp'].astype(str) + "°C - " + df['max_temp'].astype(str) + "°C<br>" +
            "降雨機率: " + df['rain_prob'].astype(str) + "%<br>" +
            "舒適度: " + df['comfort_index']
        )
        return df
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- 主程式 ---
def main():
    geojson = get_taiwan_geojson()
    df = load_data()

    if df.empty or not geojson:
        st.warning("無資料可顯示，請檢查 data.db 或網路連線。")
        return

    # --- 時間篩選器 ---
    # 取得唯一的時間點並排序
    unique_times = df[['start_time', 'end_time']].drop_duplicates().sort_values('start_time')
    
    # 製作選單字典
    time_options = {}
    for _, row in unique_times.iterrows():
        display = format_time_display(row['start_time'])
        time_options[display] = row['start_time']

    # 側邊欄
    with st.sidebar:
        st.header("控制面板")
        selected_display_time = st.selectbox("選擇預報時間", list(time_options.keys()))
        
        # 選擇地圖上色的依據
        color_metric = st.radio("地圖顏色依據", ["最高溫 (MaxT)", "降雨機率 (PoP)"], index=0)

    # 根據選擇的時間篩選資料
    selected_start_time = time_options[selected_display_time]
    df_filtered = df[df['start_time'] == selected_start_time].copy()

    # 設定地圖上色的欄位
    if color_metric == "最高溫 (MaxT)":
        color_col = "max_temp"
        color_scale = "RdOr" # 紅橘色系代表溫度
        label_legend = "最高溫 (°C)"
    else:
        color_col = "rain_prob"
        color_scale = "Blues" # 藍色系代表雨
        label_legend = "降雨機率 (%)"

    # --- 繪製地圖 (Plotly) ---
    # 這裡的重點是 locations 對應到 geojson 中的 properties.Name (或類似欄位)
    # 我們使用的 GeoJSON 縣市名稱在 feature.properties.CityName 或 Name
    
    fig = px.choropleth_mapbox(
        df_filtered,
        geojson=geojson,
        locations='location',          # Dataframe 中對應縣市名稱的欄位
        featureidkey="properties.Name",# GeoJSON 中對應縣市名稱的路徑 (這個 GeoJSON 使用 Name)
        color=color_col,               # 決定顏色的數值
        color_continuous_scale=color_scale,
        range_color=(df[color_col].min(), df[color_col].max()), # 固定顏色範圍，避免切換時間時顏色跳動
        mapbox_style="carto-positron", # 地圖底圖樣式 (乾淨風格)
        zoom=6.5,
        center={"lat": 23.97565, "lon": 120.9738819}, # 台灣中心點
        opacity=0.7,
        labels={color_col: label_legend},
        # 設定 Hover 顯示的資訊
        hover_name='location',
        hover_data={
            'location': False,        # 標題已經顯示地點，這裡隱藏
            color_col: False,         # 隱藏預設的顏色數值
            'start_time': False,      # 隱藏時間
            'end_time': False,        # 隱藏時間
            'weather_condition': True,# 顯示天氣
            'min_temp': True,         # 顯示最低溫
            'max_temp': True,         # 顯示最高溫
            'rain_prob': True,        # 顯示降雨
            'comfort_index': True     # 顯示舒適度
        }
    )

    # 客製化 Hover 的標籤顯示文字 (讓它是中文)
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                      "天氣: %{customdata[2]}<br>" +
                      "氣溫: %{customdata[3]}°C - %{customdata[4]}°C<br>" +
                      "降雨機率: %{customdata[5]}%<br>" +
                      "舒適度: %{customdata[6]}"
    )

    # 調整地圖邊界與 Layout
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    # 在 Streamlit 顯示
    st.info(f"目前顯示預報時間: {selected_display_time}")
    st.plotly_chart(fig, use_container_width=True)
    
    # 下方顯示詳細資料表格 (選用)
    with st.expander("查看詳細數據表格"):
        st.dataframe(df_filtered.drop(columns=['id', 'start_time', 'end_time', 'hover_info']), hide_index=True)

if __name__ == "__main__":
    main()
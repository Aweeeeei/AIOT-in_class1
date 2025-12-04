import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json
import requests
from datetime import datetime

# 設定頁面
st.set_page_config(page_title="台灣天氣地圖", layout="wide")
st.title("🗺️ 台灣各地天氣預報地圖")

# --- 1. 取得台灣縣市 GeoJSON (修正版) ---
@st.cache_data
def get_taiwan_geojson():
    # 改用 g0v 的 GeoJSON (2010年縣市界)
    # 檔案大小約 8MB，第一次載入會稍久，cache_data 會幫忙快取
    url = "https://raw.githubusercontent.com/g0v/twgeojson/master/json/twCounty2010.geo.json"
    try:
        response = requests.get(url)
        response.raise_for_status() # 檢查 404
        geojson = response.json()
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
        df = pd.read_sql("SELECT * FROM forecasts", conn)
        
        # 1. 數值轉換：將字串轉為數字，以便地圖上色
        df['min_temp'] = pd.to_numeric(df['min_temp'])
        df['max_temp'] = pd.to_numeric(df['max_temp'])
        df['rain_prob'] = pd.to_numeric(df['rain_prob'])
        
        # 2. 名稱修正：解決地圖空白問題
        # (A) 統一將氣象局的「臺」轉為地圖檔常用的「台」 (解決 臺北、臺中、臺南、臺東)
        df['location'] = df['location'].str.replace('臺', '台')

        # (B) 處理 2010 年舊地圖的行政區名稱 (解決 新北->台北縣, 桃園市->桃園縣)
        county_mapping = {
            '桃園市': '桃園縣',
            '新北市': '臺北縣',
            # 針對 2010 年圖資，台中/台南/高雄 其實分縣與市，這裡我們先對應到「市」
            # 這樣至少市中心會有顏色
        }
        df['location'] = df['location'].replace(county_mapping)

        # 3. 建立 Hover 資訊 (這就是原本漏掉的關鍵部分！)
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

    if df.empty:
        st.warning("⚠️ 讀取不到天氣資料，請確認 data.db 是否存在且已執行 get_weather.py。")
        return
        
    if not geojson:
        st.warning("⚠️ 地圖資料下載失敗，請檢查網路連線。")
        return

    # --- 時間篩選器 ---
    unique_times = df[['start_time', 'end_time']].drop_duplicates().sort_values('start_time')
    time_options = {}
    for _, row in unique_times.iterrows():
        display = format_time_display(row['start_time'])
        time_options[display] = row['start_time']

    # 側邊欄
    with st.sidebar:
        st.header("控制面板")
        selected_display_time = st.selectbox("選擇預報時間", list(time_options.keys()))
        color_metric = st.radio("地圖顏色依據", ["最高溫 (MaxT)", "降雨機率 (PoP)"], index=0)

    # 篩選資料
    selected_start_time = time_options[selected_display_time]
    df_filtered = df[df['start_time'] == selected_start_time].copy()

    # 設定顏色參數
    if color_metric == "最高溫 (MaxT)":
        color_col = "max_temp"
        color_scale = "OrRd"
        label_legend = "最高溫 (°C)"
    else:
        color_col = "rain_prob"
        color_scale = "Blues"
        label_legend = "降雨機率 (%)"

    # --- 繪製地圖 ---
    fig = px.choropleth_mapbox(
        df_filtered,
        geojson=geojson,
        locations='location',           # DataFrame 的地名
        featureidkey="properties.COUNTYNAME", # g0v GeoJSON 的地名 Key 是 COUNTYNAME
        color=color_col,
        color_continuous_scale=color_scale,
        range_color=(df[color_col].min(), df[color_col].max()),
        mapbox_style="carto-positron",
        zoom=6.5,
        center={"lat": 23.97565, "lon": 120.9738819},
        opacity=0.7,
        labels={color_col: label_legend},
        hover_name='location',
        hover_data={
            'location': False,
            color_col: False,
            'start_time': False,
            'end_time': False,
            'weather_condition': True,
            'min_temp': True,
            'max_temp': True,
            'rain_prob': True,
            'comfort_index': True,
            'hover_info': False # 不顯示這個輔助欄位
        }
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                      "天氣: %{customdata[0]}<br>" +
                      "氣溫: %{customdata[1]}°C - %{customdata[2]}°C<br>" +
                      "降雨機率: %{customdata[3]}%<br>" +
                      "舒適度: %{customdata[4]}"
    )
    
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    st.info(f"目前顯示預報時間: {selected_display_time}")
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
import requests
import sqlite3
import pandas as pd

# 請將此處替換為你的 CWA API Key
API_KEY = "CWA-1FFDDAEC-161F-46A3-BE71-93C32C52829F"
URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"

def fetch_weather_data():
    params = {
        "Authorization": API_KEY
    }
    
    print("正在下載資料: F-C0032-001...")
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status() # 檢查請求是否成功
        data = response.json()
        
        if data.get('success') == 'true':
            return data['records']
        else:
            print("API 回傳失敗，請檢查 API Key 或參數。")
            return None
    except Exception as e:
        print(f"連線發生錯誤: {e}")
        return None

def save_to_db(records):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # 1. 建立資料表
    # 我們將 location, start_time, end_time 做為複合唯一鍵，避免重複插入資料
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT,
        start_time TEXT,
        end_time TEXT,
        weather_condition TEXT,
        rain_prob TEXT,
        min_temp TEXT,
        max_temp TEXT,
        comfort_index TEXT,
        UNIQUE(location, start_time, end_time) ON CONFLICT REPLACE
    )
    ''')

    # 2. 解析資料並準備插入
    # 資料結構: records -> location list -> weatherElement list -> time list
    locations = records.get('location', [])
    
    insert_list = []

    for loc in locations:
        loc_name = loc['locationName']
        
        # 為了方便取用，將 weatherElement 轉換成以 elementName 為 Key 的字典
        # 例如: weather_map['Wx'] 會拿到該地點 Wx 的時間列表
        weather_map = {item['elementName']: item['time'] for item in loc['weatherElement']}
        
        # 根據 API 結構，每個 Element 都有 3 個時間段 (0, 1, 2)
        # 我們假設所有 Element 的時間段都是對齊的，所以以 'Wx' 的長度為準進行迴圈
        time_segments = weather_map.get('Wx', [])
        
        for i in range(len(time_segments)):
            # 抓取基本時間資訊 (從 Wx 裡面抓即可)
            start_time = time_segments[i]['startTime']
            end_time = time_segments[i]['endTime']
            
            # 抓取各項天氣數值 (使用 get 避免 KeyError，並取 parameterName)
            # Wx: 天氣現象
            wx = weather_map['Wx'][i]['parameter']['parameterName']
            
            # PoP: 降雨機率 (JSON中是字串 '0', '10' 等)
            pop = weather_map['PoP'][i]['parameter']['parameterName']
            
            # MinT: 最低溫度
            min_t = weather_map['MinT'][i]['parameter']['parameterName']
            
            # MaxT: 最高溫度
            max_t = weather_map['MaxT'][i]['parameter']['parameterName']
            
            # CI: 舒適度
            ci = weather_map['CI'][i]['parameter']['parameterName']
            
            # 加入列表準備寫入資料庫
            insert_list.append((
                loc_name, start_time, end_time, wx, pop, min_t, max_t, ci
            ))

    # 3. 批量寫入資料庫
    cursor.executemany('''
    INSERT INTO forecasts (location, start_time, end_time, weather_condition, rain_prob, min_temp, max_temp, comfort_index)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', insert_list)

    conn.commit()
    print(f"成功更新資料庫！共寫入 {len(insert_list)} 筆資料。")
    
    # 4. (選用) 簡單驗證：印出前 5 筆資料確認
    print("\n--- 資料庫預覽 (前 5 筆) ---")
    df = pd.read_sql("SELECT * FROM forecasts LIMIT 5", conn)
    print(df)

    conn.close()

if __name__ == "__main__":
    records = fetch_weather_data()
    if records:
        save_to_db(records)
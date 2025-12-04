# 🗺️ 台灣天氣預報地圖 (Taiwan Weather Map)

這是一個使用 Python 與 Streamlit 製作的互動式台灣天氣地圖，視覺化呈現中央氣象署 (CWA) 的未來 36 小時天氣預報。

## 🚀 使用步驟

### 步驟 1：下載與更新資料
下載專案程式碼後，請確保 `get_weather.py` 中已填入你的 API Key，接著在終端機執行以下指令來產生資料庫：

```bash
# 執行資料抓取程式
python get_weather.py
```

執行成功後，目錄下會產生一個 data.db 檔案，這就是地圖的資料來源。

### 步驟 2：上傳與部署
1. 將完整的專案資料夾（包含 weather.py, get_weather.py, requirements.txt 以及剛剛產生的 data.db）上傳至 GitHub。

2. 前往 Streamlit Cloud 並登入。

3. 點選 New app，選擇你的 GitHub Repository。

4. Main file path 選擇 weather.py。

5. 點擊 Deploy 按鈕，等待部署完成。

## 🔗 範例網站

你可以點擊下方連結查看部署後的實際效果：

https://aiot-inclass1.streamlit.app/
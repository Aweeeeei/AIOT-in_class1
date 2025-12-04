import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_movies():
    # 建立一個列表來儲存所有爬取到的電影資料
    movie_data = []
    
    # 基礎 URL 結構
    base_url = "https://ssr1.scrape.center/page/{}"

    # 迴圈遍歷第 1 頁到第 10 頁
    for page in range(1, 11):
        url = base_url.format(page)
        print(f"正在爬取第 {page} 頁: {url}")
        
        try:
            # 發送 GET請求
            response = requests.get(url)
            
            # 檢查請求是否成功 (狀態碼 200)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 找到該頁面上所有的電影卡片 (根據網站結構，通常在 el-card class 中)
                items = soup.find_all('div', class_='el-card')
                
                for item in items:
                    # 1. 擷取電影名稱 (在 h2 標籤內)
                    title_tag = item.find('h2')
                    title = title_tag.text.strip() if title_tag else "未知名稱"
                    
                    # 2. 擷取圖片 URL (在 img 標籤的 src 屬性)
                    img_tag = item.find('img', class_='cover')
                    img_url = img_tag['src'] if img_tag else "無圖片"
                    
                    # 3. 擷取評分 (在 p 標籤 class='score' 內)
                    score_tag = item.find('p', class_='score')
                    score = score_tag.text.strip() if score_tag else "無評分"
                    
                    # 4. 擷取類型 (在 class='categories' 內的 button 標籤)
                    categories_div = item.find('div', class_='categories')
                    if categories_div:
                        # 找到所有按鈕並取得文字，然後用逗號合併
                        buttons = categories_div.find_all('button')
                        categories = ", ".join([btn.text.strip() for btn in buttons])
                    else:
                        categories = "無分類"
                    
                    # 將這部電影的資訊加入列表
                    movie_data.append({
                        '電影名稱': title,
                        '評分': score,
                        '類型': categories,
                        '圖片 URL': img_url
                    })
            else:
                print(f"無法讀取第 {page} 頁，狀態碼: {response.status_code}")
                
        except Exception as e:
            print(f"爬取第 {page} 頁時發生錯誤: {e}")
        
        # 禮貌性延遲 1 秒，避免對伺服器造成過大負擔
        time.sleep(1)

    # 將資料轉換為 DataFrame
    df = pd.DataFrame(movie_data)
    
    # 儲存成 csv 檔案
    # encoding='utf-8-sig' 是為了讓 Excel 開啟時中文能正常顯示
    df.to_csv('movie.csv', index=False, encoding='utf-8-sig')
    
    print("-" * 30)
    print(f"爬取完成！共抓取 {len(df)} 部電影。")
    print("檔案已儲存為 movie.csv")

if __name__ == "__main__":
    scrape_movies()
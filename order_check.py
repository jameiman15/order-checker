import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib3
import traceback

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 從 GitHub Secrets 讀取設定
USERNAME = os.environ.get('ELIFE_USERNAME')
PASSWORD = os.environ.get('ELIFE_PASSWORD') 
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')

def create_session():
    """創建優化的 requests session"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.8,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    session.headers.update(headers)
    
    return session

def send_email(subject, body):
    """發送郵件通知"""
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        
        print("✅ 郵件發送成功")
        return True
    except Exception as e:
        print(f"❌ 郵件發送失敗: {e}")
        return False

def login_to_website(session):
    """登入全國電子廠商系統"""
    urls = [
        "https://www.elifemall.com.tw/vendor/",
        "http://www.elifemall.com.tw/vendor/",
    ]
    
    for url in urls:
        try:
            print(f"嘗試連接: {url}")
            response = session.get(url, timeout=30, verify=False)
            
            if response.status_code == 200:
                print(f"✅ 連接成功: {url}")
                
                # 解析登入表單
                soup = BeautifulSoup(response.text, 'html.parser')
                forms = soup.find_all('form')
                
                if forms:
                    form = forms[0]
                    login_data = {}
                    
                    # 設定基本登入資料
                    login_data['mno'] = USERNAME
                    login_data['mpasswd'] = PASSWORD
                    
                    # 處理隱藏欄位
                    for inp in form.find_all('input', type='hidden'):
                        if inp.get('name') and inp.get('value'):
                            login_data[inp.get('name')] = inp.get('value')
                    
                    # 找到登入表單的 action
                    action = form.get('action', url)
                    if not action.startswith('http'):
                        base_url = '/'.join(url.split('/')[:3])
                        if action.startswith('/'):
                            action = base_url + action
                        else:
                            action = url.rstrip('/') + '/' + action.lstrip('/')
                    
                    print(f"提交登入到: {action}")
                    
                    # 提交登入表單
                    login_response = session.post(action, data=login_data, timeout=30, verify=False, allow_redirects=True)
                    
                    # 檢查登入結果
                    success_keywords = ["廠商", "商品", "訂單", "menu", "logout", "登出"]
                    login_success = any(keyword in login_response.text for keyword in success_keywords)
                    
                    if login_success:
                        print("✅ 登入成功")
                        return True, login_response, session
                    else:
                        print("❌ 登入失敗，檢查帳號密碼")
                        # 檢查是否有錯誤訊息
                        if "錯誤" in login_response.text or "error" in login_response.text.lower():
                            print("發現登入錯誤訊息")
                        return False, login_response, session
                else:
                    print("❌ 未找到登入表單")
                    
        except requests.exceptions.Timeout:
            print(f"❌ {url} - 連接超時")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {url} - 連接錯誤: {e}")
        except Exception as e:
            print(f"❌ {url} - 其他錯誤: {e}")
            
    return False, None, session

def check_orders(session):
    """檢查訂單狀態（這裡可以加入具體的訂單查詢邏輯）"""
    try:
        # 這裡可以加入訂單頁面的抓取和分析邏輯
        # 例如：抓取訂單列表、檢查新訂單、分析訂單狀態等
        
        print("🔍 開始檢查訂單...")
        
        # 示例：嘗試訪問訂單頁面
        order_urls = [
            "https://www.elifemall.com.tw/vendor/order_list.php",
            "https://www.elifemall.com.tw/vendor/orders.php",
        ]
        
        for url in order_urls:
            try:
                response = session.get(url, timeout=30, verify=False)
                if response.status_code == 200:
                    print(f"✅ 成功訪問訂單頁面: {url}")
                    # 這裡可以解析訂單內容
                    # soup = BeautifulSoup(response.text, 'html.parser')
                    # 分析訂單數據...
                    return {"status": "success", "orders": "訂單檢查完成"}
            except Exception as e:
                print(f"❌ 無法訪問 {url}: {e}")
                
        return {"status": "success", "orders": "登入成功，訂單檢查功能需進一步開發"}
        
    except Exception as e:
        print(f"❌ 訂單檢查錯誤: {e}")
        return {"status": "error", "error": str(e)}

def main():
    start_time = datetime.now()
    print("=" * 50)
    print("🤖 GitHub Actions 訂單檢查系統")
    print(f"⏰ 執行時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 50)
    
    # 檢查必要的環境變數
    required_vars = ['ELIFE_USERNAME', 'ELIFE_PASSWORD', 'GMAIL_USER', 'GMAIL_PASSWORD', 'RECEIVER_EMAIL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        error_msg = f"❌ 缺少必要的環境變數: {', '.join(missing_vars)}"
        print(error_msg)
        send_email("【訂單檢查】設定錯誤", f"缺少環境變數：{missing_vars}")
        return
    
    try:
        # 建立 session
        session = create_session()
        
        # 嘗試登入
        login_success, response, session = login_to_website(session)
        
        if login_success:
            print("🎉 系統登入成功！")
            
            # 檢查訂單
            order_result = check_orders(session)
            
            # 計算執行時間
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 發送成功報告
            subject = "【訂單檢查】✅ 執行成功"
            body = f"""🤖 GitHub Actions 訂單檢查報告

✅ 執行狀態：成功
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
⌛ 執行耗時：{duration:.2f} 秒
🌐 執行環境：GitHub Actions (免費)

📊 檢查結果：
- 網站連接：✅ 正常
- 系統登入：✅ 成功
- 訂單檢查：{order_result.get('status', '未知')}

📝 詳細資訊：
{order_result.get('orders', '無額外資訊')}

🔄 下次執行：根據排程自動執行
🎯 系統狀態：運作正常

---
此郵件由 GitHub Actions 自動發送"""
            
            send_email(subject, body)
            
        else:
            print("❌ 登入失敗")
            
            # 發送失敗報告
            subject = "【訂單檢查】❌ 登入失敗"
            body = f"""🤖 GitHub Actions 訂單檢查報告

❌ 執行狀態：登入失敗
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
🌐 執行環境：GitHub Actions

❗ 問題說明：
無法登入全國電子廠商系統

💡 可能原因：
1. 帳號密碼錯誤
2. 網站結構變更
3. 網站臨時維護

🔧 建議處理：
1. 檢查 GitHub Secrets 中的帳號密碼
2. 確認網站是否正常運作
3. 檢查程式碼是否需要更新

🔄 下次執行：根據排程自動執行

---
此郵件由 GitHub Actions 自動發送"""
            
            send_email(subject, body)
            
    except Exception as e:
        print(f"💥 執行錯誤: {e}")
        print(traceback.format_exc())
        
        # 發送錯誤報告
        subject = "【訂單檢查】💥 系統錯誤"
        body = f"""🤖 GitHub Actions 訂單檢查報告

💥 執行狀態：系統錯誤
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
🌐 執行環境：GitHub Actions

❗ 錯誤訊息：
{str(e)}

🔍 詳細追蹤：
{traceback.format_exc()}

🔄 下次執行：根據排程自動執行

---
此郵件由 GitHub Actions 自動發送"""
        
        send_email(subject, body)

if __name__ == "__main__":
    main()

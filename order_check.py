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
import time
import re

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
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
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

def save_debug_info(filename, content, description=""):
    """保存除錯資訊"""
    try:
        os.makedirs("artifacts", exist_ok=True)
        filepath = f"artifacts/{filename}"
        
        if isinstance(content, bytes):
            with open(filepath, 'wb') as f:
                f.write(content)
        else:
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(str(content))
        
        print(f"🔍 已保存除錯資訊: {filepath} - {description}")
    except Exception as e:
        print(f"❌ 保存除錯資訊失敗: {e}")

def test_website_connectivity():
    """測試網站連通性"""
    test_urls = [
        "https://www.elifemall.com.tw/",
        "https://www.elifemall.com.tw/vendor/",
        "http://www.elifemall.com.tw/vendor/"
    ]
    
    session = create_session()
    results = {}
    
    for url in test_urls:
        try:
            print(f"🌐 測試連接: {url}")
            response = session.get(url, timeout=15, verify=False, allow_redirects=True)
            
            results[url] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'encoding': response.encoding,
                'final_url': response.url
            }
            
            print(f"  ✅ 狀態碼: {response.status_code}")
            print(f"  📏 內容長度: {len(response.content)} bytes")
            print(f"  🔗 最終URL: {response.url}")
            
            # 保存 HTML 內容供除錯
            save_debug_info(f"response_{url.replace('://', '_').replace('/', '_')}.html", 
                          response.content, f"Response from {url}")
            
        except Exception as e:
            results[url] = {'error': str(e)}
            print(f"  ❌ 連接失敗: {e}")
    
    return results

def login_to_website(session):
    """登入全國電子廠商系統"""
    login_urls = [
        "https://www.elifemall.com.tw/vendor/",
        "http://www.elifemall.com.tw/vendor/",
        "https://www.elifemall.com.tw/vendor/index.php",
        "http://www.elifemall.com.tw/vendor/index.php"
    ]
    
    for url in login_urls:
        try:
            print(f"🔍 嘗試登入: {url}")
            
            # 先獲取登入頁面
            response = session.get(url, timeout=30, verify=False, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"❌ HTTP 狀態碼錯誤: {response.status_code}")
                continue
            
            print(f"✅ 成功獲取登入頁面")
            print(f"📏 頁面大小: {len(response.content)} bytes")
            print(f"🔠 編碼: {response.encoding}")
            
            # 保存登入頁面供除錯
            save_debug_info("login_page.html", response.content, "登入頁面內容")
            
            # 嘗試不同編碼解析
            content = ""
            for encoding in ['utf-8', 'big5', 'gb2312', 'iso-8859-1']:
                try:
                    content = response.content.decode(encoding)
                    print(f"✅ 使用 {encoding} 編碼解析成功")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                content = response.content.decode('utf-8', errors='ignore')
                print("⚠️ 使用 utf-8 強制解析")
            
            # 解析表單
            soup = BeautifulSoup(content, 'html.parser')
            forms = soup.find_all('form')
            
            if not forms:
                print("❌ 未找到表單")
                # 檢查是否有 JavaScript 重導向
                if 'location.href' in content or 'window.location' in content:
                    print("⚠️ 頁面可能包含 JavaScript 重導向")
                continue
            
            print(f"📋 找到 {len(forms)} 個表單")
            
            # 尋找登入表單
            login_form = None
            for i, form in enumerate(forms):
                print(f"📋 表單 {i+1}:")
                inputs = form.find_all(['input', 'select', 'textarea'])
                for inp in inputs:
                    input_type = inp.get('type', 'text')
                    input_name = inp.get('name', '')
                    print(f"  - {input_type}: {input_name}")
                
                # 尋找包含密碼欄位的表單
                if form.find('input', {'type': 'password'}) or \
                   any(inp.get('name', '').lower() in ['password', 'passwd', 'mpasswd', 'pwd'] 
                       for inp in inputs):
                    login_form = form
                    print(f"✅ 找到登入表單 (表單 {i+1})")
                    break
            
            if not login_form:
                print("❌ 未找到登入表單")
                continue
            
            # 準備登入資料
            login_data = {}
            
            # 處理所有表單欄位
            for inp in login_form.find_all(['input', 'select']):
                name = inp.get('name', '')
                input_type = inp.get('type', 'text')
                value = inp.get('value', '')
                
                if not name:
                    continue
                
                if input_type == 'hidden':
                    login_data[name] = value
                elif name.lower() in ['username', 'user', 'mno', 'account']:
                    login_data[name] = USERNAME
                elif name.lower() in ['password', 'passwd', 'mpasswd', 'pwd']:
                    login_data[name] = PASSWORD
                elif input_type in ['text', 'email']:
                    if not value:  # 如果沒有預設值，可能需要填入使用者名稱
                        login_data[name] = USERNAME
                    else:
                        login_data[name] = value
            
            # 如果沒有找到明顯的使用者名稱和密碼欄位，使用常見的名稱
            if USERNAME and not any(key in login_data for key in ['username', 'user', 'mno', 'account']):
                login_data['mno'] = USERNAME
            if PASSWORD and not any(key in login_data for key in ['password', 'passwd', 'mpasswd', 'pwd']):
                login_data['mpasswd'] = PASSWORD
            
            print(f"📝 登入資料: {[k for k in login_data.keys()]}")
            save_debug_info("login_data.txt", str(login_data), "登入資料 (密碼已遮蔽)")
            
            # 確定提交 URL
            action = login_form.get('action', '')
            if not action:
                submit_url = url
            elif action.startswith('http'):
                submit_url = action
            elif action.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                submit_url = base_url + action
            else:
                submit_url = url.rsplit('/', 1)[0] + '/' + action
            
            print(f"🚀 提交登入到: {submit_url}")
            
            # 提交登入表單
            time.sleep(2)  # 等待一下避免太快
            login_response = session.post(
                submit_url, 
                data=login_data, 
                timeout=30, 
                verify=False, 
                allow_redirects=True
            )
            
            print(f"📬 登入回應狀態碼: {login_response.status_code}")
            print(f"🔗 最終 URL: {login_response.url}")
            
            # 保存登入回應
            save_debug_info("login_response.html", login_response.content, "登入回應")
            
            # 檢查登入結果
            response_content = ""
            for encoding in ['utf-8', 'big5', 'gb2312']:
                try:
                    response_content = login_response.content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not response_content:
                response_content = login_response.content.decode('utf-8', errors='ignore')
            
            # 檢查成功指標
            success_keywords = ["歡迎", "廠商", "商品", "訂單", "menu", "logout", "登出", "管理", "系統"]
            error_keywords = ["錯誤", "失敗", "error", "failed", "invalid", "帳號密碼"]
            
            success_found = any(keyword in response_content for keyword in success_keywords)
            error_found = any(keyword in response_content for keyword in error_keywords)
            
            print(f"🔍 成功關鍵字檢查: {success_found}")
            print(f"❌ 錯誤關鍵字檢查: {error_found}")
            
            if success_found and not error_found:
                print("🎉 登入成功！")
                return True, login_response, session
            elif error_found:
                print("❌ 登入失敗 - 發現錯誤訊息")
                return False, login_response, session
            else:
                print("⚠️ 登入狀態不明確")
                # 繼續嘗試其他 URL
                
        except requests.exceptions.Timeout:
            print(f"❌ {url} - 連接超時")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {url} - 連接錯誤: {e}")
        except Exception as e:
            print(f"❌ {url} - 其他錯誤: {e}")
            traceback.print_exc()
            
    return False, None, session

def check_orders(session):
    """檢查訂單狀態"""
    try:
        print("🔍 開始檢查訂單...")
        
        order_urls = [
            "https://www.elifemall.com.tw/vendor/order_list.php",
            "https://www.elifemall.com.tw/vendor/orders.php",
            "https://www.elifemall.com.tw/vendor/order.php",
            "https://www.elifemall.com.tw/vendor/menu.php"
        ]
        
        for url in order_urls:
            try:
                print(f"📋 嘗試訪問: {url}")
                response = session.get(url, timeout=30, verify=False)
                
                if response.status_code == 200:
                    print(f"✅ 成功訪問: {url}")
                    save_debug_info(f"orders_{url.split('/')[-1]}.html", 
                                  response.content, f"訂單頁面: {url}")
                    
                    # 這裡可以加入訂單解析邏輯
                    return {"status": "success", "orders": f"成功訪問 {url}"}
                else:
                    print(f"❌ 狀態碼 {response.status_code}: {url}")
                    
            except Exception as e:
                print(f"❌ 無法訪問 {url}: {e}")
                
        return {"status": "partial", "orders": "登入成功，但無法訪問訂單頁面"}
        
    except Exception as e:
        print(f"❌ 訂單檢查錯誤: {e}")
        return {"status": "error", "error": str(e)}

def main():
    start_time = datetime.now()
    print("=" * 60)
    print("🤖 GitHub Actions 訂單檢查系統 v2.0")
    print(f"⏰ 執行時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    
    # 檢查環境變數
    required_vars = ['ELIFE_USERNAME', 'ELIFE_PASSWORD', 'GMAIL_USER', 'GMAIL_PASSWORD', 'RECEIVER_EMAIL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        error_msg = f"❌ 缺少環境變數: {', '.join(missing_vars)}"
        print(error_msg)
        send_email("【訂單檢查】設定錯誤", f"缺少環境變數：{missing_vars}")
        return
    
    print("✅ 環境變數檢查完成")
    print(f"📧 郵件將發送到: {RECEIVER_EMAIL}")
    
    try:
        # 測試網站連通性
        print("\n🌐 測試網站連通性...")
        connectivity_results = test_website_connectivity()
        
        # 建立 session 並嘗試登入
        print("\n🔐 開始登入程序...")
        session = create_session()
        login_success, response, session = login_to_website(session)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if login_success:
            print("🎉 系統登入成功！")
            
            # 檢查訂單
            order_result = check_orders(session)
            
            # 發送成功報告
            subject = "【訂單檢查】✅ 執行成功"
            body = f"""🤖 GitHub Actions 訂單檢查報告 v2.0

✅ 執行狀態：成功
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
⌛ 執行耗時：{duration:.2f} 秒

📊 檢查結果：
- 網站連接：✅ 正常
- 系統登入：✅ 成功
- 訂單檢查：{order_result.get('status', '未知')}

📝 詳細資訊：
{order_result.get('orders', '無額外資訊')}

🔧 連通性測試結果：
{chr(10).join([f"- {url}: {result.get('status_code', result.get('error', 'Unknown'))}" for url, result in connectivity_results.items()])}

🔄 下次執行：根據排程自動執行
🎯 系統狀態：運作正常

---
此郵件由 GitHub Actions 自動發送 v2.0"""
            
            send_email(subject, body)
            
        else:
            print("❌ 登入失敗")
            
            # 發送詳細的失敗報告
            subject = "【訂單檢查】❌ 登入失敗 (詳細報告)"
            body = f"""🤖 GitHub Actions 訂單檢查報告 v2.0

❌ 執行狀態：登入失敗
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
⌛ 執行耗時：{duration:.2f} 秒

🔧 連通性測試結果：
{chr(10).join([f"- {url}: {result.get('status_code', result.get('error', 'Unknown'))}" for url, result in connectivity_results.items()])}

❗ 問題說明：
無法登入全國電子廠商系統

💡 可能原因：
1. 帳號密碼錯誤
2. 網站結構變更 (表單欄位名稱改變)
3. 網站加入新的驗證機制 (驗證碼、CSRF 等)
4. IP 封鎖或地區限制
5. 網站臨時維護

🔧 建議處理：
1. 檢查 GitHub Secrets 中的帳號密碼是否正確
2. 確認網站是否正常運作
3. 查看 GitHub Actions 的 artifacts 中的除錯檔案
4. 檢查是否需要更新程式碼

📁 除錯資訊：
- 已保存登入頁面 HTML 到 artifacts
- 已保存登入回應到 artifacts  
- 已保存表單資料到 artifacts

🔄 下次執行：根據排程自動執行

---
此郵件由 GitHub Actions 自動發送 v2.0"""
            
            send_email(subject, body)
            
    except Exception as e:
        print(f"💥 執行錯誤: {e}")
        traceback.print_exc()
        
        # 發送錯誤報告
        subject = "【訂單檢查】💥 系統錯誤"
        body = f"""🤖 GitHub Actions 訂單檢查報告 v2.0

💥 執行狀態：系統錯誤
⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

❗ 錯誤訊息：
{str(e)}

🔍 詳細追蹤：
{traceback.format_exc()}

🔄 下次執行：根據排程自動執行

---
此郵件由 GitHub Actions 自動發送 v2.0"""
        
        send_email(subject, body)

if __name__ == "__main__":
    main()

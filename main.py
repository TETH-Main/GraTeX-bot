import os
import io, base64, discord, asyncio
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

# webdriver_managerは条件付きでインポート
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    print("webdriver-manager not available, using system ChromeDriver")

def create_driver():
    """Chrome WebDriverを作成する関数"""
    options = Options()
    
    # 基本設定
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    
    # ユーザーデータディレクトリの競合を回避 - より強力な一意性確保
    import tempfile
    import uuid
    import time
    import os
    
    # より一意性の高いディレクトリ名を生成
    timestamp = int(time.time() * 1000)  # ミリ秒タイムスタンプ
    process_id = os.getpid()  # プロセスID
    unique_id = uuid.uuid4().hex[:8]  # 短いUUID
    
    temp_dir = tempfile.gettempdir()
    unique_user_data_dir = f"{temp_dir}/chrome_user_data_{process_id}_{timestamp}_{unique_id}"
    
    # ディレクトリが既に存在する場合は削除
    if os.path.exists(unique_user_data_dir):
        try:
            import shutil
            shutil.rmtree(unique_user_data_dir)
            print(f"Removed existing user data directory: {unique_user_data_dir}")
        except Exception as cleanup_error:
            print(f"Could not remove existing directory: {cleanup_error}")
            # さらに一意なディレクトリを作成
            unique_user_data_dir = f"{temp_dir}/chrome_user_data_{process_id}_{timestamp}_{unique_id}_fallback"
    
    options.add_argument(f'--user-data-dir={unique_user_data_dir}')
    print(f"Using unique user data directory: {unique_user_data_dir}")
    
    # Railway/Docker環境での追加設定
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    
    # シングルプロセスモードは競合の原因になる可能性があるため条件付きで使用
    # Railway環境では通常のマルチプロセスモードを使用
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        print("Railway environment detected, using multi-process mode")
        # Railway環境での追加設定
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu-sandbox')
        options.add_argument('--disable-software-rasterizer')
    else:
        # ローカル環境ではシングルプロセスモードを使用
        options.add_argument('--single-process')
    
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.headless = True
    
    # Railway/Docker環境でのChrome設定
    chrome_paths = [
        '/usr/bin/chromium',             # Docker/Chromium
        '/usr/bin/google-chrome',        # Google Chrome
        '/nix/store/*/bin/chromium',     # Nixpacks
        '/usr/bin/chromium-browser',     # Alternative
    ]
    
    chromedriver_paths = [
        '/usr/bin/chromedriver',         # Docker/System
        '/usr/local/bin/chromedriver',   # Custom install
        '/nix/store/*/bin/chromedriver', # Nixpacks
    ]
    
    # Chrome バイナリパスを探す
    chrome_binary = None
    for path in chrome_paths:
        if '*' in path:
            # Nixパターンのマッチング
            import glob
            matches = glob.glob(path)
            if matches and os.path.exists(matches[0]):
                chrome_binary = matches[0]
                break
        elif os.path.exists(path):
            chrome_binary = path
            break
    
    if chrome_binary:
        options.binary_location = chrome_binary
        print(f"Using Chrome binary: {chrome_binary}")
    else:
        print("Chrome binary not found, using default")
    
    # ChromeDriver パスを探す
    chromedriver_path = None
    for path in chromedriver_paths:
        if '*' in path:
            import glob
            matches = glob.glob(path)
            if matches and os.path.exists(matches[0]):
                chromedriver_path = matches[0]
                break
        elif os.path.exists(path):
            chromedriver_path = path
            break
    
    try:
        print("Attempting to create Chrome WebDriver...")
        
        if chromedriver_path:
            print(f"Using ChromeDriver at: {chromedriver_path}")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            print(f"WebDriver created with driver: {chromedriver_path}")
        else:
            # webdriver-managerを使用
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    print("Attempting to use webdriver-manager...")
                    chromedriver_path = ChromeDriverManager().install()
                    service = Service(chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=options)
                    print(f"WebDriver created with webdriver-manager: {chromedriver_path}")
                except Exception as wm_error:
                    print(f"webdriver-manager failed: {wm_error}")
                    print("Attempting default Chrome settings...")
                    # 最後の手段：デフォルト
                    driver = webdriver.Chrome(options=options)
                    print("WebDriver created with default settings")
            else:
                print("webdriver-manager not available, using default Chrome...")
                # 最後の手段：デフォルト
                driver = webdriver.Chrome(options=options)
                print("WebDriver created with default settings")
        
        return driver
        
    except Exception as e:
        print(f"WebDriver creation error: {e}")
        
        # エラーが user-data-dir 関連の場合、追加の対処を試す
        if "user data directory" in str(e).lower() or "user-data-dir" in str(e).lower():
            print("User data directory conflict detected, trying alternative approach...")
            
            try:
                # user-data-dir を完全に無効化して再試行
                options_no_userdir = Options()
                
                # 基本設定を再適用（user-data-dir以外）
                basic_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--remote-debugging-port=9222',
                    '--window-size=1920,1080',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
                
                # Railway環境の追加設定
                if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
                    basic_args.extend([
                        '--disable-dev-shm-usage',
                        '--disable-gpu-sandbox',
                        '--disable-software-rasterizer'
                    ])
                else:
                    basic_args.append('--single-process')
                
                for arg in basic_args:
                    options_no_userdir.add_argument(arg)
                
                options_no_userdir.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                options_no_userdir.headless = True
                
                # Chrome バイナリパスを設定
                if chrome_binary:
                    options_no_userdir.binary_location = chrome_binary
                
                print("Retrying without user-data-dir...")
                if chromedriver_path:
                    service = Service(chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=options_no_userdir)
                else:
                    driver = webdriver.Chrome(options=options_no_userdir)
                
                print("WebDriver created successfully without user-data-dir")
                return driver
                
            except Exception as retry_error:
                print(f"Retry without user-data-dir also failed: {retry_error}")
        
        # 最終的な代替手段
        print("Attempting minimal Chrome configuration as last resort...")
        try:
            minimal_options = Options()
            minimal_options.add_argument('--no-sandbox')
            minimal_options.add_argument('--disable-dev-shm-usage')
            minimal_options.add_argument('--headless')
            
            if chrome_binary:
                minimal_options.binary_location = chrome_binary
            
            driver = webdriver.Chrome(options=minimal_options)
            print("WebDriver created with minimal configuration")
            return driver
            
        except Exception as final_error:
            print(f"All WebDriver creation attempts failed. Final error: {final_error}")
            raise e

# グローバル変数として初期化は後で行う
driver = None

def initialize_driver():
    """WebDriverを初期化する関数"""
    global driver
    if driver is None:
        print("Creating new WebDriver instance...")
        driver = create_driver()
        print("Loading GraTeX website...")
        driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
        print("Waiting for page to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))
        print("WebDriver initialized successfully")
    else:
        print("WebDriver already initialized")


def cleanup_driver():
    """WebDriverをクリーンアップする関数"""
    global driver
    if driver:
        try:
            # ユーザーデータディレクトリのパスを取得（可能であれば）
            user_data_dir = None
            try:
                # Chromeのプロセスからユーザーデータディレクトリを取得を試みる
                capabilities = driver.capabilities
                chrome_options = capabilities.get('goog:chromeOptions', {})
                args = chrome_options.get('args', [])
                for arg in args:
                    if arg.startswith('--user-data-dir='):
                        user_data_dir = arg.split('=', 1)[1]
                        break
            except:
                pass
            
            print("Closing WebDriver...")
            driver.quit()
            print("WebDriver closed successfully")
            
            # ユーザーデータディレクトリを削除
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    import shutil
                    import time
                    # 少し待ってからディレクトリ削除を試行
                    time.sleep(1)
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    print(f"Cleaned up user data directory: {user_data_dir}")
                except Exception as cleanup_error:
                    print(f"Could not clean up user data directory: {cleanup_error}")
                    
        except Exception as e:
            print(f"Error closing WebDriver: {e}")
        finally:
            driver = None


async def generate_img(latex, labelSize='4', zoomLevel=0):
    print(f"=== generate_img called ===")
    print(f"LaTeX: {latex}")
    print(f"Label size: {labelSize}")
    print(f"Zoom level: {zoomLevel}")
    
    global driver
    
    # ドライバーが初期化されていない場合は初期化
    if driver is None:
        print("Driver not initialized, initializing...")
        try:
            initialize_driver()
        except Exception as e:
            print(f"Failed to initialize driver: {e}")
            import traceback
            traceback.print_exc()
            return "error"
    else:
        print("Driver already exists, checking status...")
        try:
            # ドライバーの状態をチェック
            current_url = driver.current_url
            window_handles = driver.window_handles
            print(f"Driver status: URL={current_url}, Windows={len(window_handles)}")
        except Exception as driver_check_error:
            print(f"Driver appears to be invalid: {driver_check_error}")
            print("Attempting to reinitialize driver...")
            cleanup_driver()
            try:
                initialize_driver()
            except Exception as reinit_error:
                print(f"Failed to reinitialize driver: {reinit_error}")
                return "error"

    try:
        print("Checking current page...")
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # ページが正しく読み込まれているかチェック
        if "GraTeX" not in current_url:
            print("Not on GraTeX page, navigating...")
            driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            print("Waiting for page to load...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))
            print("Page loaded successfully")
        else:
            print("Already on GraTeX page")
            
        # ページが応答可能な状態かチェック
        page_ready = driver.execute_script("return document.readyState === 'complete';")
        print(f"Page ready state: {page_ready}")
        
        calculator_available = driver.execute_script("return typeof calculator !== 'undefined';")
        print(f"Calculator object available: {calculator_available}")
        
        if not calculator_available:
            print("WARNING: Calculator object not available, page may not be fully loaded")
            await asyncio.sleep(3)  # 追加待機
            calculator_available = driver.execute_script("return typeof calculator !== 'undefined';")
            print(f"Calculator available after wait: {calculator_available}")
        
        print("Checking zoom restore button...")
        zoom_restore = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomrestore")
        if zoom_restore and zoom_restore[0].is_displayed():
            zoom_restore[0].click()
            print("Zoom restore clicked")
        else:
            print("Zoom restore button not found or not displayed")
            
        print(f"Setting zoom level to {zoomLevel}...")
        if (zoomLevel > 0):
            for i in range(zoomLevel):
                zoom_in_buttons = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomin")
                if zoom_in_buttons:
                    zoom_in_buttons[0].click()
                    print(f"Zoom in {i+1}/{zoomLevel}")
                    await asyncio.sleep(0.5)  # 少し待機
        if (zoomLevel < 0):
            for i in range(-zoomLevel):
                zoom_out_buttons = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomout")
                if zoom_out_buttons:
                    zoom_out_buttons[0].click()
                    print(f"Zoom out {i+1}/{-zoomLevel}")
                    await asyncio.sleep(0.5)  # 少し待機

        print(f"Setting label size to {labelSize}...")
        try:
            label_selects = driver.find_elements(By.NAME, "labelSize")
            print(f"Found {len(label_selects)} label size selectors")
            if label_selects:
                print(f"Label selector found, setting to value: {labelSize}")
                Select(label_selects[0]).select_by_value(labelSize)
                print("Label size set successfully")
                
                # 選択された値を確認
                selected_value = Select(label_selects[0]).first_selected_option.get_attribute("value")
                print(f"Confirmed label size set to: {selected_value}")
            else:
                print("ERROR: Label size selector not found - this may indicate page loading issues")
                # ページの状態をデバッグ
                try:
                    page_title = driver.title
                    print(f"Current page title: {page_title}")
                    form_elements = driver.find_elements(By.TAG_NAME, "select")
                    print(f"Found {len(form_elements)} select elements total")
                    for i, select in enumerate(form_elements[:3]):  # 最初の3個だけ
                        select_name = select.get_attribute("name")
                        print(f"Select {i}: name='{select_name}'")
                except Exception as debug_e:
                    print(f"Failed to get label selector debug info: {debug_e}")
        except Exception as e:
            print(f"ERROR setting label size: {e}")
            import traceback
            traceback.print_exc()
        
        print("Removing old expression...")
        try:
            driver.execute_script("calculator.removeExpression({id:'3'});")
            print("Old expression removed successfully")
        except Exception as e:
            print(f"ERROR removing old expression: {e}")
        
        print(f"Setting new expression: {latex}")
        try:
            # JavaScriptエスケープを改善
            escaped_latex = latex.replace('\\', '\\\\').replace('`', '\\`')
            print(f"Escaped LaTeX: {escaped_latex}")
            js_command = f"calculator.setExpression({{id:'1', latex: String.raw`{escaped_latex}`, color:'black'}});"
            print(f"Executing JavaScript: {js_command}")
            driver.execute_script(js_command)
            print("New expression set successfully")
            
            # 式が正しく設定されたかJavaScriptで確認
            try:
                expression_count = driver.execute_script("return calculator.getExpressions().length;")
                print(f"Total expressions in calculator: {expression_count}")
                
                # 設定した式が存在するかチェック
                expression_exists = driver.execute_script("return calculator.getExpressions().some(e => e.id === '1');")
                print(f"Expression with id '1' exists: {expression_exists}")
            except Exception as check_e:
                print(f"Error checking expression state: {check_e}")
                
        except Exception as e:
            print(f"ERROR setting new expression: {e}")
            import traceback
            traceback.print_exc()
            return "error"
        
        print("Waiting 5 seconds for expression to render...")
        await asyncio.sleep(5)
        
        print("Looking for screenshot button...")
        screenshot_buttons = driver.find_elements(By.ID, "screenshot-button")
        print(f"Found {len(screenshot_buttons)} screenshot buttons")
        
        if screenshot_buttons:
            try:
                print("Screenshot button found, analyzing element...")
                button = screenshot_buttons[0]
                print(f"Button displayed: {button.is_displayed()}")
                print(f"Button enabled: {button.is_enabled()}")
                print(f"Button tag: {button.tag_name}")
                print(f"Button text: {button.text}")
                print(f"Button location: {button.location}")
                print(f"Button size: {button.size}")
                
                # ボタンがクリック可能かチェック
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "screenshot-button")))
                    print("Button is clickable according to WebDriverWait")
                except:
                    print("WARNING: Button may not be fully clickable yet")
                
                print("Attempting to click screenshot button...")
                button.click()
                print("Screenshot button clicked successfully")
                
                # クリック後の状態を確認
                await asyncio.sleep(1)  # クリック処理の時間を与える
                print("Checking post-click state...")
                
            except Exception as click_error:
                print(f"ERROR clicking screenshot button: {click_error}")
                import traceback
                traceback.print_exc()
                
                # 代替手段を試す
                try:
                    print("Trying JavaScript click as fallback...")
                    driver.execute_script("arguments[0].click();", button)
                    print("JavaScript click succeeded")
                except Exception as js_click_error:
                    print(f"JavaScript click also failed: {js_click_error}")
                    return "error"
        else:
            print("ERROR: Screenshot button not found in DOM")
            # DOMの状態をより詳しくデバッグ
            try:
                print("Debugging page state...")
                page_title = driver.title
                print(f"Page title: {page_title}")
                
                # 現在のページのボタン要素を全て確認
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(all_buttons)} button elements")
                for i, btn in enumerate(all_buttons[:5]):  # 最初の5個だけ
                    btn_id = btn.get_attribute("id")
                    btn_class = btn.get_attribute("class")
                    btn_text = btn.text[:30] if btn.text else ""
                    print(f"Button {i}: id='{btn_id}', class='{btn_class}', text='{btn_text}'")
                
                # 特定のクラスやIDパターンを持つ要素を探す
                screenshot_related = driver.find_elements(By.XPATH, "//*[contains(@id, 'screenshot') or contains(@class, 'screenshot')]")
                print(f"Found {len(screenshot_related)} screenshot-related elements")
                
                # ページが完全に読み込まれているかチェック
                ready_state = driver.execute_script("return document.readyState;")
                print(f"Document ready state: {ready_state}")
                
                # JavaScript変数の状態をチェック
                calculator_exists = driver.execute_script("return typeof calculator !== 'undefined';")
                print(f"Calculator object exists: {calculator_exists}")
                
            except Exception as debug_error:
                print(f"Error getting page debug info: {debug_error}")
            return "error"

        try:
            print("Waiting for generation container to appear...")
            wait_element = WebDriverWait(driver, 30)
            
            # まずコンテナの存在をチェック
            print("Checking if generation container exists in DOM...")
            gen_containers = driver.find_elements(By.ID, "generate-container")
            print(f"Found {len(gen_containers)} generation containers")
            
            if gen_containers:
                container = gen_containers[0]
                print(f"Container exists - displayed: {container.is_displayed()}")
                print(f"Container style: {container.get_attribute('style')}")
                print(f"Container class: {container.get_attribute('class')}")
                print(f"Container size: {container.size}")
                print(f"Container location: {container.location}")
            
            # 表示されるまで待機
            generation_container = wait_element.until(
                EC.visibility_of_element_located((By.ID, "generate-container")))
            print("Generation container became visible")
            
            # コンテナが表示された後の状態を確認
            print(f"Final container state - displayed: {generation_container.is_displayed()}")
            print(f"Final container size: {generation_container.size}")
            
            # コンテナ内のコンテンツを確認
            try:
                container_html = generation_container.get_attribute("innerHTML")
                print(f"Container innerHTML length: {len(container_html)}")
                if len(container_html) > 0:
                    print(f"Container content preview: {container_html[:200]}...")
                else:
                    print("WARNING: Container is visible but empty")
                    
                # コンテナ内の子要素をチェック
                child_elements = generation_container.find_elements(By.XPATH, ".//*")
                print(f"Container has {len(child_elements)} child elements")
                
            except Exception as content_error:
                print(f"Error checking container content: {content_error}")
            
        except TimeoutException:
            print("ERROR: Timeout waiting for generation container")
            print("This suggests the screenshot generation failed or is taking too long")
            
            # より詳細なデバッグ情報を収集
            try:
                print("=== GENERATION TIMEOUT DEBUG ===")
                
                # 再度コンテナの存在をチェック
                gen_containers = driver.find_elements(By.ID, "generate-container")
                print(f"Generation containers after timeout: {len(gen_containers)}")
                
                if gen_containers:
                    container = gen_containers[0]
                    print(f"Container exists but not visible:")
                    print(f"  - displayed: {container.is_displayed()}")
                    print(f"  - style: {container.get_attribute('style')}")
                    print(f"  - class: {container.get_attribute('class')}")
                    
                    # CSSスタイルを詳しく確認
                    computed_style = driver.execute_script(
                        "return window.getComputedStyle(arguments[0]);", container)
                    if computed_style:
                        print(f"  - computed display: {computed_style.get('display')}")
                        print(f"  - computed visibility: {computed_style.get('visibility')}")
                        print(f"  - computed opacity: {computed_style.get('opacity')}")
                
                # エラーメッセージがあるかチェック
                error_elements = driver.find_elements(By.CLASS_NAME, "error")
                if error_elements:
                    print(f"Found {len(error_elements)} error elements on page:")
                    for i, error_elem in enumerate(error_elements):
                        try:
                            error_text = error_elem.text
                            print(f"  Error {i+1}: {error_text}")
                        except:
                            print(f"  Error {i+1}: [Could not read text]")
                
                # JavaScript console errors
                try:
                    js_errors = driver.execute_script(
                        "return window.console && window.console.errors ? window.console.errors : []")
                    if js_errors:
                        print(f"JavaScript errors: {js_errors}")
                except:
                    print("Could not retrieve JavaScript errors")
                
                # calculatorオブジェクトの状態をチェック
                try:
                    calculator_state = driver.execute_script("""
                        if (typeof calculator === 'undefined') return 'Calculator not defined';
                        try {
                            var expressions = calculator.getExpressions();
                            return {
                                expressionCount: expressions.length,
                                hasId1: expressions.some(e => e.id === '1'),
                                calculatorReady: typeof calculator.setExpression === 'function'
                            };
                        } catch (e) {
                            return 'Calculator error: ' + e.message;
                        }
                    """)
                    print(f"Calculator state: {calculator_state}")
                except Exception as calc_error:
                    print(f"Error checking calculator state: {calc_error}")
                
                # ページ全体の読み込み状態
                ready_state = driver.execute_script("return document.readyState;")
                print(f"Document ready state: {ready_state}")
                
                print("=== END DEBUG ===")
                
            except Exception as debug_error:
                print(f"Error during generation container debug: {debug_error}")
            
            # クリーンアップしてエラーを返す
            try:
                driver.execute_script("calculator.removeExpression({id:'1'});")
                print("Cleaned up expression after timeout")
            except:
                pass
            return "error"
            
        except Exception as wait_error:
            print(f"ERROR waiting for generation container: {wait_error}")
            import traceback
            traceback.print_exc()
            return "error"
            
        print("Removing expression...")
        try:
            driver.execute_script("calculator.removeExpression({id:'1'});")
            print("Expression removed successfully")
        except Exception as remove_error:
            print(f"Error removing expression: {remove_error}")

        print("Getting image data...")
        preview_elements = driver.find_elements(By.ID, "preview")
        print(f"Found {len(preview_elements)} preview elements")
        
        if preview_elements:
            try:
                preview_element = preview_elements[0]
                print(f"Preview element found:")
                print(f"  - displayed: {preview_element.is_displayed()}")
                print(f"  - tag: {preview_element.tag_name}")
                print(f"  - size: {preview_element.size}")
                print(f"  - location: {preview_element.location}")
                
                # 要素の属性を全て確認
                all_attributes = driver.execute_script(
                    "var elem = arguments[0]; var attrs = {}; "
                    "for (var i = 0; i < elem.attributes.length; i++) { "
                    "attrs[elem.attributes[i].name] = elem.attributes[i].value; } "
                    "return attrs;", preview_element)
                print(f"  - attributes: {all_attributes}")
                
                img_data = preview_element.get_attribute("src")
                
                if img_data:
                    print(f"Image data retrieved:")
                    print(f"  - length: {len(img_data)}")
                    print(f"  - starts with: {img_data[:50]}...")
                    
                    if img_data.startswith("data:image/png;base64,"):
                        print("Image data has correct data URL format")
                        result = img_data[22:]  # "data:image/png;base64," を除去
                        print(f"Base64 data extracted, length: {len(result)}")
                        
                        # base64データの妥当性チェック
                        try:
                            import base64
                            decoded = base64.b64decode(result)
                            print(f"Base64 decode successful:")
                            print(f"  - decoded size: {len(decoded)} bytes")
                            
                            # PNG形式かチェック（PNGファイルは\x89PNG で始まる）
                            if decoded.startswith(b'\x89PNG'):
                                print("  - Valid PNG format detected")
                            else:
                                print(f"  - WARNING: Decoded data doesn't start with PNG signature")
                                print(f"  - First 16 bytes: {decoded[:16]}")
                            
                            return result
                            
                        except Exception as decode_error:
                            print(f"ERROR: Base64 decode failed: {decode_error}")
                            
                            # デコードに失敗した場合、データの詳細を確認
                            print(f"Problematic base64 data sample: {result[:100]}...")
                            
                            # 不正な文字があるかチェック
                            import re
                            invalid_chars = re.findall(r'[^A-Za-z0-9+/=]', result)
                            if invalid_chars:
                                print(f"Invalid base64 characters found: {set(invalid_chars)}")
                            
                            return "error"
                    elif img_data.startswith("data:image/"):
                        print(f"Image data has different format: {img_data[:50]}...")
                        # 他の画像形式の場合
                        if "base64," in img_data:
                            base64_start = img_data.find("base64,") + 7
                            result = img_data[base64_start:]
                            print(f"Extracted base64 from different format, length: {len(result)}")
                            return result
                        else:
                            print("ERROR: Not a base64 data URL")
                            return "error"
                    else:
                        print(f"ERROR: Invalid image data format")
                        print(f"Expected 'data:image/' but got: {img_data[:100]}...")
                        
                        # 値が空でない場合の追加チェック
                        if len(img_data) > 0:
                            print(f"Non-empty src value detected, checking if it's a URL...")
                            if img_data.startswith(("http://", "https://", "/")):
                                print("Src appears to be a URL rather than data URL")
                                # URLの場合の処理は今回は対象外
                            elif img_data.startswith("blob:"):
                                print("Src appears to be a blob URL")
                                # blob URLの場合の処理は今回は対象外
                        
                        return "error"
                else:
                    print("ERROR: No image data in src attribute")
                    
                    # src属性が空の場合の追加デバッグ
                    print("Checking other possible image attributes...")
                    
                    # data-src や其他の属性をチェック
                    data_src = preview_element.get_attribute("data-src")
                    if data_src:
                        print(f"Found data-src: {data_src[:50]}...")
                    
                    # CSS background-image をチェック
                    background_image = driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).backgroundImage;", 
                        preview_element)
                    if background_image and background_image != "none":
                        print(f"Found background-image: {background_image[:50]}...")
                    
                    return "error"
                    
            except Exception as preview_error:
                print(f"ERROR processing preview element: {preview_error}")
                import traceback
                traceback.print_exc()
                return "error"
        else:
            print("ERROR: Preview element not found in DOM")
            
            # プレビュー要素が見つからない場合の詳細デバッグ
            try:
                print("=== PREVIEW ELEMENT DEBUG ===")
                
                # 生成コンテナ内を詳しく調べる
                gen_containers = driver.find_elements(By.ID, "generate-container")
                if gen_containers:
                    container = gen_containers[0]
                    print("Generation container content analysis:")
                    
                    container_html = container.get_attribute("innerHTML")
                    print(f"  - innerHTML length: {len(container_html)}")
                    
                    if len(container_html) > 0:
                        print(f"  - content preview: {container_html[:300]}...")
                        
                        # コンテナ内のすべての要素を列挙
                        child_elements = container.find_elements(By.XPATH, ".//*")
                        print(f"  - child elements: {len(child_elements)}")
                        
                        for i, child in enumerate(child_elements[:10]):  # 最初の10個
                            tag = child.tag_name
                            child_id = child.get_attribute("id")
                            child_class = child.get_attribute("class")
                            print(f"    Child {i}: <{tag}> id='{child_id}' class='{child_class}'")
                
                # 類似のIDを持つ要素を探す
                print("Searching for elements with similar IDs...")
                preview_like = driver.find_elements(By.XPATH, "//*[contains(@id, 'preview') or contains(@class, 'preview')]")
                print(f"Found {len(preview_like)} preview-like elements:")
                for i, elem in enumerate(preview_like[:5]):
                    elem_id = elem.get_attribute("id")
                    elem_class = elem.get_attribute("class")
                    elem_tag = elem.tag_name
                    print(f"  Preview-like {i}: <{elem_tag}> id='{elem_id}' class='{elem_class}'")
                
                # img要素を全て確認
                print("Analyzing all img elements...")
                img_elements = driver.find_elements(By.TAG_NAME, "img")
                print(f"Found {len(img_elements)} img elements:")
                for i, img in enumerate(img_elements[:10]):  # 最初の10個
                    img_id = img.get_attribute("id")
                    img_class = img.get_attribute("class")
                    img_src = img.get_attribute("src")
                    img_displayed = img.is_displayed()
                    print(f"  Image {i}: id='{img_id}' class='{img_class}' displayed={img_displayed}")
                    if img_src:
                        print(f"    src: {img_src[:50]}...")
                
                print("=== END DEBUG ===")
                
            except Exception as debug_error:
                print(f"Error during preview element debug: {debug_error}")
            
            return "error"
            
    except Exception as e:
        print(f"Error in generate_img: {e}")
        import traceback
        traceback.print_exc()
        
        # エラー時にドライバーを再初期化
        print("Attempting to reinitialize driver due to error...")
        cleanup_driver()
        try:
            initialize_driver()
            print("Driver reinitialized successfully")
        except Exception as reinit_error:
            print(f"Failed to reinitialize driver: {reinit_error}")
        
        return "error"


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# スラッシュコマンド用のTree
tree = bot.tree

print("Bot instance created with intents and tree initialized")


async def waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel):
  print(f"waitReaction called with arg: {arg}, labelSize: {labelSize}, zoomLevel: {zoomLevel}")
  
  # ctx_or_interactionがInteractionかContextかを判定
  if hasattr(ctx_or_interaction, 'user'):
    # Interaction
    user = ctx_or_interaction.user
    print(f"Using Interaction user: {user}")
  else:
    # Context
    user = ctx_or_interaction.author
    print(f"Using Context author: {user}")

  def check(reaction, reaction_user):
    result = reaction_user == user and str(reaction.emoji) in [
      '1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔎', '🔭', '✅', '🚮'
    ]
    print(f"Reaction check: user={reaction_user}, emoji={reaction.emoji}, result={result}")
    return result

  try:
    print("Waiting for reaction...")
    reaction, reaction_user = await bot.wait_for('reaction_add',
                                        timeout=20.0,
                                        check=check)
    print(f"Reaction received: {reaction.emoji} from {reaction_user}")
  except asyncio.TimeoutError:
    print("Reaction timeout, clearing reactions")
    await message.clear_reactions()
    return
  else:
    if (str(reaction.emoji) == '✅'):
      print("Complete reaction received")
      await message.clear_reactions()
      return

    if (str(reaction.emoji) == '🚮'):
      print("Delete reaction received")
      await message.delete()
      return

    if (str(reaction.emoji) == '🔎'):
      zoomLevel += 1
      print(f"Zoom in: new zoom level = {zoomLevel}")
    if (str(reaction.emoji) == '🔭'):
      zoomLevel -= 1
      print(f"Zoom out: new zoom level = {zoomLevel}")

    if (str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣']):
      labelSize = str(reaction.emoji)[0]
      print(f"Label size changed to: {labelSize}")

    await reaction.remove(reaction_user)
    
    # メッセージ更新処理
    try:
      print(f"Generating new image with labelSize={labelSize}, zoomLevel={zoomLevel}")
      img_data = await generate_img(arg, labelSize, zoomLevel)
      if img_data == "error":
        print("Image generation returned error")
        return
      
      print("Updating message with new image")
      await message.edit(attachments=[
        discord.File(io.BytesIO(base64.b64decode(img_data)),
                     f'GraTeX zoom {zoomLevel}.png')
      ])
      print("Message updated successfully")
    except Exception as e:
      print(f"Error updating image: {e}")
      return
    
    await waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel)


@bot.event
async def on_ready():
    print('=== GraTeX bot is starting up ===')
    print(f'Bot user: {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Bot guilds: {len(bot.guilds)}')
    
    # Bot起動時にWebDriverを初期化
    try:
        print('Initializing WebDriver...')
        initialize_driver()
        print('WebDriver initialized successfully on bot startup')
    except Exception as e:
        print(f'Error initializing WebDriver: {e}')
    
    # スラッシュコマンドを同期
    try:
        print('Syncing slash commands...')
        synced = await tree.sync()
        print(f'Successfully synced {len(synced)} slash commands:')
        for cmd in synced:
            print(f'  - {cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')
    
    print('=== GraTeX bot is ready! ===')


@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    print(f"Application command error: {error}")
    print(f"Interaction: {interaction}")
    if not interaction.response.is_done():
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Bot error in event {event}: {args}, {kwargs}")
    import traceback
    traceback.print_exc()


# ヘルプ用のEmbed作成関数
def create_help_embed():
    embed = discord.Embed(
        title="🧮 GraTeX Bot - Help",
        description="Generate mathematical graphs from LaTeX formulas with interactive controls",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📖 Basic Usage",
        value='`/gratex formula:"latex_formula"`\n\n**Example:**\n`/gratex formula:"\\cos x\\le\\cos y"`',
        inline=False
    )
    
    embed.add_field(
        name="🎛️ Interactive Controls",
        value="2⃣3⃣4⃣6⃣ : Change label size\n🔎 : Zoom in\n🔭 : Zoom out\n✅ : Complete editing\n🚮 : Delete message",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Advanced Usage",
        value='`/gratex formula:"latex" label_size:4 zoom_level:0`\n\n**Parameters:**\n• label_size: 1, 2, 3, 4, 6, 8\n• zoom_level: integer value',
        inline=False
    )
    
    embed.add_field(
        name="⏱️ Note",
        value="If no response for 20 seconds, editing automatically completes",
        inline=False
    )
    
    embed.set_footer(text="Powered by GraTeX | Made with ❤️")
    
    return embed


# スラッシュコマンド定義
@tree.command(name="gratex", description="Generate mathematical graphs from LaTeX formulas")
async def gratex_slash(
    interaction: discord.Interaction,
    formula: str,
    label_size: int = 4,
    zoom_level: int = 0
):
    print(f"=== Slash command received ===")
    print(f"User: {interaction.user}")
    print(f"Guild: {interaction.guild}")
    print(f"Formula: {formula}")
    print(f"Label size: {label_size}")
    print(f"Zoom level: {zoom_level}")
    
    # パラメータ検証
    if label_size not in [1, 2, 3, 4, 6, 8]:
        print(f"Invalid label size: {label_size}")
        await interaction.response.send_message(
            '❌ **Invalid label size!**\nLabel size must be one of: 1, 2, 3, 4, 6, 8\n\nUse `/gratex formula:"help"` for more information.',
            ephemeral=True
        )
        return
    
    if not isinstance(zoom_level, int):
        print(f"Invalid zoom level type: {type(zoom_level)}")
        await interaction.response.send_message(
            '❌ **Invalid zoom level!**\nZoom level must be an integer\n\nUse `/gratex formula:"help"` for more information.',
            ephemeral=True
        )
        return

    # "help"チェック
    if formula.lower() == "help":
        print("Help requested")
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)
        return
    
    # 処理中メッセージ
    print("Deferring interaction response...")
    await interaction.response.defer()
    
    try:
        # 画像生成
        print(f"Generating image for formula: {formula}")
        cleaned_formula = formula.translate(str.maketrans('', '', '`'))
        print(f"Cleaned formula: {cleaned_formula}")
        
        img_data = await generate_img(cleaned_formula, str(label_size), zoom_level)
        print(f"Image generation result: {'success' if img_data != 'error' else 'error'}")
        
        if img_data == "error":
            print("Image generation failed")
            await interaction.followup.send(
                '❌ **The graph could not be generated.**\nPlease enter a simpler formula and try again.'
            )
            return

        # 画像送信
        print("Sending image file...")
        reply = await interaction.followup.send(
            file=discord.File(
                io.BytesIO(base64.b64decode(img_data)), 
                'GraTeX.png'
            )
        )
        print(f"Image sent successfully, message ID: {reply.id}")
        
        # リアクション追加
        print("Adding reactions...")
        reactions = ['2⃣', '3⃣', '4⃣', '6⃣', '🔎', '🔭', '✅', '🚮']
        for emoji in reactions:
            try:
                await reply.add_reaction(emoji)
                print(f"Added reaction: {emoji}")
            except Exception as e:
                print(f"Failed to add reaction {emoji}: {e}")
        
        print("Starting reaction listener...")
        # リアクション待機
        await waitReaction(interaction, reply, formula, str(label_size), zoom_level)
        
    except Exception as e:
        print(f"Error in slash command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(
                '❌ **An error occurred while generating the graph.**\nPlease try again later.'
            )
        except:
            print("Failed to send error message")


if __name__ == "__main__":
    print("=== Starting GraTeX Bot ===")
    
    # プロセス終了時のクリーンアップを登録
    import atexit
    import signal
    
    def cleanup_on_exit():
        print("Performing cleanup on exit...")
        cleanup_driver()
        
        # 残存するユーザーデータディレクトリを削除
        try:
            import tempfile
            import glob
            temp_dir = tempfile.gettempdir()
            chrome_dirs = glob.glob(f"{temp_dir}/chrome_user_data_*")
            for dir_path in chrome_dirs:
                try:
                    import shutil
                    shutil.rmtree(dir_path, ignore_errors=True)
                    print(f"Cleaned up temp directory: {dir_path}")
                except:
                    pass
        except:
            pass
    
    atexit.register(cleanup_on_exit)
    
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, cleaning up...")
        cleanup_on_exit()
        exit(0)
    
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except:
        # Windowsでは一部のシグナルが利用できない場合がある
        pass
    
    # Railwayの環境変数からトークンを取得
    token = os.getenv("TOKEN")
    if not token:
        print("ERROR: TOKEN environment variable is not set")
        raise ValueError("TOKEN environment variable is not set")
    
    print(f"Token found: {token[:10]}...")
    
    try:
        print("Starting bot...")
        bot.run(token)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # クリーンアップ
        print("Final cleanup...")
        cleanup_on_exit()

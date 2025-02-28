import os
import time
import random
import requests
from tabulate import tabulate
from playwright.sync_api import sync_playwright

# 设置 PushPlus 的 Token 和发送请求的 URL
PUSHPLUS_TOKEN = os.environ.get("PUSHTOKEN")
url_pushplus = 'http://www.pushplus.plus/send'

# 用户名和密码从环境变量中获取
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

HOME_URL = "https://linux.do/"

class LinuxDoBrowser:
    def __init__(self, retries=3) -> None:
        self.retries = retries
        self.initialize_browser()

    def initialize_browser(self):
        for attempt in range(self.retries):
            try:
                print(f"Attempt {attempt + 1} to initialize browser...")
                self.pw = sync_playwright().start()
                self.browser = self.pw.firefox.launch(
                    headless=True,
                    args=[
                        "--disable-gpu",  # 禁用 GPU 加速
                        "--no-sandbox",  # 禁用沙盒模式
                        "--disable-dev-shm-usage",  # 禁用共享内存
                    ]
                )
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                self.page.goto(HOME_URL)
                print("Browser initialized successfully")
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retries - 1:
                    raise
                self.close_resources()
                time.sleep(5)  # 等待一段时间后重试

    def close_resources(self):
        if hasattr(self, 'context'):
            self.context.close()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'pw'):
            self.pw.stop()

    def login(self):
        try:
            print("Attempting to log in...")
            self.page.click(".login-button .d-button-label")
            time.sleep(2)
            self.page.fill("#login-account-name", USERNAME)
            time.sleep(2)
            self.page.fill("#login-account-password", PASSWORD)
            time.sleep(2)
            self.page.click("#login-button")
            time.sleep(10)
            user_ele = self.page.query_selector("#current-user")
            if not user_ele:
                print("Login failed")
                return False
            else:
                print("Login success")
                return True
        except Exception as e:
            print(f"Login failed with error: {e}")
            return False

    def scroll_down(self):
        print("Scrolling down...")
        self.page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(2)  # 等待加载新内容

    def click_topic(self):
        max_browse_count = 50  # 减少浏览数量以降低资源消耗
        browsed_topics = []  # 存储浏览的帖子
        total_count = 0

        while total_count < max_browse_count:
            try:
                print(f"Loading topic list...")
                time.sleep(5)
                topics = self.page.query_selector_all("#list-area .title")

                if not topics:
                    print("No topics found, please check the selector or page load.")
                    break

                # 排除已经浏览过的帖子
                new_topics = [t for t in topics if t not in browsed_topics]
                browsed_topics.extend(new_topics)

                if not new_topics:
                    print("No more topics loaded.")
                    break

                for topic in new_topics:
                    if total_count >= max_browse_count:
                        break

                    try:
                        print(f"Browsing topic {total_count + 1}...")
                        # 检查上下文是否有效
                        if self.context.is_closed():
                            print("Browser context is closed, reinitializing...")
                            self.close_resources()
                            self.initialize_browser()

                        page = self.context.new_page()
                        page.goto(HOME_URL + topic.get_attribute("href"))
                        time.sleep(3)
                        
                        if random.random() < 0.02:  # 保持 2% 点赞几率
                            print("Attempting to like...")
                            self.click_like(page)

                        total_count += 1
                        time.sleep(3)
                    except Exception as e:
                        print(f"Error browsing topic: {e}")
                    finally:
                        if not page.is_closed():
                            page.close()

                print(f"Browsed {total_count} topics")
                self.scroll_down()

            except Exception as e:
                print(f"Error loading topic list: {e}")
                # 重新初始化浏览器上下文
                self.close_resources()
                self.initialize_browser()

        print(f"Total topics browsed: {total_count}")

    def click_like(self, page):
        try:
            page.locator(".discourse-reactions-reaction-button").first.click()
            print("Like success")
        except Exception as e:
            print(f"Like failed: {e}")

    def print_connect_info(self):
        try:
            print("Fetching connection info...")
            page = self.context.new_page()
            page.goto("https://connect.linux.do/")
            rows = page.query_selector_all("table tr")

            info = []

            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 3:
                    project = cells[0].text_content().strip()
                    current = cells[1].text_content().strip()
                    requirement = cells[2].text_content().strip()
                    info.append([project, current, requirement])

            # 使用 HTML 表格格式化数据，包含标题
            html_table = "<table style='border-collapse: collapse; width: 100%; border: 1px solid black;'>"
            html_table += "<caption>在过去 100 天内：</caption>"
            html_table += "<tr><th style='border: 1px solid black; padding: 8px;'>项目</th><th style='border: 1px solid black; padding: 8px;'>当前</th><th style='border: 1px solid black; padding: 8px;'>要求</th></tr>"

            for row in info:
                html_table += "<tr>"
                for cell in row:
                    html_table += f"<td style='border: 1px solid black; padding: 8px;'>{cell}</td>"
                html_table += "</tr>"

            html_table += "</table>"

            # 准备推送数据
            push_data = {
                "token": PUSHPLUS_TOKEN,
                "title": "Linux.do 自动签到",
                "content": html_table,
                "template": "html"  # 指定使用 HTML 格式
            }

            # 发送推送请求到 PushPlus
            response_pushplus = requests.post(url_pushplus, data=push_data)
            print("Push result:", response_pushplus.text)
        except Exception as e:
            print(f"Error fetching connection info: {e}")
        finally:
            if not page.is_closed():
                page.close()

    def run(self):
        try:
            if not self.login():
                return
            self.click_topic()
            self.print_connect_info()
        except Exception as e:
            print(f"Error during execution: {e}")
            # 重新初始化浏览器
            self.close_resources()
            self.initialize_browser()
            self.run()
        finally:
            # 确保资源释放
            self.close_resources()

if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        print("Please set USERNAME and PASSWORD")
        exit(1)
    
    l = LinuxDoBrowser()
    l.run()

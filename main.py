import os
import time
import random
import requests
from tabulate import tabulate
from bs4 import BeautifulSoup

# 设置 PushPlus 的 Token 和发送请求的 URL
PUSHPLUS_TOKEN = os.environ.get("PUSHTOKEN")
url_pushplus = 'http://www.pushplus.plus/send'

# 用户名和密码从环境变量中获取
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

HOME_URL = "https://linux.do/"

class LinuxDoScraper:
    def __init__(self) -> None:
        self.session = requests.Session()

    def login(self):
        try:
            print("Attempting to log in...")
            login_url = HOME_URL + "login"
            response = self.session.get(login_url)
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("meta", attrs={"name": "csrf-token"})["content"]

            login_data = {
                "username": USERNAME,
                "password": PASSWORD,
                "authenticity_token": csrf_token
            }
            response = self.session.post(login_url, data=login_data)
            if response.status_code == 200:
                print("Login success")
                return True
            else:
                print("Login failed")
                return False
        except Exception as e:
            print(f"Login failed with error: {e}")
            return False

    def scrape_topics(self):
        max_browse_count = 50  # 减少浏览数量以降低资源消耗
        total_count = 0

        while total_count < max_browse_count:
            try:
                print(f"Loading topic list...")
                response = self.session.get(HOME_URL)
                soup = BeautifulSoup(response.text, "html.parser")
                topics = soup.select("#list-area .title")

                if not topics:
                    print("No topics found, please check the selector or page load.")
                    break

                for topic in topics:
                    if total_count >= max_browse_count:
                        break

                    try:
                        print(f"Browsing topic {total_count + 1}...")
                        topic_url = HOME_URL + topic["href"]
                        response = self.session.get(topic_url)
                        time.sleep(3)
                        
                        if random.random() < 0.02:  # 保持 2% 点赞几率
                            print("Attempting to like...")
                            self.click_like(topic_url)

                        total_count += 1
                        time.sleep(3)
                    except Exception as e:
                        print(f"Error browsing topic: {e}")

                print(f"Browsed {total_count} topics")
            except Exception as e:
                print(f"Error loading topic list: {e}")

        print(f"Total topics browsed: {total_count}")

    def click_like(self, topic_url):
        try:
            like_url = topic_url + "/like"
            response = self.session.post(like_url)
            if response.status_code == 200:
                print("Like success")
            else:
                print("Like failed")
        except Exception as e:
            print(f"Like failed: {e}")

    def print_connect_info(self):
        try:
            print("Fetching connection info...")
            response = self.session.get("https://connect.linux.do/")
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select("table tr")

            info = []

            for row in rows:
                cells = row.select("td")
                if len(cells) >= 3:
                    project = cells[0].text.strip()
                    current = cells[1].text.strip()
                    requirement = cells[2].text.strip()
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

    def run(self):
        try:
            if not self.login():
                return
            self.scrape_topics()
            self.print_connect_info()
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        print("Please set USERNAME and PASSWORD")
        exit(1)
    
    scraper = LinuxDoScraper()
    scraper.run()

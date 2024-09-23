import asyncio
import os
from datetime import date, timedelta

from twikit import Client

from src.logger import LOG  # 导入日志模块

class XClient:
    def __init__(self,user, email, pwd):

        self.client = Client('en-Us',
                             proxy='http://127.0.0.1:7890',
                             user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
        self.user = user
        self.email = email
        self.pwd = pwd


    async def login_client(self):
        if os.path.exists('cookies.json'):
            self.client.load_cookies('cookies.json')
        else:
            await self.client.login(
                auth_info_1=self.user, auth_info_2=self.email, password=self.pwd
            )
            self.client.save_cookies('cookies.json')


    async def export_tweets_by_date_range(self, user_name, days):

        await self.login_client()

        today = date.today()  # 获取当前日期
        since = today - timedelta(days=days)  # 计算开始日期

        user = await self.client.get_user_by_screen_name(user_name)

        tweets = await self.client.get_user_tweets(user.id, 'Tweets', count=20)

        all_tweets = []
        while tweets:
            for tweet in tweets:
                tweet_date = tweet.created_at_datetime.date()
                if tweet_date < since:
                    tweets = None
                    break
                if tweet_date < today:
                    all_tweets.append(tweet)
            if tweets:
                tweets = await tweets.next()

        user_dir = os.path.join('daily_tweets', user_name.replace("/", "_"))  # 构建目录路径
        os.makedirs(user_dir, exist_ok=True)  # 确保目录存在

        date_str = f"{since}_to_{today}"
        file_path = os.path.join(user_dir, f'{date_str}.md')  # 构建文件路径

        with open(file_path, 'w') as file:
            file.write(f"# Tweets from {tweet.user.name} ({since} to {today})\n\n")
            file.write(f"\n## Post in the Last {days} Days\n")
            for tweet in all_tweets:
                file.write(f"### {tweet.created_at_datetime}\n")
                file.write(f"content:{tweet.full_text}\n\n")
                if tweet.quote is not None:
                    file.write(f"quote: @{tweet.quote.user.name}-{tweet.quote.text}\n\n")
                file.write(f"url: https://x.com/{user_name}/status/{tweet.id}\n\n")

        LOG.info(f"[{user_name}]最新 tweet 生成： {file_path}")  # 记录日志
        return file_path





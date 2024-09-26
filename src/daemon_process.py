import asyncio

import schedule # 导入 schedule 实现定时任务执行器
import time  # 导入time库，用于控制时间间隔
import os   # 导入os模块用于文件和目录操作
import signal  # 导入signal库，用于信号处理
import sys  # 导入sys库，用于执行系统相关的操作
from datetime import datetime  # 导入 datetime 模块用于获取当前日期

from config import Config  # 导入配置管理类
from src.clients.github_client import GitHubClient  # 导入GitHub客户端类，处理GitHub API请求
from notifier import Notifier  # 导入通知器类，用于发送通知
from report_generator import ReportGenerator  # 导入报告生成器类
from llm import LLM  # 导入语言模型类，可能用于生成报告内容
from src.clients.hacker_news_client import HackerNewsClient
from src.clients.x_client import XClient
from subscription_manager import SubscriptionManager  # 导入订阅管理器类，管理GitHub仓库订阅
from logger import LOG  # 导入日志记录器


def graceful_shutdown(signum, frame):
    # 优雅关闭程序的函数，处理信号时调用
    LOG.info("[优雅退出]守护进程接收到终止信号")
    sys.exit(0)  # 安全退出程序


def github_job(subscription_manager, github_client, report_generator, notifier, days):
    LOG.info("[开始执行定时任务]GitHub Repo 项目进展报告")
    subscriptions = subscription_manager.list_subscriptions()  # 获取当前所有订阅
    LOG.info(f"订阅列表：{subscriptions}")
    for repo in subscriptions:
        # 遍历每个订阅的仓库，执行以下操作
        markdown_file_path = github_client.export_progress_by_date_range(repo, days)
        # 从Markdown文件自动生成进展简报
        report, _ = report_generator.generate_github_report(markdown_file_path)
        notifier.notify_github_report(repo, report)
    LOG.info(f"[定时任务执行完毕]")

async def x_job(x_client, subscriptions, report_generator, notifier):
    LOG.info("[开始执行定时任务]x 话题跟踪")
    try:
        for subscription in subscriptions:
            markdown_file_path = await x_client.export_tweets_by_date_range(subscription, 1)
            report, _ = report_generator.generate_x_report(markdown_file_path)
            notifier.notify_x_report(subscription, report)

        LOG.info(f"[定时任务执行完毕]")
    except Exception as e:
        LOG.error(f"执行x 话题跟踪失败：{e}")

def run_x_job(x_client, subscriptions, report_generator, notifier):
    try:
        loop = asyncio.get_event_loop()  # 获取当前事件循环
        if loop.is_closed():  # 如果事件循环已关闭，创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(x_job(x_client, subscriptions, report_generator, notifier))  # 运行异步任务
    except Exception as e:
        LOG.error(f"运行x_job时发生错误：{e}")
    finally:
        if not loop.is_closed():  # 仅在未关闭时关闭事件循环
            loop.close()  # 关闭事件循环

def hn_topic_job(hacker_news_client, report_generator):
    LOG.info("[开始执行定时任务]Hacker News 热点话题跟踪")
    markdown_file_path = hacker_news_client.export_top_stories()

    if markdown_file_path is None:
        LOG.error("获取Hacker News失败")
    else:
        _, _ = report_generator.generate_hn_topic_report(markdown_file_path)
        LOG.info(f"[定时任务执行完毕]")


def hn_daily_job(report_generator, notifier):
    LOG.info("[开始执行定时任务]Hacker News 今日前沿技术趋势")
    # 获取当前日期，并格式化为 'YYYY-MM-DD' 格式
    date = datetime.now().strftime('%Y-%m-%d')
    # 生成每日汇总报告的目录路径
    directory_path = os.path.join('hacker_news', date)
    # 确保目录存在
    os.makedirs(directory_path, exist_ok=True)
    # 生成每日汇总报告并保存
    report, _ = report_generator.generate_hn_daily_report(directory_path)
    notifier.notify_hn_report(date, report)
    LOG.info(f"[定时任务执行完毕]")


def main():
    # 设置信号处理器
    signal.signal(signal.SIGTERM, graceful_shutdown)

    config = Config()  # 创建配置实例
    github_client = GitHubClient(config.github_token)  # 创建GitHub客户端实例
    hacker_news_client = HackerNewsClient() # 创建 Hacker News 客户端实例
    notifier = Notifier(config.email)  # 创建通知器实例
    llm = LLM(config)  # 创建语言模型实例
    report_generator = ReportGenerator(llm, config.report_types)  # 创建报告生成器实例
    subscription_manager = SubscriptionManager(config.subscriptions_file)  # 创建订阅管理器实例

    x_client = XClient(config.x_user, config.x_email, config.x_pwd)

    # 启动时立即执行（如不需要可注释）
    # github_job(subscription_manager, github_client, report_generator, notifier, config.freq_days)
    # asyncio.run(x_job(x_client, config.x_subscriptions, report_generator, notifier))
    # hn_daily_job(report_generator, notifier)

    # 安排 GitHub 的定时任务
    schedule.every(config.freq_days).days.at(
        config.exec_time
    ).do(github_job, subscription_manager, github_client, report_generator, notifier, config.freq_days)

    # 安排 hn_topic_job 每4小时执行一次，从0点开始
    schedule.every(4).hours.at(":00").do(hn_topic_job, hacker_news_client, report_generator)

    # 安排 hn_daily_job 每天早上10点执行一次
    schedule.every().day.at("10:00").do(hn_daily_job, report_generator, notifier)

    schedule.every().day.at("09:00").do(run_x_job, x_client, config.x_subscriptions, report_generator, notifier)

    try:
        # 在守护进程中持续运行
        while True:
            schedule.run_pending()
            time.sleep(1)  # 短暂休眠以减少 CPU 使用
    except Exception as e:
        LOG.error(f"主进程发生异常: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

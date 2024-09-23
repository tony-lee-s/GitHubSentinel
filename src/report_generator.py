import os
import re

from logger import LOG  # 导入日志模块

class ReportGenerator:
    def __init__(self, llm, report_types):
        self.llm = llm  # 初始化时接受一个LLM实例，用于后续生成报告
        self.report_types = report_types
        self.prompts = {}  # 存储所有预加载的提示信息
        self._preload_prompts()

    def _preload_prompts(self):
        """
        预加载所有可能的提示文件，并存储在字典中。
        """
        for report_type in self.report_types:  # 使用从配置中加载的报告类型
            prompt_file = f"prompts/{report_type}_{self.llm.model}_prompt.txt"
            if not os.path.exists(prompt_file):
                LOG.error(f"提示文件不存在: {prompt_file}")
                raise FileNotFoundError(f"提示文件未找到: {prompt_file}")
            with open(prompt_file, "r", encoding='utf-8') as file:
                self.prompts[report_type] = file.read()

    def generate_report(self, markdown_file_path, report_type, output_suffix):
        """
        通用的报告生成方法。
        """
        with open(markdown_file_path, 'r') as file:
            markdown_content = file.read()

        system_prompt = self.prompts.get(report_type)
        report = self.llm.generate_report(system_prompt, markdown_content)

        report_file_path = os.path.splitext(markdown_file_path)[0] + output_suffix
        with open(report_file_path, 'w+') as report_file:
            report_file.write(report)

        LOG.info(f"{report_type} 报告已保存到 {report_file_path}")
        return report, report_file_path

    def generate_x_report(self, markdown_file_path):
        """
        生成 X 项目的报告。如果 markdown 内容长度超过 3000 字符，则分割成多个部分分别生成报告，然后合并这些报告。
        """
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            markdown_content = file.read()

        # 提取标题
        title_end_index = markdown_content.find("\n\n") + 2
        title = markdown_content[:title_end_index]
        content = markdown_content[title_end_index:]

        # 使用正则表达式匹配每条 tweet 的时间戳
        tweet_pattern = re.compile(r'### \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:\d{2}')
        tweets = tweet_pattern.split(content)
        timestamps = tweet_pattern.findall(content)

        # 重新组合每条 tweet 与其时间戳
        tweets = [f"{timestamps[i]}\n{tweets[i + 1]}" for i in range(len(timestamps))]

        # 分割 tweets 内容
        parts = self._split_tweets_into_parts(tweets, title)

        reports = []
        system_prompt = self.prompts.get("x") if len(parts) == 1 else self._load_prompt("x_short_ollama_prompt.txt")

        for part in parts:
            report = self.llm.generate_report(system_prompt, part)
            reports.append(report)

        full_report = "\n".join(reports)
        LOG.info(f"full_report:{full_report}")

        # 合并所有部分的报告
        full_report = f"{title}\n" + full_report

        report_file_path = os.path.splitext(markdown_file_path)[0] + "_report.md"
        self._save_report(report_file_path, full_report)

        return full_report, report_file_path

    def _split_tweets_into_parts(self, tweets, title):
        """
        将 tweets 分割成多个部分，每部分的长度不超过 1000 字符。
        """
        parts = []
        current_part = title
        for tweet in tweets:
            if len(current_part) + len(tweet) > 1000:
                parts.append(current_part)
                current_part = title + tweet
            else:
                current_part += tweet
        parts.append(current_part)
        return parts

    def _load_prompt(self, prompt_filename):
        """
        加载指定的提示文件内容。
        """
        with open(f"prompts/{prompt_filename}", "r", encoding='utf-8') as file:
            return file.read()

    def _save_report(self, report_file_path, report_content):
        """
        保存报告到指定的文件路径。
        """
        with open(report_file_path, 'w+', encoding='utf-8') as report_file:
            report_file.write(report_content)
        LOG.info(f"x 报告已保存到 {report_file_path}")

    def generate_github_report(self, markdown_file_path):
        """
        生成 GitHub 项目的报告，并保存为 {original_filename}_report.md。
        """
        return self.generate_report(markdown_file_path, "github", "_report.md")

    def generate_hn_topic_report(self, markdown_file_path):
        """
        生成 Hacker News 小时主题的报告，并保存为 {original_filename}_topic.md。
        """
        return self.generate_report(markdown_file_path, "hacker_news_hours_topic", "_topic.md")

    def generate_hn_daily_report(self, directory_path):
        """
        生成 Hacker News 每日汇总的报告，并保存到 hacker_news/tech_trends/ 目录下。
        这里的输入是一个目录路径，其中包含所有由 generate_hn_topic_report 生成的 *_topic.md 文件。
        """
        markdown_content = self._aggregate_topic_reports(directory_path)
        system_prompt = self.prompts.get("hacker_news_daily_report")

        base_name = os.path.basename(directory_path.rstrip('/'))
        report_file_path = os.path.join("hacker_news/tech_trends/", f"{base_name}_trends.md")

        # 确保 tech_trends 目录存在
        os.makedirs(os.path.dirname(report_file_path), exist_ok=True)

        report = self.llm.generate_report(system_prompt, markdown_content)

        with open(report_file_path, 'w+') as report_file:
            report_file.write(report)

        LOG.info(f"Hacker News 每日汇总报告已保存到 {report_file_path}")
        return report, report_file_path

    def _aggregate_topic_reports(self, directory_path):
        """
        聚合目录下所有以 '_topic.md' 结尾的 Markdown 文件内容，生成每日汇总报告的输入。
        """

        # 判断目录是否存在
        if not os.path.exists(directory_path):
            LOG.error(f"目录不存在: {directory_path}")
            raise FileNotFoundError(f"目录未找到: {directory_path}")

        markdown_content = ""
        for filename in os.listdir(directory_path):
            if filename.endswith("_topic.md"):
                with open(os.path.join(directory_path, filename), 'r') as file:
                    markdown_content += file.read() + "\n"
        return markdown_content

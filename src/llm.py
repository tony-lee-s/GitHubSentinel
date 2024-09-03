import os
import json
from openai import AzureOpenAI  # 导入OpenAI库用于访问GPT模型
from logger import LOG  # 导入日志模块


class LLM:
    def __init__(self):
        # 创建一个OpenAI客户端实例
        self.client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("OPENAI_API_BASE")
        )

    def generate_report(self, prompt_file_name, markdown_content, dry_run=False):

        # 从TXT文件加载提示信息
        with open(f"prompts/{prompt_file_name}", "r", encoding='utf-8') as file:
            system_prompt = file.read()

        # 使用从TXT文件加载的提示信息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown_content},
        ]

        if dry_run:
            # 如果启用了dry_run模式，将不会调用模型，而是将提示信息保存到文件中
            LOG.info("Dry run mode enabled. Saving prompt to file.")
            with open("daily_progress/prompt.txt", "w+") as f:
                # 格式化JSON字符串的保存
                json.dump(messages, f, indent=4, ensure_ascii=False)
            LOG.debug("Prompt已保存到 daily_progress/prompt.txt")

            return "DRY RUN"

        # 日志记录开始生成报告
        LOG.info("使用 GPT 模型开始生成报告。")

        try:
            # 调用OpenAI GPT模型生成报告
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 指定使用的模型版本
                messages=messages
            )
            LOG.debug("GPT response: {}", response)
            # 返回模型生成的内容
            return response.choices[0].message.content
        except Exception as e:
            # 如果在请求过程中出现异常，记录错误并抛出
            LOG.error(f"生成报告时发生错误：{e}")

    def generate_daily_report(self, markdown_content, dry_run=False):
        return self.generate_report("report_prompt.txt", markdown_content, dry_run)

    def generate_hacker_news_report(self, markdown_content, dry_run=False):
        return self.generate_report("hacker_news_prompt.txt", markdown_content, dry_run)


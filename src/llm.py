# src/llm.py

import os
from openai import AzureOpenAI

class LLM:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("OPENAI_API_BASE")
        )

    def generate_daily_report(self, markdown_content, dry_run=False):
        system_prompt = f"""You are a GitHub project progress summary expert.
        Now you need to summarize a brief report based on the latest progress of the project.  
        The requirements are as follows:  
        1. You must summarize the report in Chinese;  
        2. Combine similar items based on functionality;  
        3. The report should include at least:  
            1) New features;  
            2) Major improvements;  
            3) Bug fixes.
        """
        prompt = f"Here is the latest progress of the project:\n\n{markdown_content}"
        if dry_run:
            with open("daily_progress/prompt.txt", "w+") as f:
                f.write(prompt)
            return "DRY RUN"

        print("Before call GPT")
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        print("After call GPT")
        print(response)
        return response.choices[0].message.content

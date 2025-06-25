# config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("错误：请在 .env 文件中设置您的 OPENAI_API_KEY")

if not DIFY_API_KEY:
    raise ValueError("错误：请在 .env 文件中设置您的 DIFY_API_KEY")
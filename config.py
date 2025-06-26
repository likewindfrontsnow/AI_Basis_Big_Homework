# config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv(override=True)

DIFY_API_KEY = os.getenv("DIFY_API_KEY")
FILE_PATH = os.getenv("FILE_PATH")
OUTPUT_CHUNK_FOLDER = os.getenv("OUTPUT_CHUNK_FOLDER", "output_chunks")  
FINAL_TRANSCRIPT_FILE = os.getenv("FINAL_TRANSCRIPT_FILE", "source_transcript.txt")  
USER= os.getenv("USER", "user")  
INPUT_VARIABLE_NAME = os.getenv("INPUT_VARIABLE_NAME", "source_transcript")  
OUTPUT_VARIABLE_NAME = os.getenv("OUTPUT_VARIABLE_NAME", "final_output")  
LOCAL_SAVE_PATH = os.getenv("LOCAL_SAVE_PATH", "result.md")  


if not DIFY_API_KEY:
    raise ValueError("错误：请在 .env 文件中设置您的 DIFY_API_KEY")
if not FILE_PATH:
    raise ValueError("错误：请在 .env 文件中设置您的 FILE_PATH")
if not OUTPUT_CHUNK_FOLDER:
    raise ValueError("错误：请在 .env 文件中设置您的 OUTPUT_CHUNK_FOLDER")
if not FINAL_TRANSCRIPT_FILE:
    raise ValueError("错误：请在 .env 文件中设置您的 FINAL_TRANSCRIPT_FILE")
if not USER:
    raise ValueError("错误：请在 .env 文件中设置您的 USER")
if not INPUT_VARIABLE_NAME:
    raise ValueError("错误：请在 .env 文件中设置您的 INPUT_VARIABLE_NAME")
if not OUTPUT_VARIABLE_NAME:
    raise ValueError("错误：请在 .env 文件中设置您的 OUTPUT_VARIABLE_NAME")
if not LOCAL_SAVE_PATH:
    raise ValueError("错误：请在 .env 文件中设置您的 LOCAL_SAVE_PATH")

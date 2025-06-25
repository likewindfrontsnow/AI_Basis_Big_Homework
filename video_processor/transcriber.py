# video_processor/transcriber.py
from openai import OpenAI
import config

# 初始化 OpenAI 客户端
client = OpenAI(api_key=config.OPENAI_API_KEY)

def transcribe_single_audio_chunk(audio_path: str) -> str | None:
    """调用 Whisper API 转录单个音频文件"""
    print(f"  > 正在转录: {audio_path}")
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
              model="whisper-1", 
              file=audio_file
            )
        print(f"  > 转录成功！")
        return transcription.text
    except Exception as e:
        print(f"  > 调用 Whisper API 失败: {e}")
        return None
# transcriber.py
from openai import OpenAI, APIError, AuthenticationError, APIConnectionError, RateLimitError
import os
from utils import retry # <-- Import the retry decorator

# Define which OpenAI errors are worth retrying
RETRYABLE_EXCEPTIONS = (APIError, APIConnectionError, RateLimitError)

@retry(max_retries=3, delay=5, allowed_exceptions=RETRYABLE_EXCEPTIONS) # <-- Apply retry decorator
def transcribe_single_audio_chunk(audio_path: str, openai_api_key: str) -> str | None:
    """调用 Whisper API 转录单个音频文件"""
    client = OpenAI(api_key=openai_api_key) # Initialization is lightweight
    
    audio_filename = os.path.basename(audio_path)
    print(f"  > 正在转录: {audio_filename}")
    
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
              model="whisper-1", 
              file=audio_file
            )
        print(f"  > ✅ 文件 '{audio_filename}' 转录成功！")
        return transcription.text
    
    except FileNotFoundError:
        print(f"  > 错误：找不到音频文件: {audio_path}")
        # No retry for file not found
        return None 
    except AuthenticationError as e:
        print("  > OpenAI API 错误：身份验证失败，请检查您的 OPENAI_API_KEY 是否正确。")
        # No retry for auth errors, as it won't resolve itself.
        # We raise it so the main process can catch it and report a persistent error.
        raise e
    except RETRYABLE_EXCEPTIONS as e:
        print(f"  > 调用 Whisper API 时发生可重试错误: {e}")
        # Re-raise to trigger the retry decorator
        raise e
    except Exception as e:
        # For other unexpected errors
        print(f"  > 调用 Whisper API 时发生未知失败: {e}")
        raise e # Re-raise to be caught by the main process
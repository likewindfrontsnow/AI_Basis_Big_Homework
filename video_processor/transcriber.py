from openai import OpenAI,APIError, AuthenticationError

def transcribe_single_audio_chunk(audio_path: str,openai_api_key: str) -> str | None:
    """调用 Whisper API 转录单个音频文件"""
    try:
        client= OpenAI(api_key=openai_api_key)
    except Exception as e:
        print(f"初始化 OpenAI 客户端失败: {e}，请检查是否填写了OPENAI的API密钥。")
        return None
    
    if not client:
        print("  > 错误：OpenAI 客户端未初始化，无法进行转录。")
        return None
    
    print(f"  > 正在转录: {audio_path}")
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
              model="whisper-1", 
              file=audio_file
            )
        print(f"  > 转录成功！")
        return transcription.text
    except FileNotFoundError:
        print(f"  > 错误：找不到音频文件: {audio_path}")
        return None
    except AuthenticationError:
        print("  > OpenAI API 错误：身份验证失败，请检查您的 OPENAI_API_KEY 是否正确。")
        return None
    except APIError as e:
        print(f"  > 调用 Whisper API 时发生服务端错误: {e}")
        return None
    except Exception as e:
        print(f"  > 调用 Whisper API 时发生未知失败: {e}")
        return None
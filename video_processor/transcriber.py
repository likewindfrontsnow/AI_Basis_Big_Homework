# transcriber.py
import os
import functools
import torch
from openai import OpenAI, APIError, AuthenticationError, APIConnectionError, RateLimitError
from utils import retry

# 尝试导入 whisper 和 faster_whisper 库
try:
    import whisper
except ImportError:
    whisper = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from opencc import OpenCC
    # 正确的初始化方式是不带 .json 后缀
    cc = OpenCC('t2s')
except ImportError:
    OpenCC = None
    cc = None


@functools.lru_cache(maxsize=None)
def load_local_model(model_identifier: str):
    """
    根据传入的标识符，动态加载并缓存本地模型。
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if model_identifier.startswith("faster-whisper"):
        if WhisperModel is None:
            raise ImportError("Faster-Whisper 未安装。请运行 `pip install faster-whisper`。")
        
        model_name = model_identifier.split('-', 2)[2]
        compute_type = "float16" if device == "cuda" else "int8"
            
        print(f"正在加载 Faster-Whisper 模型 '{model_name}' (设备: {device.upper()}, 计算类型: {compute_type})...")
        # --- 确保这一行已被修改 ---
        # 添加 local_files_only=False 以修复模型下载/加载错误
        model = WhisperModel(model_name, device=device, compute_type=compute_type, local_files_only=False)
        # --- 修改结束 ---
        print(f"Faster-Whisper 模型 '{model_name}' 加载成功。")
        return model

    elif model_identifier.startswith("whisper"):
        if whisper is None:
            raise ImportError("OpenAI-Whisper 未安装。请运行 `pip install openai-whisper`。")
        
        model_name = model_identifier.split('-', 1)[1]
        print(f"正在加载官方 Whisper 模型 '{model_name}' (设备: {device.upper()})...")
        model = whisper.load_model(model_name, device=device)
        print(f"官方 Whisper 模型 '{model_name}' 加载成功。")
        return model
        
    else:
        raise ValueError(f"无法识别的模型标识符: {model_identifier}")

def transcribe_local_with_choice(audio_path: str, model_identifier: str) -> str | None:
    """
    根据用户选择，使用相应的本地模型进行转录，并自动将中文结果转为简体。
    """
    audio_filename = os.path.basename(audio_path)
    print(f"  > 正在使用模型 '{model_identifier}' 转录: {audio_filename}")
    
    try:
        model = load_local_model(model_identifier)
        
        full_text = ""
        detected_language = ""

        if isinstance(model, WhisperModel):
            segments, info = model.transcribe(audio_path, beam_size=5)
            full_text = "".join(segment.text for segment in segments)
            detected_language = info.language
        else:
            result = model.transcribe(audio_path, fp16=torch.cuda.is_available())
            full_text = result.get('text', '')
            detected_language = result.get('language', '')

        if detected_language == 'zh' and cc is not None:
            print(f"  > 检测到中文内容，正在转换为简体中文...")
            simplified_text = cc.convert(full_text)
            print(f"  > ✅ 转换完成。")
            full_text = simplified_text
        elif detected_language == 'zh' and cc is None:
             print("  > 警告: 检测到中文内容，但 OpenCC 未安装，无法转换为简体。请运行 `pip install opencc-python-reimplemented`。")

        print(f"  > ✅ 文件 '{audio_filename}' 使用 '{model_identifier}' 转录成功！")
        return full_text
        
    except Exception as e:
        print(f"  > ❌ 使用本地模型 '{model_identifier}' 转录时发生未知失败: {e}")
        raise e

RETRYABLE_EXCEPTIONS = (APIError, APIConnectionError, RateLimitError)
@retry(max_retries=3, delay=5, allowed_exceptions=RETRYABLE_EXCEPTIONS)
def transcribe_single_audio_chunk(audio_path: str, openai_api_key: str) -> str | None:
    client = OpenAI(api_key=openai_api_key)
    audio_filename = os.path.basename(audio_path)
    print(f"  > 正在使用 OpenAI API 转录: {audio_filename}")
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
              model="whisper-1", 
              file=audio_file
            )
        print(f"  > ✅ 文件 '{audio_filename}' API 转录成功！")
        
        text_to_check = transcription.text
        if cc is not None and any('\u4e00' <= char <= '\u9fff' for char in text_to_check[:100]):
            print(f"  > 检测到中文内容，正在转换为简体中文...")
            simplified_text = cc.convert(text_to_check)
            print(f"  > ✅ 转换完成。")
            return simplified_text

        return text_to_check
    
    except Exception as e:
        print(f"  > 调用 Whisper API 时发生未知失败: {e}")
        raise e
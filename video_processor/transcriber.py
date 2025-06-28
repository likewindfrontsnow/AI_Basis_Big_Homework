# transcriber.py
import os
import functools
import torch
from openai import OpenAI, APIError, AuthenticationError, APIConnectionError, RateLimitError
from utils import retry

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
    cc_t2s = OpenCC('t2s')
    cc_s2t = OpenCC('s2t')
except ImportError:
    OpenCC = None
    cc_t2s = None
    cc_s2t = None

LOCAL_MODEL_PATHS = {
    "faster-whisper-large-v3": os.path.join("大模型", "faster-whisper-large-v3"),
    "whisper-large-v3": os.path.join("大模型", "whisper", "large-v3.pt"),
    "whisper-medium": os.path.join("大模型", "whisper", "medium.pt"),
    "whisper-base": os.path.join("大模型", "whisper", "base.pt")
}

@functools.lru_cache(maxsize=None)
def load_local_model(model_identifier: str):
    model_path = LOCAL_MODEL_PATHS.get(model_identifier)
    if not model_path or not os.path.exists(model_path):
        raise FileNotFoundError(f"未在预设路径中找到模型 '{model_identifier}'。请检查“大模型”文件夹中的路径 '{model_path}' 是否正确。")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if model_identifier.startswith("faster-whisper"):
        if WhisperModel is None:
            raise ImportError("Faster-Whisper 未安装。请运行 `pip install faster-whisper`。")
        
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"正在从本地路径加载 Faster-Whisper 模型 '{model_path}' (设备: {device.upper()}, 计算类型: {compute_type})...")
        model = WhisperModel(model_path, device=device, compute_type=compute_type)
        print(f"Faster-Whisper 模型加载成功。")
        return model

    elif model_identifier.startswith("whisper"):
        if whisper is None:
            raise ImportError("OpenAI-Whisper 未安装。请运行 `pip install openai-whisper`。")
        
        print(f"正在从本地路径加载官方 Whisper 模型 '{model_path}' (设备: {device.upper()})...")
        model = whisper.load_model(model_path, device=device)
        print(f"官方 Whisper 模型加载成功。")
        return model
        
    else:
        raise ValueError(f"无法识别的模型标识符: {model_identifier}")

def transcribe_local_with_choice(audio_path: str, model_identifier: str, output_chinese_format: str) -> str | None:
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

        if detected_language == 'zh':
            if output_chinese_format == 'simplified' and cc_t2s:
                print(f"  > 检测到中文，按要求转换为 [简体中文]...")
                full_text = cc_t2s.convert(full_text)
            elif output_chinese_format == 'traditional' and cc_s2t:
                print(f"  > 检测到中文，按要求确保为 [繁體中文]...")
                full_text = cc_s2t.convert(full_text)
            elif OpenCC is None:
                 print("  > 警告: 检测到中文内容，但 OpenCC 未安装，无法进行简繁转换。")

        print(f"  > ✅ 文件 '{audio_filename}' 使用 '{model_identifier}' 转录成功！")
        return full_text
        
    except Exception as e:
        print(f"  > ❌ 使用本地模型 '{model_identifier}' 转录时发生未知失败: {e}")
        raise e

@retry(max_retries=3, delay=5, allowed_exceptions=(APIError, APIConnectionError, RateLimitError))
def transcribe_single_audio_chunk(audio_path: str, openai_api_key: str, output_chinese_format: str) -> str | None:
    client = OpenAI(api_key=openai_api_key)
    audio_filename = os.path.basename(audio_path)
    print(f"  > 正在使用 OpenAI API 转录: {audio_filename}")
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        print(f"  > ✅ 文件 '{audio_filename}' API 转录成功！")
        
        text_to_check = transcription.text
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text_to_check[:100])
        if is_chinese:
            if output_chinese_format == 'simplified' and cc_t2s:
                print(f"  > 检测到中文，按要求转换为 [简体中文]...")
                return cc_t2s.convert(text_to_check)
            elif output_chinese_format == 'traditional' and cc_s2t:
                print(f"  > 检测到中文，按要求确保为 [繁體中文]...")
                return cc_s2t.convert(text_to_check)
        
        return text_to_check
    
    except Exception as e:
        print(f"  > 调用 Whisper API 时发生未知失败: {e}")
        raise e
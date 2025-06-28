# transcriber.py
import os
import functools
import torch
from openai import OpenAI, APIError, AuthenticationError, APIConnectionError, RateLimitError
from utils import retry

# 尝试导入依赖，如果失败则设为 None
try:
    import whisper
except ImportError:
    whisper = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None

try:
    from opencc import OpenCC
    cc_t2s = OpenCC('t2s')
    cc_s2t = OpenCC('s2t')
except ImportError:
    OpenCC = None
    cc_t2s = None
    cc_s2t = None

# 定义本地模型的期望存放路径
LOCAL_MODEL_PATHS = {
    "faster-whisper-large-v3": os.path.join("大模型", "faster-whisper-large-v3"),
    "whisper-large-v3": os.path.join("大模型", "whisper"),
    "whisper-medium": os.path.join("大模型", "whisper"),
    "whisper-base": os.path.join("大模型", "whisper")
}

# 定义模型的源，用于自动下载
MODEL_SOURCES = {
    "faster-whisper-large-v3": {"repo_id": "Systran/faster-whisper-large-v3"},
    "whisper-large-v3": {"name": "large-v3"},
    "whisper-medium": {"name": "medium"},
    "whisper-base": {"name": "base"}
}

@functools.lru_cache(maxsize=None)
def load_local_model(model_identifier: str):
    """
    加载本地模型。如果模型文件不存在，则自动从源下载。
    使用 LRU 缓存来避免重复加载模型到内存。
    """
    model_path = LOCAL_MODEL_PATHS.get(model_identifier)
    if not model_path:
        raise ValueError(f"无法识别的模型标识符: {model_identifier}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # --- Faster-Whisper 模型处理逻辑 ---
    if model_identifier.startswith("faster-whisper"):
        if WhisperModel is None:
            raise ImportError("依赖缺失: Faster-Whisper 未安装。请运行 `pip install faster-whisper`。")
        if snapshot_download is None:
            raise ImportError("依赖缺失: huggingface_hub 未安装。请运行 `pip install huggingface_hub`。")

        # 检查模型是否存在，不存在则下载
        if not os.path.exists(model_path):
            print(f"本地模型 '{model_identifier}' 不存在于 '{model_path}'。")
            print("将开始自动从 Hugging Face Hub 下载，请耐心等待...")
            source_info = MODEL_SOURCES.get(model_identifier)
            if not source_info:
                raise ValueError(f"找不到模型 '{model_identifier}' 的下载源信息。")
            
            os.makedirs(model_path, exist_ok=True)
            try:
                snapshot_download(
                    repo_id=source_info["repo_id"], 
                    local_dir=model_path,
                    local_dir_use_symlinks=False # 建议在Windows上设为False
                )
                print("✅ 模型下载完成！")
            except Exception as e:
                raise RuntimeError(f"从 Hugging Face Hub 下载模型失败: {e}")

        # 加载模型
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"正在从本地路径加载 Faster-Whisper 模型 '{model_path}' (设备: {device.upper()}, 计算类型: {compute_type})...")
        model = WhisperModel(model_path, device=device, compute_type=compute_type)
        print(f"✅ Faster-Whisper 模型加载成功。")
        return model

    # --- 官方 Whisper 模型处理逻辑 ---
    elif model_identifier.startswith("whisper"):
        if whisper is None:
            raise ImportError("依赖缺失: OpenAI-Whisper 未安装。请运行 `pip install openai-whisper`。")
        
        # 对于官方 whisper，load_model 函数会处理下载逻辑
        # 我们只需提供模型名称和期望的下载根目录
        model_name = MODEL_SOURCES.get(model_identifier, {}).get("name")
        if not model_name:
            raise ValueError(f"找不到模型 '{model_identifier}' 的官方名称。")

        download_root = model_path
        os.makedirs(download_root, exist_ok=True)
        
        print(f"正在加载官方 Whisper 模型 '{model_name}' (设备: {device.upper()})...")
        print(f"模型将从 '{download_root}' 加载，如果不存在则会自动下载。")
        model = whisper.load_model(model_name, device=device, download_root=download_root)
        print(f"✅ 官方 Whisper 模型 '{model_name}' 加载成功。")
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

        if isinstance(model, WhisperModel): # Faster-Whisper
            segments, info = model.transcribe(audio_path, beam_size=5)
            full_text = "".join(segment.text for segment in segments)
            detected_language = info.language
        else: # Official Whisper
            result = model.transcribe(audio_path, fp16=torch.cuda.is_available())
            full_text = result.get('text', '')
            detected_language = result.get('language', '')

        if detected_language == 'zh':
            if OpenCC is None:
                print("  > 警告: 检测到中文内容，但 OpenCC 未安装，无法进行简繁转换。请运行 `pip install opencc-python-rebuilt`。")
            elif output_chinese_format == 'simplified' and cc_t2s:
                print(f"  > 检测到中文，按要求转换为 [简体中文]...")
                full_text = cc_t2s.convert(full_text)
            elif output_chinese_format == 'traditional' and cc_s2t:
                print(f"  > 检测到中文，按要求确保为 [繁體中文]...")
                full_text = cc_s2t.convert(full_text)

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
        # 使用更可靠的方式判断中文
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text_to_check[:100])
        if is_chinese:
            if OpenCC is None:
                print("  > 警告: 检测到中文内容，但 OpenCC 未安装，无法进行简繁转换。请运行 `pip install opencc-python-rebuilt`。")
            elif output_chinese_format == 'simplified' and cc_t2s:
                print(f"  > 检测到中文，按要求转换为 [简体中文]...")
                return cc_t2s.convert(text_to_check)
            elif output_chinese_format == 'traditional' and cc_s2t:
                print(f"  > 检测到中文，按要求确保为 [繁體中文]...")
                return cc_s2t.convert(text_to_check)
        
        return text_to_check
    
    except Exception as e:
        print(f"  > 调用 Whisper API 时发生未知失败: {e}")
        raise e
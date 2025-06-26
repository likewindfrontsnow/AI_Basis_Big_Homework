import subprocess
import os
import math
import concurrent.futures

def get_media_duration(media_path: str) -> float | None:
    """使用 ffprobe 获取媒体文件总时长（秒），适用于视频和音频。"""
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', media_path]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout)
    except FileNotFoundError:
        print("错误：找不到 ffprobe 命令。请确保 FFmpeg 已经安装并添加到了系统环境变量中。")
        return None
    except subprocess.CalledProcessError as e:
        print(f"ffprobe 执行失败，可能是文件已损坏或格式不支持: {e.stderr}")
        return None
    except Exception as e:
        print(f"获取媒体时长时发生错误: {e}")
        return None

def _process_chunk(args) -> str | None:
    """(工作函数) 处理单个音频块的生成。"""
    media_path, output_dir, chunk_duration, i, num_chunks = args
    start_time = i * chunk_duration
    output_filename = os.path.join(output_dir, f"chunk_{i+1:03d}.mp3")
    
    command = [
        'ffmpeg', '-i', media_path, 
        '-ss', str(start_time), 
        '-t', str(chunk_duration), 
        '-vn', '-acodec', 'libmp3lame', 
        '-q:a', '2', '-y', output_filename
    ]
    
    try:
        print(f"开始生成第 {i+1}/{num_chunks} 个音频块: {output_filename}")
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"完成生成第 {i+1}/{num_chunks} 个音频块。")
        return output_filename
    except subprocess.CalledProcessError as e:
        print(f"处理第 {i+1} 个音频块时失败: {e.stderr}")
        return None
    except FileNotFoundError:
        print("错误：找不到 ffmpeg 命令。")
        return None

def split_media_to_audio_chunks_generator(media_path: str, output_dir: str, chunk_duration: int = 600):
    """
    (生成器版本) 将媒体文件切分为音频块，并实时产出进度。
    产出事件: ('progress', 已完成数量, 总数量)
              ('result', 输出文件列表)
              ('error', 错误信息)
    """
    if not os.path.exists(media_path):
        yield 'error', f"错误：媒体文件 '{media_path}' 不存在。", None
        return
    
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    except OSError as e:
        yield 'error', f"错误：创建输出目录 '{output_dir}' 失败: {e}", None
        return

    duration = get_media_duration(media_path)
    if not duration:
        yield 'error', "无法获取媒体文件时长。", None
        return

    num_chunks = math.ceil(duration / chunk_duration)
    if num_chunks == 0:
        yield 'result', []
        return
        
    print(f"媒体总时长: {duration:.2f}秒, 将被切分为 {num_chunks} 个音频块。")

    tasks_args = [(media_path, output_dir, chunk_duration, i, num_chunks) for i in range(num_chunks)]
    
    output_files = []
    completed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_args = {executor.submit(_process_chunk, args): args for args in tasks_args}
        for future in concurrent.futures.as_completed(future_to_args):
            result = future.result()
            if result:
                output_files.append(result)
            completed_count += 1
            # 产出实时进度
            yield 'progress', completed_count, num_chunks

    if not output_files:
        yield 'error', "未能成功生成任何音频块。", None
        return
    
    # 产出最终结果
    yield 'result', sorted(output_files)


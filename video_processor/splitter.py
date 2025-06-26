# video_processor/splitter.py (并行处理版)
import subprocess
import os
import math
import concurrent.futures

def get_video_duration(video_path: str) -> float | None:
    """使用 ffprobe 获取视频总时长（秒）"""
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout)
    except FileNotFoundError:
        print("错误：找不到 ffprobe 命令。请确保 FFmpeg 已经安装并添加到了系统环境变量中。")
        return None
    except subprocess.CalledProcessError as e:
        print(f"ffprobe 执行失败，可能是视频文件已损坏或格式不支持: {e.stderr}")
        return None
    except ValueError:
        print("错误：无法将 ffprobe 的输出转换为数字。")
        return None
    except Exception as e:
        print(f"获取视频时长时发生错误: {e}")
        return None

def _process_chunk(args) -> str | None:
    """
    (工作函数) 处理单个音频块的生成。
    设计为接收一个元组参数，以方便线程池调用。
    """
    video_path, output_dir, chunk_duration, i, num_chunks = args
    start_time = i * chunk_duration
    output_filename = os.path.join(output_dir, f"chunk_{i+1:03d}.mp3")
    
    # 构建 ffmpeg 命令
    command = [
        'ffmpeg', '-i', video_path, 
        '-ss', str(start_time), 
        '-t', str(chunk_duration), 
        '-vn', '-acodec', 'libmp3lame', 
        '-q:a', '2', '-y', output_filename
    ]
    
    try:
        # 打印当前正在处理的任务
        print(f"开始生成第 {i+1}/{num_chunks} 个音频块: {output_filename}")
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"完成生成第 {i+1}/{num_chunks} 个音频块。")
        return output_filename
    except subprocess.CalledProcessError as e:
        # 如果单个块处理失败，打印错误并返回 None
        print(f"处理第 {i+1} 个音频块时失败: {e.stderr}")
        return None
    except FileNotFoundError:
        # 这个错误理论上只会在主函数中第一次调用时触发，但为了稳健也在这里加上
        print("错误：找不到 ffmpeg 命令。")
        return None

def split_video_to_audio_chunks(video_path: str, output_dir: str, chunk_duration: int = 600) -> list[str]:
    """
    (并行版) 将长视频切分成多个固定时长的音频小块，返回所有音频块的文件路径列表。
    """
    if not os.path.exists(video_path):
        print(f"错误：视频文件 '{video_path}' 不存在。")
        return []
    
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    except OSError as e:
        print(f"错误：创建输出目录 '{output_dir}' 失败: {e}")
        return []

    duration = get_video_duration(video_path)
    if not duration:
        return []

    num_chunks = math.ceil(duration / chunk_duration)
    print(f"视频总时长: {duration:.2f}秒, 将被切分为 {num_chunks} 个音频块。")

    # 准备要传递给每个工作线程的参数列表
    tasks_args = [
        (video_path, output_dir, chunk_duration, i, num_chunks) for i in range(num_chunks)
    ]
    
    output_files = []
    # 使用线程池执行并行任务
    # max_workers 可以根据你的CPU核心数来调整，None 表示使用默认值（通常是核心数*5）
    # 对于CPU密集型任务，设置为 os.cpu_count() 通常是个不错的选择
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # 使用 executor.map 来提交所有任务并保持结果的顺序
        # 它会自动处理参数的分发
        results = executor.map(_process_chunk, tasks_args)
        
        # 收集所有成功生成的文件路径
        for result in results:
            if result:
                output_files.append(result)

    if not output_files:
        print("--- 未能成功生成任何音频块。 ---")
    elif len(output_files) < num_chunks:
         print(f"--- 音频块生成部分完成！成功 {len(output_files)}/{num_chunks} 个。 ---")
    else:
        print("--- 所有音频块生成完毕！ ---")
        
    # 按文件名排序，确保输出列表的顺序是正确的
    return sorted(output_files)
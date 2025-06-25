# video_processor/splitter.py
import subprocess
import os
import math

def get_video_duration(video_path: str) -> float | None:
    """使用 ffprobe 获取视频总时长（秒）"""
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout)
    except FileNotFoundError:
        print("错误：找不到 ffprobe 命令。请确保 FFmpeg 已经安装并添加到了系统环境变量中。")
        return None
    except Exception as e:
        print(f"获取视频时长时发生错误: {e}")
        return None

def split_video_to_audio_chunks(video_path: str, output_dir: str, chunk_duration: int = 600) -> list[str]:
    """将长视频切分成多个固定时长的音频小块，返回所有音频块的文件路径列表。"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    duration = get_video_duration(video_path)
    if not duration:
        return []

    num_chunks = math.ceil(duration / chunk_duration)
    print(f"视频总时长: {duration:.2f}秒, 将被切分为 {num_chunks} 个音频块。")
    
    output_files = []
    for i in range(num_chunks):
        start_time = i * chunk_duration
        output_filename = os.path.join(output_dir, f"chunk_{i+1:03d}.mp3")
        command = ['ffmpeg', '-i', video_path, '-ss', str(start_time), '-t', str(chunk_duration), '-vn', '-acodec', 'libmp3lame', '-q:a', '2', '-y', output_filename]
        
        try:
            print(f"正在生成第 {i+1}/{num_chunks} 个音频块: {output_filename}")
            subprocess.run(command, check=True, capture_output=True, text=True)
            output_files.append(output_filename)
        except subprocess.CalledProcessError as e:
            print(f"处理第 {i+1} 个音频块时失败: {e.stderr}")
            continue
            
    print("--- 所有音频块生成完毕！ ---")
    return output_files
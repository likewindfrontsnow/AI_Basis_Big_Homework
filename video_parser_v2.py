import os
from moviepy.editor import VideoFileClip
import math

def segment_video(video_path: str, output_dir: str = "output", segment_duration: int = 120):
    """
    将视频文件按指定时长切片，并分别保存视频片段和对应的音频。
    (V2: 修复了循环处理中的资源占用问题)

    :param video_path: 输入的视频文件路径。
    :param output_dir: 输出文件夹路径。
    :param segment_duration: 每个片段的时长（秒），默认为120秒（2分钟）。
    """
    if not os.path.exists(video_path):
        print(f"错误：视频文件不存在于 {video_path}")
        return

    print(f"正在创建输出目录: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    specific_output_dir = os.path.join(output_dir, video_name)
    os.makedirs(specific_output_dir, exist_ok=True)
    print(f"文件将被保存在: {specific_output_dir}")

    # 先获取一次总时长，用于计算总片段数
    with VideoFileClip(video_path) as temp_clip:
        duration = temp_clip.duration
    
    total_segments = math.ceil(duration / segment_duration)
    print(f"视频总时长: {duration:.2f} 秒，将被切分为 {total_segments} 个片段。")

    print("="*20)
    print("开始处理视频分段...")
    print("="*20)

    for i in range(total_segments):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)
        segment_id = i + 1

        print(f"\n--- 正在处理片段 {segment_id}/{total_segments} (时间: {start_time:.2f}s -> {end_time:.2f}s) ---")

        clip = None
        sub_clip = None
        try:
            # 【核心修改】在循环内部加载视频，确保每次都是新的文件句柄
            clip = VideoFileClip(video_path)
            
            # 剪切视频片段
            sub_clip = clip.subclip(start_time, end_time)

            # 定义输出文件名
            segment_video_filename = os.path.join(specific_output_dir, f"segment_{segment_id}.mp4")

            # 保存视频片段 (包含了音频)
            sub_clip.write_videofile(segment_video_filename, codec="libx264", audio_codec="aac")
            
            print(f"--- 片段 {segment_id} 已成功保存至 {segment_video_filename} ---")

        except Exception as e:
            print(f"处理片段 {segment_id} 时发生错误: {e}")
        finally:
            # 【核心修改】确保在每次循环结束时，都释放所有资源
            if sub_clip:
                sub_clip.close()
            if clip:
                clip.close()
    
    print("\n所有片段处理完成！")


# --- 主程序入口 ---
if __name__ == "__main__":
    test_video_path = "course_video.mp4"
    
    if os.path.exists(test_video_path):
        segment_video(video_path=test_video_path)
    else:
        print("="*50)
        print(f"未找到测试视频 '{test_video_path}'")
        print("请将你的视频文件放在此目录下，并更新脚本中的 'test_video_path' 变量。")
        print("="*50)
# main.py
import time
import os
from video_processor.splitter import split_video_to_audio_chunks
from video_processor.transcriber import transcribe_single_audio_chunk
# 从您重命名后的文件中导入
from dify_api_text import run_workflow

# --- 配置 ---
DIFY_API_KEY = "app-Ny5hgY02NGRetPfUJwh4g2OV"  # <<< 请把这里换成你的 Dify API Key
FILE_PATH = 'test.mp4'                      # <<< 请把这里换成你的视频文件名
OUTPUT_CHUNK_FOLDER = 'audio_chunks'        # 保存音频切片的文件夹
FINAL_TRANSCRIPT_FILE = 'source_transcript.txt' # 最终文字稿保存的文件名
USER = "balabala"                           # 用户标识
INPUT_VARIABLE_NAME = "source_transcript"   # Dify 工作流中定义的输入变量名
OUTPUT_VARIABLE_NAME = "final_output"     # Dify 工作流中定义的输出变量名
LOCAL_SAVE_PATH = "result.md"               # 最终智能笔记的保存路径


def generate_transcript_from_video(video_path: str, output_dir: str, transcript_save_path: str) -> str | None:
    """
    一个完整的处理流程：从视频文件生成文字稿，并保存到文件。
    如果成功，返回完整的文字稿字符串；如果失败，返回 None。
    """
    # 步骤一：切分视频
    print("\n--- 步骤 1: 开始切分视频为音频块 ---")
    audio_chunks = split_video_to_audio_chunks(
        video_path=video_path,
        output_dir=output_dir,
        chunk_duration=600  # 10分钟一个切片
    )
    
    if not audio_chunks:
        print("音频切分失败，程序退出。请检查 FFmpeg 是否安装以及视频文件路径是否正确。")
        return None

    # 步骤二：循环处理每个音频块
    print("\n--- 步骤 2: 开始逐个转录音频块 ---")
    all_transcripts = []
    for i, chunk_path in enumerate(audio_chunks):
        print(f"处理第 {i+1}/{len(audio_chunks)} 个音频块...")
        transcript_fragment = transcribe_single_audio_chunk(chunk_path)
        if transcript_fragment:
            all_transcripts.append(transcript_fragment)
        time.sleep(1) # 礼貌性等待，避免API调用过于频繁

    # 步骤三：汇总并保存最终文字稿
    if not all_transcripts:
        print("所有音频块都未能成功转录，程序退出。")
        return None

    print("\n--- 步骤 3: 正在汇总所有文字稿 ---")
    full_transcript = "\n\n".join(all_transcripts)
    
    try:
        with open(transcript_save_path, "w", encoding="utf-8") as f:
            f.write(full_transcript)
        print(f"任务完成！完整文字稿已保存到: {transcript_save_path}")
        return full_transcript
    except IOError as e:
        print(f"保存文字稿文件时出错: {e}")
        return None


def process_transcript_with_dify(transcript_text: str):
    """
    使用 Dify 工作流处理文字稿并保存最终结果。
    """
    print("\n--- 步骤 4: 将文字稿提交给 Dify 工作流进行处理 ---")
    
    workflow_success = run_workflow(
        input_text=transcript_text,
        user=USER,
        dify_api_key=DIFY_API_KEY,
        input_variable_name=INPUT_VARIABLE_NAME,
        output_variable_name=OUTPUT_VARIABLE_NAME,
        local_save_path=LOCAL_SAVE_PATH,
    )

    if workflow_success:
        print(f"\n🎉 恭喜！智能笔记已生成，请查看文件: {LOCAL_SAVE_PATH}")
    else:
        print("\n❌ Dify 工作流执行失败。请检查控制台日志以获取更多信息。")


if __name__ == '__main__':
    print("--- 大学生智能笔记 Agent 启动 ---")

    # 主流程：先生成文字稿
    full_transcript = generate_transcript_from_video(
        video_path=FILE_PATH,
        output_dir=OUTPUT_CHUNK_FOLDER,
        transcript_save_path=FINAL_TRANSCRIPT_FILE
    )

    # 然后，如果文字稿成功生成，再用Dify处理
    if full_transcript:
        process_transcript_with_dify(full_transcript)
    else:
        print("\n由于未能生成文字稿，无法继续执行 Dify 工作流。程序终止。")

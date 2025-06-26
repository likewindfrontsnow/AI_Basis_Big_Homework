# main.py
import concurrent.futures
import time
import os
import sys
from video_processor.splitter import split_video_to_audio_chunks
from video_processor.transcriber import transcribe_single_audio_chunk
from dify_api_text import run_workflow

# 初始化配置
try:
    from config import OPENAI_API_KEY,DIFY_API_KEY, FILE_PATH, OUTPUT_CHUNK_FOLDER, FINAL_TRANSCRIPT_FILE, USER, INPUT_VARIABLE_NAME, OUTPUT_VARIABLE_NAME, LOCAL_SAVE_PATH
except ValueError as e:
    print(f"{e}", file=sys.stderr)
    print("注意：为使配置生效，修改 .env文件后请保存并重新运行程序。", file=sys.stderr)
    sys.exit(1) # 配置错误，程序无法继续

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
        print("音频切分失败，程序退出。")
        return None

    # 步骤二：并行处理每个音频块
    print(f"\n--- 步骤 2: 开始并行转录 {len(audio_chunks)} 个音频块 ---")
    all_transcripts = []
    
    # max_workers 可以根据你的API速率限制来调整
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # 使用 executor.map 来并发执行转录任务
        # 它会保持结果的顺序与 audio_chunks 的顺序一致
        transcript_results = executor.map(
            lambda chunk: transcribe_single_audio_chunk(chunk, OPENAI_API_KEY),
            audio_chunks
        )
        
        # 收集结果
        for transcript_fragment in transcript_results:
            if transcript_fragment:
                all_transcripts.append(transcript_fragment)

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
    try:
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

    except KeyboardInterrupt:
        print("\n\n程序被用户中断。正在退出...")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序运行期间发生未捕获的严重错误: {e}", file=sys.stderr)
        sys.exit(1)
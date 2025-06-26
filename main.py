# main.py
import concurrent.futures
import time
import os
import sys
import shutil
from video_processor.splitter import split_video_to_audio_chunks
from video_processor.transcriber import transcribe_single_audio_chunk
from dify_api_text import run_workflow

def main_process_generator(video_path: str, openai_api_key: str, dify_api_key: str, output_filename: str):
    """
    一个生成器函数，执行整个流程并实时 yield 状态和进度。
    """
    # --- 准备工作 ---
    # 根据用户输入动态生成输出路径
    output_dir = "output_chunks"
    transcript_save_path = "source_transcript.txt"
    final_notes_save_path = f"{output_filename}.md" # 使用用户自定义文件名

    total_steps = 4 # 总共有4个主要步骤
    current_progress = 0
    
    # --- 步骤 1: 切分视频 ---
    yield "progress", current_progress / total_steps, "步骤 1/4: 正在切分视频为音频块..."
    
    # 定义一个回调函数来更新主进度条
    def split_progress_updater():
        # 这个函数什么也不用做，我们只利用 as_completed 来驱动进度
        pass

    audio_chunks = split_video_to_audio_chunks(
        video_path=video_path,
        output_dir=output_dir,
        chunk_duration=600
        # 这里暂时不传递回调，因为切分非常快，主要进度在转录
    )
    
    if not audio_chunks:
        yield "error", 0, "音频切分失败，程序退出。"
        return

    current_progress += 1
    yield "progress", current_progress / total_steps, f"视频切分完成，得到 {len(audio_chunks)} 个音频块。"

    # --- 步骤 2: 并行转录 ---
    yield "progress", current_progress / total_steps, f"步骤 2/4: 正在并行转录 {len(audio_chunks)} 个音频块..."
    
    all_transcripts = []
    num_transcribed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_chunk = {executor.submit(transcribe_single_audio_chunk, chunk, openai_api_key): chunk for chunk in audio_chunks}
        
        for future in concurrent.futures.as_completed(future_to_chunk):
            result = future.result()
            if result:
                all_transcripts.append(result)
            num_transcribed += 1
            # 产出详细的子进度
            yield "sub_progress", num_transcribed / len(audio_chunks), f"正在转录... ({num_transcribed}/{len(audio_chunks)})"

    if not all_transcripts:
        yield "error", 0, "所有音频块都未能成功转录，请检查网络或OpenAI API密钥。"
        return

    current_progress += 1
    yield "progress", current_progress / total_steps, "所有音频块转录完成！"
    
    # --- 步骤 3: 汇总保存 ---
    yield "progress", current_progress / total_steps, "步骤 3/4: 正在汇总文字稿..."
    full_transcript = "\n\n".join(all_transcripts)
    try:
        with open(transcript_save_path, "w", encoding="utf-8") as f:
            f.write(full_transcript)
    except IOError as e:
        yield "error", 0, f"保存临时文字稿失败: {e}"
        return

    current_progress += 1
    yield "progress", current_progress / total_steps, "文字稿汇总完成。"

    # --- 步骤 4: Dify 处理 ---
    yield "progress", current_progress / total_steps, "步骤 4/4: 正在提交给 Dify 工作流..."

    workflow_success = run_workflow(
        input_text=full_transcript,
        user="streamlit_user", # 可以硬编码或从界面获取
        dify_api_key=dify_api_key,
        input_variable_name="source_transcript", # 从config获取或硬编码
        output_variable_name="final_output",
        local_save_path=final_notes_save_path
    )
    
    if not workflow_success:
        yield "error", 0, "Dify 工作流执行失败。"
        return

    current_progress += 1
    yield "progress", current_progress / total_steps, "处理完成！"
    yield "done", final_notes_save_path, "🎉 恭喜！智能笔记已生成！"

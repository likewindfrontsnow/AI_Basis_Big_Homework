# main.py
import concurrent.futures
import time
import os
import sys
import shutil
from openai import AuthenticationError
from video_processor.splitter import split_media_to_audio_chunks_generator
from video_processor.transcriber import transcribe_single_audio_chunk
from dify_api_text import run_workflow_streaming

def main_process_generator(input_path: str, openai_api_key: str, dify_api_key: str, output_filename: str):
    """
    (更新版) 一个生成器函数，执行处理流程并实时产出状态、进度和LLM文本块。
    - 新增了对持久性错误的捕获和处理。
    """
    output_dir = "output_chunks"
    final_notes_save_path = f"{output_filename}.md"
    
    video_exts = {'.mp4', '.mov', '.mpeg', '.webm'}
    audio_exts = {'.mp3', '.m4a', '.wav', '.amr', '.mpga'}
    text_exts = {'.txt', '.md', '.mdx', '.markdown', '.pdf', '.html', '.xlsx', '.xls', '.doc', '.docx', '.csv', '.eml', '.msg', '.pptx', '.ppt', '.xml', '.epub'}

    file_ext = os.path.splitext(input_path)[1].lower()
    current_progress = 0
    full_transcript = ""

    def run_dify_and_yield_results():
        """辅助生成器：运行Dify工作流并处理事件。"""
        final_llm_output_chunks = []
        dify_generator = run_workflow_streaming(
            input_text=full_transcript,
            user="streamlit_user",
            dify_api_key=dify_api_key,
            input_variable_name="source_transcript"
        )
        
        for event_type, data in dify_generator:
            if event_type == "text_chunk":
                final_llm_output_chunks.append(data)
                yield "llm_chunk", data
            elif event_type == "error":
                # This is now a persistent error after retries from dify_api_text
                yield "persistent_error", 0, data
                return
            elif event_type == "node_started":
                yield "progress_text", f"Dify 节点 '{data}' 已开始..."
            elif event_type == "workflow_finished":
                break
        
        final_text = "".join(final_llm_output_chunks)
        if not final_text:
            yield "persistent_error", 0, "处理失败：Dify 工作流在多次尝试后未返回任何内容。"
            return

        try:
            with open(final_notes_save_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            yield "save_path", final_notes_save_path
        except IOError as e:
            yield "persistent_error", 0, f"保存最终笔记文件失败: {e}"
            return

    # === 文本文件工作流 ===
    if file_ext in text_exts:
        # ... (text workflow remains largely the same, but now uses run_dify_and_yield_results which has retries)
        total_steps = 2
        yield "progress", 0 / total_steps, "步骤 1/2: 正在读取文本文档..."
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                full_transcript = f.read()
        except Exception as e:
            yield "persistent_error", 0, f"读取文件失败: {e}"
            return
        
        current_progress += 1
        yield "progress", current_progress / total_steps, "步骤 2/2: 正在提交给 Dify 工作流 (流式传输)..."
        
        final_path = None
        # The generator now handles persistent errors internally
        dify_gen = run_dify_and_yield_results()
        for event_type, value, *rest in dify_gen:
            if event_type == "persistent_error":
                yield event_type, value, rest[0]
                return
            elif event_type == "llm_chunk":
                yield event_type, value
            elif event_type == "progress_text":
                yield "progress", current_progress / total_steps, value
            elif event_type == "save_path":
                final_path = value
                
        if final_path:
            current_progress += 1
            yield "progress", current_progress / total_steps, "处理完成！"
            yield "done", final_path, "🎉 恭喜！智能笔记已生成！"
        return

    # === 视频和音频文件工作流 ===
    elif file_ext in video_exts or file_ext in audio_exts:
        is_video = file_ext in video_exts
        total_steps = 4 if is_video else 3
        
        step_name = "视频" if is_video else "音频"
        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在切分{step_name}为音频块..."
        
        splitter_generator = split_media_to_audio_chunks_generator(input_path, output_dir, 600)
        audio_chunks = []
        
        for event_type, val1, *val2 in splitter_generator:
            if event_type == 'progress':
                completed, total = val1, val2[0]
                yield "sub_progress", completed / total, f"正在切分... ({completed}/{total})"
            elif event_type == 'result':
                audio_chunks = val1
            elif event_type == 'error':
                yield "persistent_error", 0, val1 # Now treat this as a persistent error
                return
        
        if not audio_chunks:
            yield "persistent_error", 0, f"{step_name}切分失败，请确保已安装 FFmpeg 且文件格式受支持。"
            return
        
        yield "sub_progress", 1.0, f"✅ {step_name}切分全部完成！"
        current_progress += 1
        yield "progress", current_progress / total_steps, f"✅ {step_name}切分完成，准备开始转录..."

        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在并行转录 {len(audio_chunks)} 个音频块..."
        all_transcripts = [None] * len(audio_chunks)
        num_transcribed = 0

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_index = {
                    executor.submit(transcribe_single_audio_chunk, chunk, openai_api_key): i
                    for i, chunk in enumerate(audio_chunks)
                }
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    result = future.result() # This will raise an exception if retries fail
                    if result is not None:
                        all_transcripts[index] = result
                    else:
                         # This case should ideally not be hit if an exception is raised on failure
                        raise Exception(f"Transcription for chunk {index} returned None.")
                    
                    num_transcribed += 1
                    yield "sub_progress", num_transcribed / len(audio_chunks), f"正在转录... ({num_transcribed}/{len(audio_chunks)})"

        except AuthenticationError as e:
             yield "persistent_error", 0, f"OpenAI API 认证失败: {e}. 请检查您的 API 密钥。"
             return
        except Exception as e:
            yield "persistent_error", 0, f"转录过程中发生无法恢复的错误: {e}"
            return
        
        if any(t is None for t in all_transcripts):
            yield "persistent_error", 0, "部分音频块在多次尝试后仍转录失败。"
            return

        yield "sub_progress", 1.0, "✅ 音频转录全部完成！"
        current_progress += 1
        yield "progress", current_progress / total_steps, "所有音频块转录完成！"
        shutil.rmtree(output_dir, ignore_errors=True)

        if is_video:
            yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在汇总文字稿..."
        
        full_transcript = "\n\n".join(filter(None, all_transcripts))

        if is_video:
            current_progress += 1
            yield "progress", current_progress / total_steps, "文字稿汇总完成。"
            
        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在提交给 Dify 工作流 (流式传输)..."

        final_path = None
        dify_gen = run_dify_and_yield_results()
        for event_type, value, *rest in dify_gen:
            if event_type == "persistent_error":
                yield event_type, value, rest[0]
                return
            elif event_type == "llm_chunk":
                yield event_type, value
            elif event_type == "progress_text":
                 yield "progress", current_progress / total_steps, value
            elif event_type == "save_path":
                final_path = value
        
        if final_path:
            current_progress += 1
            yield "progress", current_progress / total_steps, "处理完成！"
            yield "done", final_path, "🎉 恭喜！智能笔记已生成！"
        return
        
    else:
        yield "error", 0, f"错误：不支持的文件类型 '{file_ext}'。请上传支持的视频、音频或文本文档。"
        return
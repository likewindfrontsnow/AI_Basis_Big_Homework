# main.py
import concurrent.futures
import time
import os
import shutil
from openai import AuthenticationError
from video_processor.splitter import split_media_to_audio_chunks_generator
from video_processor.transcriber import transcribe_single_audio_chunk, transcribe_local_with_choice
from dify_api import run_workflow_streaming

def main_process_generator(input_path: str, openai_api_key: str | None, dify_api_key: str, output_filename: str, query: str, transcription_provider: str, local_model_selection: str | None, output_chinese_format: str):
    output_dir = "output_chunks"
    final_notes_save_path = f"{output_filename}.md"
    intermediate_dir = "中间文件"
    os.makedirs(intermediate_dir, exist_ok=True)
    
    video_exts = {'.mp4', '.mov', '.mpeg', '.webm'}
    audio_exts = {'.mp3', '.m4a', '.wav', '.amr', '.mpga'}
    text_exts = {'.txt', '.md', '.mdx', '.markdown', '.pdf', '.html', '.xlsx', '.xls', '.doc', '.docx', '.csv', '.eml', '.msg', '.pptx', '.ppt', '.xml', '.epub'}

    file_ext = os.path.splitext(input_path)[1].lower()
    current_progress = 0
    full_transcript = ""

    def run_dify_and_yield_results():
        final_llm_output_chunks = []
        final_outputs = None

        dify_generator = run_workflow_streaming(
            input_text=full_transcript,
            query=query,
            user="streamlit_user",
            dify_api_key=dify_api_key
        )
        
        for event_type, data in dify_generator:
            if event_type == "text_chunk":
                final_llm_output_chunks.append(data)
                yield "llm_chunk", data
            
            elif event_type == "classification_result":
                category_map = {
                    "NOTES_STEM": "这是一个理工科 (STEM) 领域的笔记",
                    "NOTES_HASS": "这是一个⼈文社科 (HASS) 领域的笔记",
                }
                friendly_text = category_map.get(data, f"无法识别笔记领域，将使用默认模板。识别码: {data}")
                yield "display_classification", friendly_text
                
            elif event_type == "error":
                user_friendly_error = f"**笔记生成失败**\n\n看起来在与 Dify 服务通信时遇到了问题。这通常与 API Key 或网络有关。\n\n**原始错误信息:**\n`{data}`"
                yield "persistent_error", 0, user_friendly_error
                return

            elif event_type == "node_started":
                yield "progress_text", f"Dify 节点 '{data}' 已开始..."

            elif event_type == "workflow_finished":
                final_outputs = data
                break
        
        final_text_from_chunks = "".join(final_llm_output_chunks)
        final_output_value = final_outputs.get('final_output', '').strip() if final_outputs else ""

        if final_output_value == 'INJECTION_DETECTED':
            error_message = "**安全警告：检测到指令注入攻击**\n\n您的输入中可能包含试图操控系统行为的指令。为安全起见，处理已终止。"
            yield "persistent_error", 0, error_message
            return

        if final_output_value == 'SENSITIVE_CONTENT_DETECTED':
            error_message = "**内容警告：检测到不当敏感内容**\n\n您的输入中可能包含不适宜的词汇。为遵守社区准则，处理已终止。"
            yield "persistent_error", 0, error_message
            return
        
        if final_output_value == query:
            error_message = ""
            if query == "Notes":
                error_message = "**笔记生成失败**\n\n无法自动识别笔记的领域 (例如理工科/人文社科)。工作流已终止，因为它无法选择合适的笔记模板。"
            else:
                error_message = f"**无效的操作类型**\n\n请求的操作 '{query}' 不是一个有效的选项 ('Notes', 'Q&A', 'Quiz')。工作流已终止。"
            yield "persistent_error", 0, error_message
            return
        
        final_text = final_text_from_chunks
        
        if "</think>" in final_text:
            final_text = final_text.split("</think>")[-1].strip()

        if not final_text:
            yield "persistent_error", 0, "**笔记生成失败**\n\nDify 工作流在多次尝试后，未返回任何有效内容。请检查您的 Dify 工作流配置以及输入文本是否过长或格式异常。"
            return

        try:
            with open(final_notes_save_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            yield "save_path", final_notes_save_path
        except IOError as e:
            user_friendly_error = f"**保存最终笔记文件失败**\n\n无法将生成的笔记写入本地文件。\n\n**可能原因:**\n- 程序没有在当前目录创建文件的权限。\n- 磁盘空间不足。\n\n**原始错误信息:**\n`{e}`"
            yield "persistent_error", 0, user_friendly_error
            return

    if file_ext in text_exts:
        total_steps = 2
        yield "progress", 0 / total_steps, "步骤 1/2: 正在读取文本文档..."
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                full_transcript = f.read()
        except Exception as e:
            user_friendly_error = f"**读取文件失败**\n\n无法读取您上传的文本文档 '{os.path.basename(input_path)}'。\n\n**可能原因:**\n- 文件已损坏或编码格式不是 UTF-8。\n- 程序没有读取该文件的权限。\n\n**原始错误信息:**\n`{e}`"
            yield "persistent_error", 0, user_friendly_error
            return
        
        current_progress += 1
        yield "progress", current_progress / total_steps, "步骤 2/2: 正在提交给 Dify 工作流 (流式传输)..."
        
        final_path = None
        dify_gen = run_dify_and_yield_results()
        for event_type, value, *rest in dify_gen:
            if event_type == "persistent_error":
                yield event_type, value, rest[0]
                return
            elif event_type == "display_classification":
                yield event_type, value
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
                user_friendly_error = f"**媒体文件切分失败**\n\n无法处理您上传的媒体文件。这通常与 **FFmpeg** 配置或文件本身有关。\n\n**请检查:**\n1. **FFmpeg 是否已正确安装**: 确保 FFmpeg 已安装并在系统的环境变量 `PATH` 中。\n2. **文件是否完好**: 确认您的文件 `{os.path.basename(input_path)}` 没有损坏且格式受支持。\n\n**原始错误信息:**\n`{val1}`"
                yield "persistent_error", 0, user_friendly_error
                return
        
        if not audio_chunks:
            yield "persistent_error", 0, f"**{step_name}切分失败**\n\n未能从您的文件中提取出任何音频块。请确保文件时长不为零，且已正确安装 FFmpeg。"
            return
        
        yield "sub_progress", 1.0, f"✅ {step_name}切分全部完成！"
        current_progress += 1
        yield "progress", current_progress / total_steps, f"✅ {step_name}切分完成，准备开始转录..."

        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在并行转录 {len(audio_chunks)} 个音频块..."
        all_transcripts = [None] * len(audio_chunks)
        num_transcribed = 0

        if transcription_provider == 'openai_api':
            transcribe_func = transcribe_single_audio_chunk
            max_workers = 10
            tasks_args_list = [(chunk, openai_api_key, output_chinese_format) for chunk in audio_chunks]
        else:
            transcribe_func = transcribe_local_with_choice
            max_workers = 1
            tasks_args_list = [(chunk, local_model_selection, output_chinese_format) for chunk in audio_chunks]

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_index = {
                    executor.submit(transcribe_func, *args): i
                    for i, args in enumerate(tasks_args_list)
                }
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    result = future.result() 
                    if result is not None:
                        all_transcripts[index] = result
                    else:
                        raise Exception(f"转录任务未返回有效文本 (块索引: {index})。")
                    
                    num_transcribed += 1
                    yield "sub_progress", num_transcribed / len(audio_chunks), f"正在转录... ({num_transcribed}/{len(audio_chunks)})"

        except AuthenticationError as e:
             user_friendly_error = f"**OpenAI API 认证失败**\n\n您的 OpenAI API Key 无效。请在左侧边栏重新输入正确的密钥。\n\n**常见原因:**\n- 密钥拼写错误。\n- 密钥已过期或被禁用。\n- 账户余额不足。\n\n**原始错误信息:**\n`{e}`"
             yield "persistent_error", 0, user_friendly_error
             return
        except Exception as e:
            mode_text = "OpenAI Whisper 服务" if transcription_provider == 'openai_api' else f"本地模型 ({local_model_selection})"
            user_friendly_error = f"**音频转录失败**\n\n在使用 {mode_text} 进行语音转文字时发生无法恢复的错误。\n\n**可能原因:**\n1. (API模式) **OpenAI 服务中断**\n2. (API模式) **网络连接问题**\n3. (本地模式) **模型库或模型文件问题**\n4. **音频数据已损坏**\n\n**原始错误信息:**\n`{e}`"
            yield "persistent_error", 0, user_friendly_error
            return
        
        if any(t is None for t in all_transcripts):
            yield "persistent_error", 0, "**音频转录不完整**\n\n部分音频块在多次尝试后仍然转录失败。为确保笔记的完整性，处理已中止。"
            return

        yield "sub_progress", 1.0, "✅ 音频转录全部完成！"
        current_progress += 1
        yield "progress", current_progress / total_steps, "所有音频块转录完成！"
        
        step_name_after_transcription = "汇总文字稿并保存..." if is_video else "保存文字稿..."
        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在{step_name_after_transcription}"
        
        full_transcript = "\n\n".join(filter(None, all_transcripts))
        
        transcript_save_path = os.path.join(intermediate_dir, "source_transcript.txt")
        try:
            with open(transcript_save_path, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
        except IOError as e:
            yield "error", 0, f"无法保存文字稿文件: {e}"

        current_progress += 1
        yield "progress", current_progress / total_steps, "文字稿保存完成。"
            
        yield "progress", current_progress / total_steps, f"步骤 {current_progress + 1}/{total_steps}: 正在提交给 Dify 工作流 (流式传输)..."

        final_path = None
        dify_gen = run_dify_and_yield_results()
        for event_type, value, *rest in dify_gen:
            if event_type == "persistent_error":
                yield event_type, value, rest[0]
                return
            elif event_type == "display_classification":
                yield event_type, value
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
        user_friendly_error = f"**不支持的文件类型**\n\n您上传的文件类型 (`{file_ext}`) 当前不受支持。请参照上传框下的提示，上传指定格式的视频、音频或文本文档。"
        yield "error", 0, user_friendly_error
        return
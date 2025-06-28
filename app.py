# app.py
import streamlit as st
import os
import shutil
from main import main_process_generator
from config import DIFY_API_KEY 

st.set_page_config(page_title="智能笔记 Agent", layout="wide")
st.title("👨‍💻 智能内容生成 Agent")
st.markdown("上传您的视频、音频或文本文档，即可自动生成结构化笔记、Q&A 或测验。")

with st.sidebar:
    st.header("⚙️ 参数配置")
    
    with st.expander("本地模型加载说明", expanded=False):
        st.info(
            """
            - **首次加载慢**: 当您第一次选择某个本地模型时，程序需要将其从硬盘加载到内存/显存，此过程可能需要一些时间。
            - **后续使用快**: 一旦加载成功，模型会驻留在内存中。在本次会话中再次使用该模型，将无需等待加载。
            - **模型存放位置**: 所有本地模型都应放置在项目根目录下的 “大模型” 文件夹中，程序会自动从此路径加载。
            """
        )

    transcription_provider = st.selectbox(
        "请选择语音转文字方式:",
        ("OpenAI API (速度快)", "本地处理 (免费但较慢)"),
        index=0,
        help=(
            "**OpenAI API**: 速度快，结果稳定，但需要您自己的 API Key 且会产生费用。"
            "**本地处理**: 完全免费，但速度显著慢于API。请确保已按说明配置好“大模型”文件夹。"
        )
    )
    provider_key = "local" if transcription_provider == "本地处理 (免费但较慢)" else "openai_api"

    local_model_selection = None
    if provider_key == "local":
        model_options = {
            "Faster-Whisper (Large-v3, 推荐)": ("faster-whisper-large-v3", "速度与质量的最佳平衡。"),
            "Whisper - Large-v3 (官方)": ("whisper-large-v3", "官方实现，提供最高的准确度，但在没有顶级GPU的情况下速度极慢。"),
            "Whisper - Medium (官方)": ("whisper-medium", "官方实现，准确度较好，速度慢于 Faster-Whisper。"),
            "Whisper - Base (官方)": ("whisper-base", "官方实现，速度最快，占用资源最少，但准确度为基础水平。")
        }
        selected_model_name = st.selectbox(
            "请选择本地模型:", options=model_options.keys(), index=0,
            help="不同模型在速度、准确度和资源占用上有所不同。"
        )
        local_model_selection, help_text = model_options[selected_model_name]
        st.info(help_text)

    st.markdown("---")
    output_chinese_format = st.radio(
        "选择中文输出格式:",
        ("简体中文", "繁體中文"),
        index=0,
        horizontal=True,
        help="此选项仅在转录内容被识别为中文时生效。"
    )
    format_key = "simplified" if output_chinese_format == "简体中文" else "traditional"

    openai_api_key_input = st.text_input(
        "请输入您的 OpenAI API Key", type="password", help="您的密钥将仅用于视频/音频的语音转录，不会被保存。",
        disabled=(provider_key == "local")
    )
    openai_api_key = openai_api_key_input if provider_key == "openai_api" else None
    output_filename = st.text_input("请输入希望的笔记文件名 (无需后缀)", value="我的学习笔记")
    query_option = st.selectbox(
        "请选择生成内容类型:", ("Notes", "Q&A", "Quiz"), index=0,
        help="选择 'Notes' 生成结构化笔记, 'Q&A' 生成问答对, 'Quiz' 生成测验题。"
    )
    st.markdown("---")
    keep_temp_files = st.checkbox(
        "保留中间文件", value=False, help="勾选后将保留上传的临时文件、音频块和转写稿。"
    )
    st.info("请在上方配置好参数后，上传文件开始处理。")

video_exts = {'mp4', 'mov','mpeg','webm'}
audio_exts = {'mp3','m4a','wav','amr','mpga'}
doc_exts = {'txt','md','mdx','markdown','pdf','html','xlsx','xls','doc','docx','csv','eml','msg','pptx','ppt','xml','epub'}
all_exts = list(video_exts | audio_exts | doc_exts)

with st.expander("查看所有支持的文件格式"):
    st.markdown(f"""
    - **视频文件**: `{', '.join(sorted(list(video_exts)))}`
    - **音频文件**: `{', '.join(sorted(list(audio_exts)))}`
    - **文档文件**: `{', '.join(sorted(list(doc_exts)))}`
    """)

uploaded_file = st.file_uploader("上传视频、音频或文档", type=all_exts)

if uploaded_file is not None:
    if st.button("开始生成", use_container_width=True, type="primary"):
        file_ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')
        is_media_file = file_ext in video_exts or file_ext in audio_exts
        if is_media_file and provider_key == "openai_api" and not openai_api_key:
            st.error("❌ 您选择了 OpenAI API 模式，请在左侧边栏输入您的 API Key。")
        else:
            st.markdown("---")
            st.subheader("处理进度")
            main_progress_bar = st.progress(0)
            main_progress_text = st.empty()
            sub_progress_bar = st.progress(0)
            sub_progress_text = st.empty()
            st.markdown("---")
            processing_headers = {
                "Notes": "正在生成笔记 (实时输出中...)",
                "Q&A": "正在进行 Q&A (实时输出中...)",
                "Quiz": "正在生成测验 (实时输出中...)"
            }
            st.subheader(processing_headers.get(query_option, "正在处理..."))
            st.info(f"当前生成模式: **{query_option}**")
            if provider_key == "local":
                 st.info(f"当前本地模型: **{local_model_selection}**")
            
            classification_display = st.empty()
            llm_output_container = st.empty()
            full_llm_response = ""
            final_result_path = None
            processing_has_failed = False
            temp_dir = "temp_uploads"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            generator = main_process_generator(
                input_path=temp_file_path, 
                openai_api_key=openai_api_key, 
                dify_api_key=DIFY_API_KEY, 
                output_filename=output_filename, 
                query=query_option,
                transcription_provider=provider_key,
                local_model_selection=local_model_selection,
                output_chinese_format=format_key
            )
            for event_type, value, *rest in generator:
                text = rest[0] if rest else ""
                if event_type == "progress":
                    main_progress_bar.progress(float(value))
                    main_progress_text.info(text)
                elif event_type == "sub_progress":
                    sub_progress_bar.progress(float(value))
                    sub_progress_text.text(text)
                elif event_type == "display_classification":
                    classification_display.success(f"✅ **笔记分类**: {value}")
                elif event_type == "llm_chunk":
                    full_llm_response += value
                    llm_output_container.markdown(full_llm_response + " ▌")
                elif event_type == "persistent_error":
                    st.error(f"处理失败: {text}")
                    main_progress_text.error("一个关键步骤在多次重试后仍然失败，已停止处理。")
                    llm_output_container.error(f"**错误详情:**\n\n{text}")
                    if st.button("🔄 重新开始"):
                        st.experimental_rerun()
                    processing_has_failed = True
                    break
                elif event_type == "error":
                    st.error(text)
                    llm_output_container.error(text)
                    processing_has_failed = True
                    break
                elif event_type == "done":
                    main_progress_bar.progress(1.0)
                    sub_progress_bar.empty()
                    sub_progress_text.empty()
                    llm_output_container.markdown(full_llm_response)
                    st.success(text)
                    final_result_path = value
            
            if final_result_path and os.path.exists(final_result_path) and not processing_has_failed:
                st.download_button(
                    label=f"下载结果 ({os.path.basename(final_result_path)})",
                    data=full_llm_response,
                    file_name=os.path.basename(final_result_path),
                    mime="text/markdown",
                    use_container_width=True
                )
            
            if not keep_temp_files:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                transcript_dir = "中间文件"
                if os.path.exists(transcript_dir):
                    shutil.rmtree(transcript_dir, ignore_errors=True)
                
                chunk_dir = "output_chunks"
                if os.path.exists(chunk_dir):
                    shutil.rmtree(chunk_dir, ignore_errors=True)
            else:
                st.info("已根据您的设置，保留了所有中间文件。")
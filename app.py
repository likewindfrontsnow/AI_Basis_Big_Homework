# app.py
import streamlit as st
import os
from main import main_process_generator
from config import DIFY_API_KEY # Dify Key 仍然从配置中读取

# --- Streamlit 界面布局 ---
st.set_page_config(page_title="智能笔记 Agent", layout="wide")
st.title("👨‍💻 智能笔记生成 Agent")
st.markdown("上传您的视频、音频或文本文档，即可自动生成结构化笔记。")

# --- 用户输入区域 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    openai_api_key = st.text_input("请输入您的 OpenAI API Key", type="password", help="您的密钥将仅用于本次处理，不会被保存。")
    output_filename = st.text_input("请输入希望的笔记文件名 (无需后缀)", value="我的学习笔记")

    st.info("请在上方配置好参数后，上传文件开始处理。")

# --- 文件上传与主逻辑 ---
uploaded_file = st.file_uploader(
    "上传视频 (mp4, mov, mpeg, webm)、音频 (mp3, m4a, wav, amr, mpga) 或文档 (txt, md, mdx, markdown, pdf, html, xlsx, xls, doc, docx, csv, eml, msg, pptx, ppt, xml, epub)", 
    type=['mp4', 'mov','mpeg','webm','mp3','m4a','wav','amr','mpga','txt','md','mdx','markdown','pdf','html','xlsx','xls','doc','docx','csv','eml','msg','pptx','ppt','xml','epub']
)

if uploaded_file is not None:
    if not openai_api_key:
        st.warning("请输入您的 OpenAI API Key 以继续。")
    else:
        if st.button("开始生成笔记", use_container_width=True, type="primary"):
            temp_dir = "temp_uploads"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.markdown("---")
            st.subheader("处理进度")
            
            main_progress_bar = st.progress(0)
            main_progress_text = st.empty()
            sub_progress_bar = st.progress(0)
            sub_progress_text = st.empty()

            st.markdown("---")
            st.subheader("生成笔记 (实时输出中...)")
            llm_output_container = st.empty()
            full_llm_response = ""
            
            final_result_path = None
            processing_has_failed = False # Flag to stop processing

            # --- 循环调用生成器，实时更新UI ---
            generator = main_process_generator(temp_file_path, openai_api_key, DIFY_API_KEY, output_filename)
            for event_type, value, *rest in generator:
                text = rest[0] if rest else ""

                if event_type == "progress":
                    main_progress_bar.progress(float(value))
                    main_progress_text.info(text)
                elif event_type == "sub_progress":
                    sub_progress_bar.progress(float(value))
                    sub_progress_text.text(text)
                elif event_type == "llm_chunk":
                    full_llm_response += value
                    llm_output_container.markdown(full_llm_response + " ▌")
                
                # --- 新增：处理不可恢复的错误 ---
                elif event_type == "persistent_error":
                    st.error(f"处理失败: {text}")
                    main_progress_text.error("一个关键步骤在多次重试后仍然失败，已停止处理。")
                    llm_output_container.error(f"**错误详情:**\n\n{text}")
                    if st.button("🔄 重新开始"):
                        st.experimental_rerun()
                    processing_has_failed = True
                    break # 停止处理事件
                
                # --- 原有错误处理，用于非重试的直接错误 ---
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
                    final_result_path = value # 保存最终文件路径
            
            # --- 显示最终结果和下载按钮 ---
            if final_result_path and os.path.exists(final_result_path) and not processing_has_failed:
                st.download_button(
                    label=f"下载笔记 ({os.path.basename(final_result_path)})",
                    data=full_llm_response,
                    file_name=os.path.basename(final_result_path),
                    mime="text/markdown",
                    use_container_width=True
                )
            
            # 清理临时文件
            try:
                os.remove(temp_file_path)
            except OSError as e:
                st.warning(f"无法删除临时文件: {e}")
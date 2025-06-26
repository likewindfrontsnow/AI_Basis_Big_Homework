# app.py
import streamlit as st
import os
from main import main_process_generator
from config import DIFY_API_KEY # Dify Key 仍然从配置中读取

# --- Streamlit 界面布局 ---
st.set_page_config(page_title="智能笔记 Agent", layout="wide")
st.title("👨‍💻 视频课程智能笔记 Agent")
st.markdown("上传您的视频课程，输入OpenAI API密钥，即可自动生成结构化笔记。")

# --- 用户输入区域 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 1. 用户输入 OpenAI API Key
    openai_api_key = st.text_input("请输入您的 OpenAI API Key", type="password", help="您的密钥将仅用于本次处理，不会被保存。")
    
    # 2. 用户自定义输出文件名
    output_filename = st.text_input("请输入希望的笔记文件名 (无需后缀)", value="我的学习笔记")

    st.info("请在上方配置好参数后，上传视频文件开始处理。")

# --- 文件上传与主逻辑 ---
uploaded_file = st.file_uploader(
    "上传一个视频文件 (mp4, mov, avi, mkv)", 
    type=['mp4', 'mov', 'avi', 'mkv']
)

if uploaded_file is not None:
    # 检查用户是否已输入API Key
    if not openai_api_key:
        st.warning("请输入您的 OpenAI API Key 以继续。")
    else:
        # 显示开始按钮
        if st.button("开始生成笔记", use_container_width=True, type="primary"):
            # 保存上传的文件到临时位置
            temp_dir = "temp_uploads"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_video_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.markdown("---")
            st.subheader("处理进度")
            
            # 创建用于显示进度的元素
            main_progress_bar = st.progress(0)
            main_progress_text = st.empty()
            sub_progress_bar = st.progress(0)
            sub_progress_text = st.empty()

            final_result_path = None
            
            # --- 循环调用生成器，实时更新UI ---
            for event_type, value, text in main_process_generator(temp_video_path, openai_api_key, DIFY_API_KEY, output_filename):
                if event_type == "progress":
                    main_progress_bar.progress(value)
                    main_progress_text.info(text)
                elif event_type == "sub_progress":
                    sub_progress_bar.progress(value)
                    sub_progress_text.text(text)
                elif event_type == "error":
                    st.error(text)
                    break
                elif event_type == "done":
                    main_progress_bar.progress(1.0) # 确保主进度条满
                    sub_progress_bar.empty() # 清空子进度条
                    sub_progress_text.empty()
                    st.success(text)
                    final_result_path = value # 保存最终文件路径
            
            # --- 显示最终结果 ---
            if final_result_path and os.path.exists(final_result_path):
                st.markdown("---")
                st.subheader("生成的笔记内容预览")
                with open(final_result_path, 'r', encoding='utf-8') as f:
                    final_notes = f.read()
                st.markdown(final_notes)
                
                st.download_button(
                    label=f"下载笔记 ({os.path.basename(final_result_path)})",
                    data=final_notes,
                    file_name=os.path.basename(final_result_path),
                    mime="text/markdown",
                    use_container_width=True
                )
            
            # 清理临时文件
            os.remove(temp_video_path)
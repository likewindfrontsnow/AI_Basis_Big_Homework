# app.py
import streamlit as st
import os
import time
from main import generate_transcript_from_video, process_transcript_with_dify
from config import OUTPUT_CHUNK_FOLDER, FINAL_TRANSCRIPT_FILE, LOCAL_SAVE_PATH

# 设置页面标题和侧边栏
st.set_page_config(page_title="智能笔记 Agent", layout="wide")
st.title("👨‍💻 大学生智能笔记 Agent")
st.markdown("上传您的视频课程，自动生成结构化笔记。")

# --- 文件上传 ---
uploaded_file = st.file_uploader(
    "选择一个视频文件 (mp4, mov, avi)", 
    type=['mp4', 'mov', 'avi', 'mkv']
)

if uploaded_file is not None:
    # 保存上传的文件到临时位置
    temp_dir = "temp_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    temp_video_path = os.path.join(temp_dir, uploaded_file.name)
    with open(temp_video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.video(temp_video_path)

    # --- 开始处理按钮 ---
    if st.button("开始生成笔记", use_container_width=True):
        with st.spinner("任务正在进行中，请稍候... 这可能需要几分钟时间。"):
            st.info("步骤 1: 正在切分视频为音频块...")
            # 注意：Streamlit 无法像桌面GUI一样实时打印日志
            # 我们只能在每个主要步骤完成后显示状态更新
            full_transcript = generate_transcript_from_video(
                video_path=temp_video_path,
                output_dir=OUTPUT_CHUNK_FOLDER,
                transcript_save_path=FINAL_TRANSCRIPT_FILE
            )

            if full_transcript:
                st.success("步骤 1 & 2 & 3: 视频切分和文字转录全部完成！")
                st.info("步骤 4: 正在提交给 Dify 工作流进行最终处理...")

                process_transcript_with_dify(full_transcript)

                st.success("🎉 恭喜！智能笔记已生成！")

                # 显示并提供下载最终的笔记文件
                try:
                    with open(LOCAL_SAVE_PATH, 'r', encoding='utf-8') as f:
                        final_notes = f.read()
                    st.markdown("---")
                    st.subheader("生成的笔记内容预览")
                    st.markdown(final_notes)

                    st.download_button(
                        label="下载笔记 (result.md)",
                        data=final_notes,
                        file_name="result.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                except FileNotFoundError:
                    st.error("无法找到生成的笔记文件。")

            else:
                st.error("处理失败，未能从视频中生成文字稿。")

        # 清理临时上传的文件
        os.remove(temp_video_path)
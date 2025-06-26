# keyframe_extractor.py (Final version for custom video)
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from __future__ import annotations

import io
import os
import logging
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def dependencies_required(*deps):
    """
    Decorator to ensure required libraries are installed.
    A user-friendly error message will be raised if a dependency is missing.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            missing_deps = []
            for dep in deps:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)
            
            if missing_deps:
                install_commands = {
                    "cv2": "opencv-python",
                    "scenedetect": "scenedetect",
                    "numpy": "numpy",
                    "PIL": "Pillow"
                }
                install_names = [install_commands.get(d, d) for d in missing_deps]
                raise ImportError(
                    f"Missing required dependencies: {', '.join(missing_deps)}. "
                    f"Please install them using 'pip install {' '.join(install_names)}'."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _capture_screenshot(video_path: str, time_sec: float) -> Image.Image:
    r"""Captures a screenshot from a video at a specific time."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        raise ValueError("Video FPS is 0, cannot seek in video.")

    frame_number = int(fps * time_sec)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    success, frame = cap.read()
    cap.release()
    
    if not success:
        raise ValueError(
            f"Failed to capture frame at {time_sec:.2f} seconds."
        )
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(frame_rgb)


def _normalize_frames(
    frames: List[Image.Image], target_width: int = 512
) -> List[Image.Image]:
    r"""Normalize the size of extracted frames."""
    normalized_frames: List[Image.Image] = []

    for frame in frames:
        width, height = frame.size
        if width == 0 or height == 0:
            logger.warning("Skipping frame with zero dimension.")
            continue

        aspect_ratio = width / height
        new_height = int(target_width / aspect_ratio)

        resized_frame = frame.resize(
            (target_width, new_height), Image.Resampling.LANCZOS
        )

        if resized_frame.mode != 'RGB':
            resized_frame = resized_frame.convert('RGB')

        with io.BytesIO() as buffer:
            resized_frame.save(buffer, format='JPEG')
            buffer.seek(0)
            formatted_frame = Image.open(buffer)
            formatted_frame.load()

        normalized_frames.append(formatted_frame)

    return normalized_frames

@dependencies_required("cv2", "numpy", "scenedetect")
def extract_keyframes(
    video_path: str,
    frame_interval: float = 10.0,
    max_frames: int = 20,
    output_dir: str | None = None,
) -> List[Image.Image]:
    r"""Extract keyframes from a video based on scene changes and
    regular intervals."""
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    cap = cv2.VideoCapture(video_path)
    total_frames_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames_count / fps if fps > 0 else 0
    cap.release()

    if duration <= 0:
        raise ValueError("Cannot process video with zero duration or invalid FPS.")

    num_frames = max(int(duration / frame_interval), 1)
    if num_frames > max_frames:
        frame_interval = duration / max_frames
        num_frames = max_frames
    
    logger.info(
        f"Video duration: {duration:.2f}s. Aiming to extract up to {num_frames} "
        f"frames with an interval of ~{frame_interval:.2f}s."
    )

    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)
    scenes = scene_manager.get_scene_list()
    
    keyframes: List[Image.Image] = []
    
    if scenes:
        logger.info(f"Detected {len(scenes)} scenes.")
        
        if len(scenes) > num_frames:
            scene_indices = np.linspace(0, len(scenes) - 1, num_frames, dtype=int)
            selected_scenes = [scenes[i] for i in scene_indices]
        else:
            selected_scenes = scenes

        for scene in selected_scenes:
            try:
                start_time_sec = scene[0].get_seconds()
                frame = _capture_screenshot(video_path, start_time_sec)
                keyframes.append(frame)
            except Exception as e:
                logger.warning(
                    f"Could not capture frame at scene start {scene[0].get_seconds():.2f}s: {e}"
                )

    if len(keyframes) < num_frames:
        logger.info(
            f"Supplementing {len(keyframes)} scene-based frames with "
            f"frames from regular intervals."
        )
        
        existing_times = [s[0].get_seconds() for s in scenes] if scenes else []
        time_threshold = 1.0
        
        for i in range(num_frames):
            if len(keyframes) >= num_frames:
                break
                
            time_sec = i * frame_interval
            
            is_too_close = any(abs(existing_time - time_sec) < time_threshold for existing_time in existing_times)
            if not is_too_close:
                try:
                    frame = _capture_screenshot(video_path, time_sec)
                    keyframes.append(frame)
                    existing_times.append(time_sec)
                except Exception as e:
                    logger.warning(f"Could not capture frame at {time_sec:.2f}s: {e}")

    if not keyframes:
        raise ValueError(f"Failed to extract any keyframes from video: {video_path}")

    normalized_keyframes = _normalize_frames(keyframes)
    logger.info(f"Extracted and normalized {len(normalized_keyframes)} keyframes.")

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        for i, frame in enumerate(normalized_keyframes):
            frame.save(os.path.join(output_dir, f"keyframe_{i+1:03d}.jpg"))
        logger.info(f"Saved keyframes to '{output_dir}'.")

    return normalized_keyframes


if __name__ == '__main__':
    # ================== USAGE EXAMPLE WITH YOUR OWN VIDEO ==================
    
    # 1. 替换为您自己的视频文件路径
    video_file_path = "test.mp4" 

    # 2. 设置保存关键帧的文件夹名称（将保存在脚本当前目录下）
    frames_output_path = "keyframes"

    # --- 开始处理 ---
    try:
        # 检查视频文件是否存在
        if not os.path.exists(video_file_path):
            raise FileNotFoundError(
                f"错误：找不到视频文件，请检查路径是否正确: {video_file_path}"
            )

        # 调用核心函数来提取关键帧
        extracted_frames = extract_keyframes(
            video_path=video_file_path,
            frame_interval=5,      # 每隔5秒提取一帧
            max_frames=20,         # 最多提取20帧
            output_dir=frames_output_path
        )
        
        print(f"\n成功提取了 {len(extracted_frames)} 个关键帧。")
        # 显示清晰的绝对路径
        absolute_output_path = os.path.abspath(frames_output_path)
        print(f"所有关键帧已保存至: {absolute_output_path}")

    except (ImportError, FileNotFoundError, ValueError) as e:
        logger.error(f"处理过程中发生错误: {e}")
    except Exception as e:
        logger.error(f"发生未知错误: {e}")
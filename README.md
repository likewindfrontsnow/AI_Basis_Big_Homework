# 👨‍💻 智能内容生成 Agent

这是一个功能强大的内容处理工具，旨在帮助学生和内容创作者将视频、音频或文字材料，通过大语言模型（LLM）快速转化为结构化的学习笔记、Q&A 对或自测题。

本应用整合了媒体处理、语音转文字（ASR）和 LLM 工作流，提供从原始文件到最终成品的端到端自动化解决方案。

---

# 1. 🌟 主要功能

- **多格式文件支持**: 无缝处理多种主流文件格式：
  - **视频**: `.mp4`, `.mov`, `.mpeg`, `.webm`
  - **音频**: `.mp3`, `.m4a`, `.wav`, `.amr`, `.mpga`
  - **文档**: `.txt`, `.md`, `.pdf`, `.docx` 等多种文本文档。
- **灵活的语音转文字 (ASR) 选项**:
  - **OpenAI API**: 利用 `whisper-1` 模型进行快速、高质量的在线转录（需要 API Key）。
  - **本地处理**: 完全免费、离线的转录方案，支持 `faster-whisper` 和官方 `whisper` 模型，保护数据隐私。
- **多样化内容生成**:
  - **智能笔记 (Notes)**: 自动识别内容领域（理工/人文社科），并应用不同的模板生成结构化、专业化的笔记。
  - **问答生成 (Q&A)**: 基于原文内容生成相关的问答对。
  - **测验生成 (Quiz)**: 根据核心概念自动创建多项选择题，用于学习效果检验。
- **Dify 工作流驱动**: 核心的 LLM 逻辑由 [Dify.AI](https://dify.ai/) 平台的工作流驱动，实现了内容审查、分类、生成和格式检查等复杂任务。
- **实时进度与结果展示**: 使用 Streamlit 构建了友好的用户界面，可以实时展示处理进度、LLM 的流式输出结果。
- **高度可配置**: 用户可在界面上自由选择转录模型、输出语言格式（简/繁体）、配置 API 密钥等。

---

# 2. 📖 技术栈

- **前端框架**: Streamlit
- **媒体处理**: FFmpeg
- **语音识别 (ASR)**: OpenAI Whisper (API) / Faster-Whisper (本地) / OpenAI-Whisper (本地)
- **LLM 工作流**: Dify.AI
- **核心语言**: Python

---

# 3. ⚙️ 环境准备与安装

在开始之前，请确保您的系统已安装以下必备软件：

1.  **Python**: 建议使用 `3.9` 或更高版本。
2.  **Git**: 用于克隆本项目仓库。
3.  **FFmpeg**: **[必需]** 用于处理所有视频和音频文件。**这是最关键的依赖项，请务必参照下面的教程正确安装。**
4.  **支持CUDA的PyTorch**：用于GPU加速处理本地whisper模型语音转文字

## 3.1 ffmpeg 安装教程

`ffmpeg` 和 `ffprobe` 是本应用处理媒体文件的核心工具。如果它们没有被正确安装并添加到系统的环境变量中，程序将无法切分音频块，导致功能失败。

### ✅ 验证安装

在安装前后，您都可以通过在终端（Windows 的 `cmd` 或 `PowerShell`，macOS/Linux 的 `Terminal`）中运行以下命令来检查 FFmpeg 是否可用：

```bash
ffmpeg -version
ffprobe -version
```

如果命令成功执行并显示版本信息，则说明安装成功。如果提示 "command not found" (或“不是内部或外部命令”)，则说明安装未成功或未配置环境变量。

### 🪟 Windows 系统

#### 方法一：使用 Chocolatey 包管理器 (推荐)

打开 PowerShell (以管理员身份)。

安装 Chocolatey（如果尚未安装），请访问 Chocolatey 官网 获取最新的安装命令。

执行安装命令：

choco install ffmpeg

安装完成后，关闭并重新打开一个终端窗口，运行验证命令。

#### 方法二：手动下载并配置环境变量

访问 FFmpeg 官方下载页面 (推荐 gyan.dev 的构建版本)。

下载 ffmpeg-release-full.7z 压缩包。

解压下载的文件到一个稳定的位置，例如 C:\ffmpeg。

配置环境变量:

右键点击“此电脑” -> “属性” -> “高级系统设置” -> “环境变量”。

在“系统变量”区域找到并选中 Path，然后点击“编辑”。

点击“新建”，然后将你的 FFmpeg bin 文件夹的完整路径（例如 C:\ffmpeg\bin）粘贴进去。

点击“确定”保存所有打开的窗口。

关闭并重新打开一个终端窗口，运行验证命令。

### macOS 系统

#### 使用 Homebrew 包管理器 (推荐)

打开“终端” (Terminal) 应用。

安装 Homebrew（如果尚未安装），请访问 Homebrew 官网 复制安装命令。

执行安装命令：

brew install ffmpeg

Homebrew 会自动处理环境变量。安装完成后，运行验证命令。

### 🐧 Linux 系统 (Debian/Ubuntu)

使用 apt 包管理器

打开终端。

执行安装命令：

sudo apt update && sudo apt install ffmpeg

安装完成后，运行验证命令。

## 3.2 支持CUDA的PyTorch安装教程

### **步骤 1: 检查您的 NVIDIA CUDA 版本**

首先，您需要知道您的 NVIDIA 驱动程序支持的最高 CUDA 版本。

1.  打开您的命令行工具（Windows 用户请使用 CMD 或 PowerShell，macOS/Linux 用户请使用终端）。
2.  输入以下命令并按回车：

    ```bash
    nvidia-smi
    ```

3.  在弹出的信息表的右上角，找到 `CUDA Version`。记下这个版本号，例如 `12.1`、`12.4` 等。

### **步骤 2: (可选但推荐) 卸载旧版本**

为了避免潜在的版本冲突，建议先完全卸载环境中可能存在的旧版 PyTorch。

```bash
# 多次执行此命令，直到系统提示“not installed”
pip uninstall torch torchvision torchaudio
```

### **步骤 3: 从 PyTorch 官网获取安装命令**

这是最关键的一步，请勿直接使用网络上搜索到的旧命令。

1.  访问 PyTorch 官方网站的安装页面： [https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/)

2.  在页面的 “INSTALL PYTORCH” 工具中，根据您的系统配置进行选择：
    * **PyTorch Build**: 选择 `Stable` (稳定版)。
    * **Your OS**: 选择您的操作系统 (Windows, Linux, Mac)。
    * **Package**: 选择 `Pip`。
    * **Language**: 选择 `Python`。
    * **Compute Platform**: **选择一个等于或低于**您在步骤 1 中查到的 CUDA 版本。通常，选择官网上提供的最新 CUDA 选项即可（例如，如果您的版本是 `12.4`，选择官网的 `CUDA 12.1` 是完全正确的，因为它向后兼容）。

3.  网站会自动生成一行安装命令。请**完整复制**这行命令。

### **步骤 4: 执行安装**

将上一步复制的完整命令粘贴到您的命令行中，然后按回车执行。

一个为 CUDA 12.1 生成的典型命令如下所示（**请以您从官网复制的命令为准！**）：
```bash
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
```
安装过程可能需要一些时间，因为它会下载几个较大的文件。

### **步骤 5: 验证安装**

安装完成后，打开 Python 解释器来验证 GPU 是否被成功识别。

1.  在命令行输入 `python` 并回车。
2.  逐行输入以下代码：
    ```python
    import torch

    # 检查 CUDA 是否可用
    is_available = torch.cuda.is_available()
    print(f"CUDA support is available: {is_available}")

    if is_available:
        # 获取 GPU 数量
        device_count = torch.cuda.device_count()
        print(f"Number of GPUs available: {device_count}")
        
        # 获取当前 GPU 的名称
        current_device_name = torch.cuda.get_device_name(0)
        print(f"Current GPU name: {current_device_name}")
    ```

如果输出结果中 `CUDA support is available: True`，则恭喜您，已成功安装 GPU 版本的 PyTorch！

## 3.3 🚀 项目安装与配置

从https://github.com/likewindfrontsnow/AI_Basis_Big_Homework 下载.zip文件并解压，或者使用git clone命令

### 3.3.1 创建并激活虚拟环境（可选）

#### 不使用anaconda

##### Windows
```
python -m venv venv
.\venv\Scripts\activate
```

##### macOS/Linux
```
python -m venv venv
source venv/bin/activate
```

#### 使用anaconda

```
conda create -n venv(可以自定义虚拟环境的名字) python=3.11(可以自定义Python版本)
conda activate venv(替换成自定义的名字)
```

### 3.3.2 安装所有 Python 依赖包（必须）
```
pip install -r requirements.txt
```


# 4. 🏃‍♂️ 运行程序
确保所有依赖和配置都已就绪后，在项目根目录下运行以下命令：

```
streamlit run app.py
```

程序将启动一个本地 web 服务，并在您的浏览器中打开应用界面。

# 5. 💡 使用说明

打开应用: 浏览器会自动打开 http://localhost:8501。

## 5.1 配置参数 (左侧边栏):

### 5.1.1 选择转录方式: 

需要根据视频/录音生成笔记才需要选择转录方式

请根据您的需求选择使用 "OpenAI API" 或 "本地处理"。

如果选择 API 方式，请输入您的密钥。

如果选择本地处理，请从下拉列表中选择一个模型。模型在第一次加载时会安装到项目根目录文件夹"大模型"中，比较耗时，后续无需安装即可直接使用，速度快。

### 5.1.2 选择转录稿输出为简体中文/繁体中文: 

默认输出简体中文

### 5.1.3 设置输出文件名（无需加后缀）

默认文件名为"我的学习笔记"

### 5.1.4 选择生成内容类型:

选择 "Notes", "Q&A", 或 "Quiz"

### 5.2 上传文件

将您的视频、音频或文档拖拽到主界面的上传区域，或者点击选择文件

### 5.3 开始生成

点击 "开始生成" 按钮

界面下方会显示详细的处理步骤和进度条。

LLM 的输出内容会实时显示在文本框中。

处理完成后，会提供最终文件的下载按钮。

# 6. 📂 项目文件结构
```
.
├── output_chunks/         # (自动生成) 存放媒体文件切分后的音频块
├── 中间文件/              # (自动生成) 存放完整的转写稿等
├── temp_uploads/          # (自动生成) 存放上传的临时文件
├── 大模型/                # (手动创建) 存放本地 Whisper 模型
├── Agent for college students.yml # Dify 工作流的定义文件，供参考
├── app.py                 # Streamlit 应用主程序 (UI界面)
├── main.py                # 核心处理流程的编排器
├── dify_api.py            # 封装与 Dify API 交互的逻辑
├── splitter.py            # 使用 FFmpeg 切分媒体文件的模块
├── transcriber.py         # 封装不同语音转文字方案的模块
├── config.py              # 加载环境变量配置
├── utils.py               # 通用工具函数 (如重试装饰器)
├── requirements.txt       # Python 依赖列表
└── README.md              # 本说明文件
```
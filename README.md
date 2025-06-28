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

## 3.2 🚀 项目安装与配置

从https://github.com/likewindfrontsnow/AI_Basis_Big_Homework 下载.zip文件并解压，或者使用git clone命令

### 3.2.1 创建并激活虚拟环境（可选）

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

### 3.2.2 安装所有 Python 依赖包（必须）
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
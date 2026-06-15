# Flet Whisper · 字幕工作台

一个用 [Flet](https://flet.dev)(Python 写 Flutter)做的桌面应用:**粘贴视频链接下载,或选择本地音视频文件,自动用 Whisper 转录并生成 SRT 字幕**。字幕保存在源文件同级目录、与源文件同名。

后端按硬件自动选择并在界面顶部显示:

- **Apple Silicon**:MLX(Metal 加速)
- **NVIDIA GPU**:faster-whisper(CUDA,最快)或 PyTorch CUDA
- **其它**:CPU

界面采用 Swiss / 国际主义平面风格(黑白 + 瑞士红、无圆角无阴影)。

---

## 功能

- **粘贴链接下载** —— 基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp),支持 YouTube / B 站 / X 等上千站点,下载最佳画质 + 音轨并合并为 mp4
- **本地文件转录** —— 点击选择本地音视频文件
- **自动生成 SRT** —— 整句字幕,保存到源文件同级、同名(源文件 `视频.mp4` 生成 `视频.srt`)
- **跨平台 GPU 加速** —— MLX / CUDA / CPU 自动探测,顶部徽标显示当前后端
- **模型可选** —— tiny / base / small / medium / large-v3(默认 small)
- **下载即转录** —— 可勾选「下载完成后自动转录」,一步到位

---

## 环境要求

- **Python 3.14 或更高版本**
- **[uv](https://github.com/astral-sh/uv)**(推荐的包管理器)
- **[ffmpeg](https://ffmpeg.org/)**(下载合并、音视频解码必需)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: 从官网下载并加入 PATH

首次使用某个模型尺寸时,会自动从 Hugging Face 下载对应权重。

---

## 安装与运行

```bash
# 克隆
git clone https://github.com/iTZR1314/Flet-whisper.git
cd Flet-whisper

# 安装依赖(uv 会自动创建虚拟环境)
uv sync

# 运行
uv run main.py
```

### NVIDIA 用户(可选,获得最快速度)

默认依赖在非苹果平台会使用 stable-ts 的 PyTorch 后端(支持 CUDA)。如需更快的 **faster-whisper**(CTranslate2):

```bash
uv sync --extra cuda
```

代码会自动探测并优先使用 faster-whisper。请确保已安装匹配 CUDA 版本的 PyTorch 与 CTranslate2。

说明:`mlx-whisper` 依赖带有平台标记,**只在 Apple Silicon 上安装**,因此 Windows / Linux / NVIDIA 用户可以正常 `uv sync`。

---

## 使用方法

1. 运行后,顶部右侧徽标会显示当前**推理后端**(如 `MLX · Apple Metal`)。
2. **下载视频(可选)**
   - 粘贴视频链接,点「选择保存目录」选好位置,再点「下载」
   - 勾选「下载完成后自动转录字幕」可在下载后直接转录
3. **转录字幕**
   - 选择模型尺寸(越大越准、越慢)
   - 点击虚线框选择本地音视频文件
4. 转录完成后,SRT 字幕保存在**源文件同级目录、同名**,界面底部显示保存路径。

---

## 技术栈

| 部分 | 使用 |
|---|---|
| 界面 | Flet 0.85(Material 3) |
| 转录 | [stable-ts](https://github.com/jianfch/stable-ts) + Whisper(MLX / faster-whisper / PyTorch) |
| 下载 | yt-dlp |
| 媒体处理 | ffmpeg |

---

## 常见问题

- **转录报错找不到 ffmpeg**:按上文安装 ffmpeg 并确保在 PATH 中。
- **下载失败**:检查链接是否有效、网络是否可访问该站点;部分站点需要登录 cookie。
- **想要更准的字幕**:把模型尺寸切到 `medium` 或 `large-v3`(更慢、占用更高)。
- **拖拽文件到窗口没反应**:Flet 桌面端暂不支持从访达/资源管理器拖入文件,请点击选择框选择文件。

---

## 许可证

MIT

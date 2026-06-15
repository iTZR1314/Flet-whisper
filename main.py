import asyncio
import os
import platform

import flet as ft
import stable_whisper
import yt_dlp

# 可选的 Whisper 模型尺寸（越大越准、越慢、占用越多）
MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "small"

# 支持的音视频扩展名
MEDIA_EXTS = [
    "mp3", "wav", "m4a", "flac", "aac", "ogg", "opus", "wma",
    "mp4", "mov", "mkv", "avi", "webm", "m4v", "mpeg", "mpg", "flv",
]

DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")


def load_whisper_backend(size: str):
    """按当前硬件自动选择 Whisper 后端，返回 (model, 后端名称)。

    - Apple Silicon → MLX（Metal 加速，需 stable-ts[mlx]）
    - NVIDIA GPU    → faster-whisper（CUDA，最快）；未装则用 PyTorch CUDA
    - 其它          → CPU
    """
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return stable_whisper.load_mlx_whisper(size), "MLX · Apple Silicon"

    cuda = False
    try:
        import torch
        cuda = torch.cuda.is_available()
    except Exception:
        cuda = False

    if cuda:
        try:
            # faster-whisper：CTranslate2 后端，NVIDIA 上最快（需 pip install faster-whisper）
            return (
                stable_whisper.load_faster_whisper(
                    size, device="cuda", compute_type="float16"
                ),
                "faster-whisper · CUDA",
            )
        except Exception:
            # 退回原版 PyTorch whisper 的 CUDA 路径
            return stable_whisper.load_model(size, device="cuda"), "PyTorch · CUDA"

    return stable_whisper.load_model(size), "CPU"


def detect_backend_label() -> str:
    """仅探测硬件用于 UI 显示（不加载模型）。"""
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "MLX · Apple Metal"
    try:
        import torch
        if torch.cuda.is_available():
            return f"NVIDIA CUDA · {torch.cuda.get_device_name(0)}"
    except Exception:
        pass
    return "CPU"

# Swiss / 国际主义风格令牌：黑、白、瑞士红，无圆角无阴影
INK = "#111111"
RED = "#E2231A"
GREY = "#7A7A7A"
LINE = "#111111"
HAIRLINE = "#E2E2E2"
PAPER = "#FFFFFF"
FONT = "Helvetica Neue"


def main(page: ft.Page):
    page.title = "WHISPER 字幕工作台"
    page.theme_mode = ft.ThemeMode.LIGHT
    # 用中性灰做种子，避免 M3 给菜单等表面染上红色调；强调红由各控件显式设定
    page.theme = ft.Theme(use_material3=True, color_scheme_seed=ft.Colors.GREY,
                          font_family=FONT)
    page.bgcolor = PAPER
    page.window.width = 760
    page.window.height = 820
    page.window.min_width = 600
    page.window.min_height = 660
    page.padding = ft.Padding(40, 36, 40, 36)

    # 运行期状态
    loaded_models: dict[str, object] = {}
    backend = {"label": ""}                     # 实际使用的后端名称
    download_dir = {"path": DEFAULT_DOWNLOAD_DIR}

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # ---------- 设计辅助 ----------
    def rule(thick: int = 2, color: str = LINE) -> ft.Container:
        return ft.Container(height=thick, bgcolor=color)

    def section_head(num: str, title: str) -> ft.Row:
        return ft.Row(
            [
                ft.Text(num, size=14, weight=ft.FontWeight.BOLD, color=RED,
                        font_family=FONT),
                ft.Text(title, size=19, weight=ft.FontWeight.BOLD, color=INK,
                        font_family=FONT),
            ],
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    solid_btn = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        bgcolor=INK, color=PAPER,
        padding=ft.Padding(26, 20, 26, 20),
        elevation=0,
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family=FONT),
    )
    red_btn = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        bgcolor=RED, color=PAPER,
        padding=ft.Padding(26, 20, 26, 20),
        elevation=0,
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family=FONT),
    )
    outline_btn = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        bgcolor=PAPER, color=INK,
        side=ft.BorderSide(1.5, INK),
        padding=ft.Padding(24, 20, 24, 20),
        elevation=0,
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family=FONT),
    )

    def swiss_field(field: ft.TextField) -> ft.TextField:
        field.filled = False
        field.border_radius = 0
        field.border_color = INK
        field.focused_border_color = RED
        field.border_width = 1.5
        field.text_style = ft.TextStyle(font_family=FONT)
        field.label_style = ft.TextStyle(color=GREY, font_family=FONT)
        return field

    # ---------- 顶部 MASTHEAD ----------
    device_label = detect_backend_label()
    backend_text = ft.Text(device_label, size=12, weight=ft.FontWeight.BOLD,
                           color=INK, font_family=FONT)
    backend_badge = ft.Container(
        content=ft.Row(
            [
                ft.Text("推理后端", size=10, weight=ft.FontWeight.BOLD, color=GREY,
                        font_family=FONT),
                ft.Container(width=8, height=8, bgcolor=RED),
                backend_text,
            ],
            spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 9, 12, 9),
        border=ft.Border.all(1.5, INK),
    )
    masthead = ft.Row(
        [
            ft.Container(width=46, height=46, bgcolor=RED),
            ft.Column(
                [
                    ft.Text("WHISPER 字幕工作台", size=26, weight=ft.FontWeight.BOLD,
                            color=INK, font_family=FONT),
                    ft.Text("下载 · 转录 · 中英双语字幕 — 跨平台 GPU 加速",
                            size=12.5, color=GREY, font_family=FONT),
                ],
                spacing=2, expand=True,
            ),
            backend_badge,
        ],
        spacing=18, vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    opt_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        bgcolor={ft.ControlState.SELECTED: INK, ft.ControlState.HOVERED: HAIRLINE,
                 ft.ControlState.DEFAULT: PAPER},
        color={ft.ControlState.SELECTED: PAPER, ft.ControlState.DEFAULT: INK},
        text_style=ft.TextStyle(font_family=FONT, weight=ft.FontWeight.BOLD),
    )
    model_dropdown = ft.Dropdown(
        label="模型尺寸",
        value=DEFAULT_MODEL,
        options=[ft.DropdownOption(s, style=opt_style) for s in MODEL_SIZES],
        width=180,
        border_radius=0,
        filled=False,
        border_color=INK,
        focused_border_color=RED,
        bgcolor=PAPER,
        elevation=0,
        text_style=ft.TextStyle(font_family=FONT),
        menu_style=ft.MenuStyle(
            bgcolor=PAPER,
            elevation=0,
            shape=ft.RoundedRectangleBorder(radius=0),
            side=ft.BorderSide(1.5, INK),
        ),
    )

    # ---------- 01 下载 ----------
    url_field = swiss_field(ft.TextField(
        label="视频链接",
        hint_text="粘贴 YouTube / B站 / X 等视频链接",
        expand=True,
    ))
    dir_label = ft.Text(download_dir["path"], size=12, color=GREY,
                        selectable=True, no_wrap=True, font_family=FONT)
    auto_transcribe = ft.Checkbox(label="下载完成后自动转录字幕", value=True,
                                  active_color=RED, check_color=PAPER)
    dl_progress = ft.ProgressBar(value=0, visible=False, border_radius=0,
                                 bar_height=6, color=RED, bgcolor=HAIRLINE)
    download_btn = ft.FilledButton("下载", style=red_btn)
    choose_dir_btn = ft.OutlinedButton("选择保存目录", style=outline_btn)

    download_section = ft.Column(
        [
            section_head("01", "下载视频"),
            ft.Container(height=6),
            url_field,
            ft.Row([choose_dir_btn, download_btn, auto_transcribe],
                   spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.Text("保存至", size=12, weight=ft.FontWeight.BOLD, color=INK,
                            font_family=FONT), dir_label],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            dl_progress,
        ],
        spacing=14,
    )

    # ---------- 02 转录 ----------
    drop_text = ft.Text("点击选择本地音视频文件", size=16, weight=ft.FontWeight.BOLD,
                        color=INK, font_family=FONT, text_align=ft.TextAlign.CENTER)
    drop_hint = ft.Text("MP4 / MOV / MP3 / WAV …", size=11.5, color=GREY,
                        font_family=FONT, text_align=ft.TextAlign.CENTER)
    tr_progress = ft.ProgressRing(visible=False, width=24, height=24, color=RED)
    drop_zone = ft.Container(
        content=ft.Column(
            [
                ft.Text("＋", size=40, weight=ft.FontWeight.BOLD, color=RED,
                        font_family=FONT),
                drop_text, drop_hint, tr_progress,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER, spacing=8,
        ),
        height=180,
        border=ft.Border.all(1.5, INK),
        border_radius=0,
        bgcolor=PAPER,
        alignment=ft.Alignment.CENTER,
        ink=True,
    )
    transcribe_section = ft.Column(
        [
            section_head("02", "转录字幕"),
            ft.Container(height=6),
            ft.Row([model_dropdown]),
            drop_zone,
        ],
        spacing=14,
    )

    # ---------- 状态 ----------
    status_dot = ft.Container(width=11, height=11, bgcolor=INK)
    status = ft.Text("就绪", size=13, weight=ft.FontWeight.BOLD, color=INK,
                     font_family=FONT)
    file_label = ft.Text("", size=12, color=GREY, selectable=True, font_family=FONT)
    result_label = ft.Text("", size=12.5, weight=ft.FontWeight.BOLD,
                           color=INK, selectable=True, font_family=FONT)
    status_section = ft.Column(
        [
            ft.Row([status_dot, status], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            file_label,
            result_label,
        ],
        spacing=8,
    )

    def set_status(message: str, kind: str = "info"):
        # 极简调色板：黑=正常/完成，红=进行中/错误
        status_dot.bgcolor = RED if kind in ("busy", "error") else INK
        status.color = RED if kind == "error" else INK
        status.value = message

    # ---------- 通用：忙碌状态 ----------
    def set_busy(busy: bool, message: str, kind: str = "busy"):
        download_btn.disabled = busy
        choose_dir_btn.disabled = busy
        url_field.disabled = busy
        drop_zone.disabled = busy
        model_dropdown.disabled = busy
        tr_progress.visible = busy and "转录" in message
        drop_text.value = "转录中…" if (busy and "转录" in message) else "点击选择本地音视频文件"
        set_status(message, kind)
        page.update()

    # ---------- 转录逻辑 ----------
    def do_transcribe(model, path: str) -> str:
        result = model.transcribe(path)
        base, _ = os.path.splitext(path)
        srt_path = base + ".srt"
        result.to_srt_vtt(srt_path, segment_level=True, word_level=False)
        return srt_path

    async def transcribe(path: str):
        result_label.value = ""
        model_size = model_dropdown.value or DEFAULT_MODEL
        try:
            if model_size not in loaded_models:
                set_busy(True, f"正在加载 Whisper 模型「{model_size}」（首次需下载）…")
                model, label = await asyncio.to_thread(load_whisper_backend, model_size)
                loaded_models[model_size] = model
                backend["label"] = label
                backend_text.value = label   # 用确认后的后端刷新顶部徽标
            set_busy(True, f"正在转录（{backend['label']}）：{os.path.basename(path)} …")
            srt_path = await asyncio.to_thread(
                do_transcribe, loaded_models[model_size], path
            )
            set_status("转录完成", "ok")
            result_label.value = f"字幕已保存：{srt_path}"
            result_label.color = INK
        except Exception as ex:
            set_status("转录失败", "error")
            result_label.value = f"错误：{ex}"
            result_label.color = RED
        finally:
            set_busy(False, status.value, "ok" if "完成" in status.value else "error")

    # ---------- 下载逻辑 ----------
    def do_download(url: str, target_dir: str, on_progress) -> str:
        # 跨多个流（视频+音频分别下载）累计字节，避免进度条来回归零跳动
        files: dict[str, tuple[int, int]] = {}   # 文件名 -> (已下载, 总大小)
        last_frac = {"v": -1.0}

        def hook(d):
            fn = d.get("filename") or d.get("tmpfilename") or "stream"
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0)
                files[fn] = (done, total)
                tot_done = sum(a for a, _ in files.values())
                tot_all = sum(b for _, b in files.values())
                if tot_all > 0:
                    frac = min(tot_done / tot_all, 1.0)
                    # 仅在变化≥0.3%时刷新，既平滑又不刷屏
                    if frac - last_frac["v"] >= 0.003 or frac >= 0.999:
                        last_frac["v"] = frac
                        speed = (d.get("_speed_str") or "").strip()
                        on_progress(frac, f"下载中… {int(frac * 100)}%  {speed}")
            elif d.get("status") == "finished":
                # 该流下完，按其总大小标记为已完成
                done, total = files.get(fn, (0, 0))
                files[fn] = (total or done, total or done)
                on_progress(None, "下载完成，正在合并/转码…")

        opts = {
            "outtmpl": os.path.join(target_dir, "%(title)s.%(ext)s"),
            "format": "bv*+ba/b",
            "merge_output_format": "mp4",
            "progress_hooks": [hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            reqs = info.get("requested_downloads")
            if reqs:
                return reqs[0]["filepath"]
            return ydl.prepare_filename(info)

    def report_download(value, message: str):
        dl_progress.value = value
        set_status(message, "busy")
        page.update()

    async def start_download(e):
        url = (url_field.value or "").strip()
        if not url:
            set_status("请先粘贴视频链接", "error")
            page.update()
            return
        result_label.value = ""
        target = download_dir["path"]
        os.makedirs(target, exist_ok=True)
        dl_progress.visible = True
        dl_progress.value = 0
        set_busy(True, "开始下载…")
        try:
            path = await asyncio.to_thread(do_download, url, target, report_download)
            set_status("下载完成", "ok")
            result_label.value = f"已保存：{path}"
            result_label.color = INK
            file_label.value = f"源文件：{path}"
            dl_progress.value = 1
            set_busy(False, status.value, "ok")
            if auto_transcribe.value:
                await transcribe(path)
        except Exception as ex:
            set_status("下载失败", "error")
            result_label.value = f"错误：{ex}"
            result_label.color = RED
            set_busy(False, status.value, "error")

    async def choose_dir(e):
        path = await file_picker.get_directory_path(
            dialog_title="选择视频保存目录",
            initial_directory=download_dir["path"],
        )
        if path:
            download_dir["path"] = path
            dir_label.value = path
            page.update()

    async def pick_file(e):
        files = await file_picker.pick_files(
            dialog_title="选择音视频文件",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=MEDIA_EXTS,
            allow_multiple=False,
        )
        if not files:
            return
        f = files[0]
        if not f.path:
            set_status("无法获取文件路径（请在桌面模式下运行）", "error")
            page.update()
            return
        file_label.value = f"源文件：{f.path}"
        page.update()
        await transcribe(f.path)

    # ---------- 绑定事件 ----------
    download_btn.on_click = start_download
    choose_dir_btn.on_click = choose_dir
    drop_zone.on_click = pick_file

    content = ft.Column(
        [
            masthead,
            rule(3),
            ft.Container(height=4),
            download_section,
            rule(1, HAIRLINE),
            transcribe_section,
            rule(1, HAIRLINE),
            status_section,
        ],
        spacing=22,
    )
    # 隐藏滚动条：仍可用滚轮/触控板滚动，但不显示滚动条
    page.add(
        ft.Column([content], scroll=ft.ScrollMode.HIDDEN, expand=True)
    )


if __name__ == "__main__":
    ft.run(main)

# YuWallpaper v0.2.0

## 简体中文

本地优先的 Windows 壁纸工具，提供中英文界面。

- 电脑默认 16:9 / 7680×4320，手机默认 9:16，支持手机型号和自定义尺寸。
- 导入图片、调整构图，导出 PNG 或循环 MP4；支持飘雪、萤火光点。
- Windows 静态壁纸直接应用；动态壁纸通过另行安装的 Lively 应用。
- 可选本地 AI 扩图，以及实验性 Wan2.2 头发 / 眨眼生成。

下载 Windows x64 portable ZIP，解压后双击 `Start-YuWallpaper.vbs`。基础功能不需要 Python、API Key 或订阅。AI 依赖和模型首次使用时单独下载；视频 AI 面向 24GB 级 NVIDIA 显卡。

17 项自动化测试通过，图片和粒子视频导出已验证。实际 Windows 桌面应用和 CUDA 模型推理仍待实机验证，AI 头发与眨眼质量尚未验证。8K 指输出尺寸，不代表原生生成细节。手机端提供文件导出，尚不支持直接设置壁纸或 iPhone Live Photo。

## English

A local-first Windows wallpaper tool with Chinese and English UI.

- Desktop defaults to 16:9 / 7680×4320; phone defaults to 9:16, with device presets and custom dimensions.
- Import an image, adjust composition, export PNG or looping MP4; snow and firefly effects included.
- Apply static wallpapers on Windows; apply videos through separately installed Lively.
- Optional local AI outpainting and experimental Wan2.2 hair / blink generation.

Download the Windows x64 portable ZIP, extract it, and double-click `Start-YuWallpaper.vbs`. Basic features require no Python installation, API key or subscription. AI dependencies and weights download separately on first use; video AI targets a 24GB-class NVIDIA GPU.

17 automated tests pass; image and particle-video exports are verified. Actual Windows desktop integration and CUDA model inference still require hardware validation. AI hair and blink quality remain unverified. 8K describes output dimensions, not native generated detail. Phone support currently exports files; direct wallpaper installation and iPhone Live Photo export are not implemented.

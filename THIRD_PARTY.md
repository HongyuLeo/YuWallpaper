# Third-party components

YuWallpaper source is MIT licensed. This does not relicense dependencies or model weights.

| Component | Distribution | License / source |
|---|---|---|
| Python 3.12.10 | Official Windows embedded distribution in the portable ZIP | PSF license; bundled `runtime/LICENSE.txt`; https://www.python.org/downloads/release/python-31210/ |
| Pillow 11.3.0 | PyPI wheel in portable ZIP | HPND and bundled dependency notices, retained in wheel metadata; https://github.com/python-pillow/Pillow/tree/11.3.0 |
| pip 25.2 | PyPI wheel in portable ZIP | MIT and vendored licenses retained in wheel metadata; https://github.com/pypa/pip/tree/25.2 |
| imageio-ffmpeg 0.6.0 | Windows wheel and binary | Wrapper BSD-2-Clause; FFmpeg binary has its own license; https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0 |
| FFmpeg | Binary supplied by imageio-ffmpeg, includes libx264 | GPL build; https://github.com/imageio/imageio-binaries and https://ffmpeg.org/legal.html ; build recipes: https://github.com/imageio/imageio-binaries/tree/master/ffmpeg |
| PyTorch / Diffusers / Transformers | Optional separately downloaded local AI dependencies | https://github.com/pytorch/pytorch ; https://github.com/huggingface/diffusers ; https://github.com/huggingface/transformers |
| Stable Diffusion Inpainting | Downloaded on first AI use, not bundled | CreativeML Open RAIL-M; https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting |
| Lively Wallpaper | Optional external application, not bundled | https://github.com/lively-community/lively |

Build manifest records package versions, artifact URLs and SHA-256 hashes. Wheel license metadata is retained in `runtime/site-packages`. FFmpeg source-distribution obligations must be checked before distributing modified binaries or publishing a commercial release; this repository does not change FFmpeg.

No user artwork or copyrighted character demonstration assets are bundled. The demo landscape is rendered programmatically by YuWallpaper's demo script.

Optional video model: Wan-AI/Wan2.2-TI2V-5B-Diffusers, Apache-2.0, https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers . Downloaded on first generation, not bundled. CUDA video runtime uses PyTorch 2.7.1+cu128 / torchvision 0.22.1+cu128 from the official PyTorch wheel index.

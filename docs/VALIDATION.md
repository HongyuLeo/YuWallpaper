# Validation — v0.2.0

## Passed in this build environment

- Python unit / integration suite: 17 tests, including foreground pixel preservation, EXIF orientation, crop coverage, particle periodicity, effect protection, invalid dimensions, real FFmpeg encoding, cancellation, authenticated loopback access, cross-origin rejection, traversal rejection, upload-to-export workflow, output byte ranges, and completed-history restoration.
- Browser automation: image import; 7680 × 4320 PNG export; iPhone 13 Pro Max preset at 1284 × 2778; lock-screen composition preview; phone PNG export; 4-second 30 FPS MP4; English language switching; settings dialog. No browser JavaScript errors recorded.
- Actual file checks: desktop PNG 7680 × 4320; phone PNG 1284 × 2778; MP4 886 × 1920, 120 frames, 30 FPS, duration exactly 4.000 seconds. MP4 dimensions round down to even pixels for H.264 compatibility.
- Chinese and English screenshots visually inspected. Demo artwork is procedural and bundled with its generating script.
- Windows package archive integrity checked; official embedded Python and Windows Pillow/FFmpeg binaries are included, with artifact URLs and checksums in the build manifest.

## v0.2 AI video validation

Added real Wan2.2 image-to-video integration using `WanImageToVideoPipeline` from Diffusers 0.35.2. Its source explicitly supports `expand_timesteps` for Wan2.2 5B I2V; the default repository WanPipeline is text-to-video and is deliberately not used.

Additional tests cover malformed/empty masks, no feather bleeding outside selected pixels, protected regions, periodic frame scheduling, synthetic worker-to-compositor integration, early no-CUDA rejection, and inference frame/dimension contracts. **Synthetic frames are test doubles, not generated model output.** Browser automation checks painting a motion mask and the missing-runtime guidance.

Actual model inference, hair appearance, blink quality and speed remain **unverified** because this build environment has no CUDA GPU. The runtime installer and large weights are not included in the portable ZIP. No claim of natural blinking or stable hair animation has been demonstrated.

## Not verified here

- Launching the Windows portable package, native static wallpaper application, and Lively CLI integration on an actual Windows desktop. The package was assembled on Linux; no Windows compatibility or SmartScreen claim is made.
- Optional local AI dependency installation, actual model download and inference, CUDA availability, AI output quality or timing. The implementation follows the model's Diffusers inpainting interface, but no weights were loaded in this environment.
- Native 8K generative detail, actual hair / blink quality, phone wallpaper installation or Live Photo export. Phone installation and Live Photo export are not implemented.

The release workflow includes a Windows runtime import smoke test. It is supplied as source and has not been executed remotely during this build.

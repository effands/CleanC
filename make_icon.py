from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
source = Image.open(root / "CleanC_transparent.png").convert("RGBA")
# A multi-resolution ICO prevents Windows from scaling one small bitmap and
# producing a soft/blurry taskbar icon.
source.save(
    root / "CleanC.ico",
    format="ICO",
    sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)],
)

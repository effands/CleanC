from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
# Use the exact user-provided broom artwork for the Windows shell icon.
source = Image.open(root / "CleanC.png").convert("RGBA")
source.save(
    root / "CleanC.ico",
    format="ICO",
    sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)],
)

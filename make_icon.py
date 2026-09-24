from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent
# Use a deliberately simple mark for Windows shell sizes. The detailed broom
# artwork is attractive in the About screen, but becomes blurry at 16-32px.
source = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
draw = ImageDraw.Draw(source)
draw.polygon(
    [(500, 42), (190, 545), (420, 545), (330, 980), (850, 365), (590, 365)],
    fill="#38bdf8",
)
draw.polygon(
    [(500, 42), (190, 545), (420, 545), (380, 720), (650, 365), (590, 365)],
    fill="#06b6d4",
)
draw.line([(500, 42), (190, 545), (420, 545), (330, 980)], fill="#e0f2fe", width=12, joint="curve")
# A multi-resolution ICO prevents Windows from scaling one small bitmap and
# producing a soft/blurry taskbar icon.
source.save(
    root / "CleanC.ico",
    format="ICO",
    sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)],
)

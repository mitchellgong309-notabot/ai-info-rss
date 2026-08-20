"""一次性生成 PWA 图标到 static/icons/（已提交，平时无需运行）。"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

BG = (11, 87, 208)     # 主题蓝
FG = (255, 255, 255)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def make(size: int, pad_ratio: float = 0.0) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    pad = int(size * pad_ratio)
    # 右下装饰圆点，避免纯文字单调
    r = size // 10
    d.ellipse([size - pad - 2 * r, size - pad - 2 * r,
               size - pad, size - pad], fill=(138, 180, 248))
    font = None
    for path in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, int(size * 0.52))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), "AI", font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1] - size * 0.04),
           "AI", font=font, fill=FG)
    return img


make(192, pad_ratio=0.04).save(OUT / "icon-192.png")
make(512, pad_ratio=0.10).save(OUT / "icon-512.png")       # maskable 安全区
make(512, pad_ratio=0.04).save(OUT / "icon-512-any.png")
print("icons generated:", [p.name for p in OUT.iterdir()])

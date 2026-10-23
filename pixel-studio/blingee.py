"""Procedural pixel stickers and glitter. No external artwork or network calls."""
import random
from PIL import Image, ImageDraw
from message import add_message

STICKERS = ("爱心", "星星", "蝴蝶结")
PATTERNS = {
    "爱心": ("01100110", "12211221", "12222221", "12222221", "01222210", "00122100", "00011000", "00000000"),
    "星星": ("000100000", "001210000", "001210000", "111211110", "122222210", "012222100", "012112100", "121001210", "110000110"),
    "蝴蝶结": ("110000011", "121000121", "122101221", "122212221", "122212221", "122101221", "121000121", "110000011"),
}


def render_frame(base, stickers=(), glitter=True, phase=0, message=None):
    """Positions and sizes are normalized so previews and exports match."""
    result = base.convert("RGBA").copy()
    width, height = result.size
    unit = max(1, min(width, height) / 240)
    draw = ImageDraw.Draw(result)
    if glitter:
        rng = random.Random(4242)
        colors = ("#fff7b2", "#ffffff", "#ff91d0", "#bcadff")
        for index in range(65):
            x, y = rng.random() * width, rng.random() * height
            offset = rng.randrange(12)
            brightness = (phase + offset) % 12
            if brightness > 7:
                continue
            radius = unit * (1 + (3 - abs(3 - brightness)) * 0.65)
            color = colors[index % len(colors)]
            thickness = max(1, round(unit))
            draw.line((x - radius, y, x + radius, y), fill=color, width=thickness)
            draw.line((x, y - radius, x, y + radius), fill=color, width=thickness)
    for sticker in stickers:
        pattern = PATTERNS[sticker["kind"]]
        x, y, fraction = sticker["x"], sticker["y"], sticker["size"]
        cells = max(map(len, pattern))
        cell = max(1, round(min(width, height) * fraction / cells))
        left = round(x * width - cells * cell / 2)
        top = round(y * height - len(pattern) * cell / 2)
        fill = "#ffe177" if sticker["kind"] == "星星" else "#ff83c2"
        for row, line in enumerate(pattern):
            for column, pixel in enumerate(line):
                if pixel != "0":
                    color = "#702654" if pixel == "1" else fill
                    cx, cy = left + column * cell, top + row * cell
                    draw.rectangle((cx, cy, cx + cell - 1, cy + cell - 1), fill=color)
    return add_message(result, message)


def animation_frames(base, stickers=(), glitter=True, max_side=720, message=None):
    """Bound GIF memory; retain aspect ratio and never enlarge the input."""
    small = base.copy()
    small.thumbnail((max_side, max_side), Image.Resampling.NEAREST)
    return [render_frame(small, stickers, glitter, phase, message) for phase in range(12 if glitter else 1)]


def save_gif(path, frames):
    """GIF has no soft alpha: consistently composite transparency onto white."""
    rgb_frames = []
    for frame in frames:
        background = Image.new("RGBA", frame.size, "white")
        background.alpha_composite(frame.convert("RGBA"))
        rgb_frames.append(background.convert("RGB"))
    rgb_frames[0].save(path, format="GIF", save_all=True, append_images=rgb_frames[1:],
                       duration=160, loop=0, disposal=2, optimize=False)

"""Fixed-family message layout shared by preview, PNG and GIF export."""
import os
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=64)
def fixed_font(size):
    windows_font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc"
    if windows_font.exists():
        return ImageFont.truetype(str(windows_font), size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


def wrap_text(text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for character in paragraph:
            if line and font.getlength(line + character) > width:
                lines.append(line)
                line = ""
            line += character
        lines.append(line)
    return lines


@lru_cache(maxsize=32)
def message_layer(text, color, aspect, box):
    """Layout on a canonical grid to keep wrapping identical at export sizes."""
    width, height = max(1, round(1000 * aspect[0])), max(1, round(1000 * aspect[1]))
    box_width, box_height = max(1, round(width * box[2])), max(1, round(height * box[3]))
    padding = min(8, max(0, min(box_width, box_height) // 10))
    available_width = max(1, box_width - padding * 2)
    available_height = max(1, box_height - padding * 2)
    for size in range(max(1, round(min(width, height) * .05)), 0, -1):
        font = fixed_font(size)
        lines = wrap_text(text, font, available_width)
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + max(1, size // 5)
        if len(lines) * line_height <= available_height and all(font.getlength(line) <= available_width for line in lines):
            break
    layer = Image.new("RGBA", (box_width, box_height))
    draw = ImageDraw.Draw(layer)
    for index, line in enumerate(lines):
        draw.text((padding, padding + index * line_height), line, font=font, fill=color, anchor="lt")
    return layer


def add_message(image, message):
    if not message or not message.get("text", "").strip():
        return image
    width, height = image.size
    longest = max(width, height)
    box = tuple(message["box"])
    layer = message_layer(message["text"][:300], message["color"], (width / longest, height / longest), box)
    dimensions = (max(1, round(width * box[2])), max(1, round(height * box[3])))
    resized = layer.resize(dimensions, Image.Resampling.LANCZOS)
    image.alpha_composite(resized, (round(width * box[0]), round(height * box[1])))
    return image

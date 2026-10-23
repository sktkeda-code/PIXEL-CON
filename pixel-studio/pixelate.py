"""Image conversion independent of the desktop interface."""
from PIL import Image, ImageOps


def load_image(path: str) -> Image.Image:
    """Read the first frame, honor camera orientation, and preserve transparency."""
    with Image.open(path) as source:
        source.load()
        return ImageOps.exif_transpose(source).convert("RGBA")


def pixelate(image: Image.Image, block_size: int) -> Image.Image:
    """Average into a small grid and enlarge without smoothing; keep original size."""
    if not isinstance(block_size, int) or isinstance(block_size, bool) or block_size < 1:
        raise ValueError("像素颗粒大小必须是正整数")
    image = image.convert("RGBA")
    if block_size == 1:
        return image.copy()
    width, height = image.size
    grid = (max(1, (width + block_size - 1) // block_size),
            max(1, (height + block_size - 1) // block_size))
    return image.resize(grid, Image.Resampling.BOX).resize(image.size, Image.Resampling.NEAREST)

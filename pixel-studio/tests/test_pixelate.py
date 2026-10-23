import tempfile
import unittest
from pathlib import Path

from PIL import Image

from pixelate import load_image, pixelate


class ConversionTests(unittest.TestCase):
    def test_average_color(self):
        image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
        image.putpixel((0, 0), (0, 0, 255, 255))
        result = pixelate(image, 2)
        self.assertEqual(result.size, (2, 2))
        self.assertEqual(len(set(result.getdata())), 1)
        # Pillow's separable BOX filter may round each pass; allow one level.
        actual = result.getpixel((0, 0))
        for measured, expected in zip(actual, (191, 0, 64, 255)):
            self.assertLessEqual(abs(measured - expected), 1)

    def test_size_and_transparency(self):
        image = Image.new("RGBA", (17, 9), (0, 0, 0, 0))
        result = pixelate(image, 256)
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.getextrema()[3], (0, 0))

    def test_one_is_lossless_copy(self):
        image = Image.new("RGBA", (3, 2), (15, 27, 39, 80))
        self.assertEqual(pixelate(image, 1).tobytes(), image.tobytes())
        self.assertIsNot(pixelate(image, 1), image)

    def test_invalid_size(self):
        for size in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                pixelate(Image.new("RGB", (1, 1)), size)

    def test_png_roundtrip_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            Image.new("RGBA", (13, 7), (20, 40, 60, 120)).save(source)
            original_bytes = source.read_bytes()
            result = pixelate(load_image(str(source)), 4)
            result.save(output)
            self.assertEqual(load_image(str(output)).tobytes(), result.tobytes())
            self.assertEqual(source.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()

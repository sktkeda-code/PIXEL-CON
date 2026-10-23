import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageSequence

from blingee import STICKERS, animation_frames, render_frame, save_gif


class BlingeeTests(unittest.TestCase):
    def test_disabled_effect_is_lossless_and_does_not_mutate_input(self):
        base = Image.new("RGBA", (200, 160), (14, 25, 36, 100))
        before = base.tobytes()
        self.assertEqual(render_frame(base, glitter=False).tobytes(), before)
        render_frame(base)
        self.assertEqual(base.tobytes(), before)

    def test_each_sticker_has_visible_pixels_at_placement(self):
        base = Image.new("RGBA", (200, 160), (0, 0, 0, 0))
        for kind in STICKERS:
            with self.subTest(kind=kind):
                sticker = dict(kind=kind, x=.5, y=.5, size=.2)
                result = render_frame(base, [sticker], glitter=False)
                self.assertIsNotNone(result.getbbox())
                self.assertGreater(result.getpixel((100, 80))[3], 0)
                self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_animation_changes_and_caps_size(self):
        frames = animation_frames(Image.new("RGBA", (1440, 900), "black"))
        self.assertEqual(len(frames), 12)
        self.assertEqual(frames[0].size, (720, 450))
        self.assertNotEqual(frames[0].tobytes(), frames[1].tobytes())
        self.assertEqual(frames[0].tobytes(), animation_frames(Image.new("RGBA", (1440, 900), "black"))[0].tobytes())

    def test_gif_roundtrip_and_white_matte(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "animation.gif"
            frames = animation_frames(Image.new("RGBA", (180, 120), (0, 0, 0, 0)))
            save_gif(path, frames)
            with Image.open(path) as output:
                self.assertEqual(output.n_frames, 12)
                self.assertEqual(output.info["loop"], 0)
                self.assertEqual(output.info["duration"], 160)
                self.assertEqual(output.size, (180, 120))
                for frame in ImageSequence.Iterator(output):
                    self.assertEqual(frame.convert("RGB").getpixel((179, 119)), (255, 255, 255))

    def test_no_glitter_exports_single_frame(self):
        frames = animation_frames(Image.new("RGBA", (20, 10)), glitter=False)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].size, (20, 10))


if __name__ == "__main__":
    unittest.main()

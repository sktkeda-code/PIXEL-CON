import unittest
from types import SimpleNamespace
import tkinter as tk
from PIL import Image
from blingee import animation_frames, render_frame
from app import PixelStudio


class MessageRenderingTests(unittest.TestCase):
    def test_color_and_clipping_to_area(self):
        base = Image.new("RGBA", (500, 400))
        message = dict(text="Hello\n你好，像素！", color="#FF0000", box=[.2, .3, .5, .3])
        output = render_frame(base, glitter=False, message=message)
        bounds = output.getbbox()
        self.assertIsNotNone(bounds)
        self.assertGreaterEqual(bounds[0], 100)
        self.assertGreaterEqual(bounds[1], 120)
        self.assertLessEqual(bounds[2], 350)
        self.assertLessEqual(bounds[3], 240)
        visible = [pixel for pixel in output.getdata() if pixel[3] > 240]
        self.assertTrue(visible)
        self.assertTrue(all(pixel[0] > 240 and pixel[1] < 10 and pixel[2] < 10 for pixel in visible))
        self.assertIsNone(base.getbbox())

    def test_blank_message_and_animation(self):
        base = Image.new("RGBA", (300, 200), "black")
        message = dict(text="", color="#FFFFFF", box=[.1, .1, .8, .5])
        self.assertEqual(render_frame(base, glitter=False, message=message).tobytes(), base.tobytes())
        message["text"] = "留言测试"
        frames = animation_frames(base, glitter=True, message=message)
        plain = animation_frames(base, glitter=True)
        self.assertEqual(len(frames), 12)
        for edited, original in zip(frames, plain):
            self.assertNotEqual(edited.tobytes(), original.tobytes())


class MessageInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PixelStudio(self.root)
        self.app.original = Image.new("RGBA", (500, 400), "black")
        self.app.generate()

    def tearDown(self):
        self.root.destroy()

    def test_text_works_without_blingee_and_stays_inside_image(self):
        app = self.app
        app.message_input.insert("1.0", "你好！")
        app.message_enabled.set(True)
        app.refresh_effects()
        self.assertFalse(app.blingee.get())
        self.assertEqual(len(app.frames), 1)
        self.assertEqual(app.message_data()["text"], "你好！")
        app.edit_message.set(True)
        app.result_bounds = (0, 0, 500, 400)
        app.canvas_press(SimpleNamespace(x=100, y=280))
        app.canvas_drag(SimpleNamespace(x=-1000, y=2000))
        app.canvas_release(None)
        bx, by, bw, bh = app.message_box
        self.assertGreaterEqual(bx, 0)
        self.assertLessEqual(by + bh, 1)
        app.result_bounds = (0, 0, 500, 400)
        app.canvas_press(SimpleNamespace(x=(bx+bw)*500, y=(by+bh)*400))
        app.canvas_drag(SimpleNamespace(x=2000, y=2000))
        self.assertLessEqual(app.message_box[0] + app.message_box[2], 1)
        self.assertLessEqual(app.message_box[1] + app.message_box[3], 1)
        self.assertEqual(app.stickers, [])
        app.message_enabled.set(False)
        app.refresh_effects()
        self.assertEqual(app.frames, [])

    def test_length_limit(self):
        self.app.message_input.insert("1.0", "文" * 350)
        self.app.message_changed()
        self.assertEqual(len(self.app.message_input.get("1.0", "end-1c")), 300)


if __name__ == "__main__":
    unittest.main()

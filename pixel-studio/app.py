"""Local image-to-pixel desktop application. Run: python app.py"""
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from pixelate import load_image, pixelate
from blingee import STICKERS, animation_frames, render_frame, save_gif


class PixelStudio:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.original = None
        self.result = None
        self.source_path = None
        self.photos = {}
        self.resize_job = None
        self.animation_job = None
        self.frames = []
        self.frame_index = 0
        self.stickers = []
        self.result_bounds = None
        self.message_box = [.1, .65, .8, .25]
        self.message_color = "#FFFFFF"
        self.text_drag = None
        self.text_job = None
        root.title("像素工坊 · 图片转像素")
        root.geometry("1120x900")
        root.minsize(900, 760)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        header = ttk.Frame(root, padding=(20, 18))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="像素工坊", font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w")
        ttk.Label(header, text="本地图片转像素 · 可选 Blingee 闪粉与像素贴纸 · 图片仅在本机处理").pack(anchor="w", pady=(5, 0))

        controls = ttk.Frame(root, padding=(20, 0, 20, 14))
        controls.grid(row=1, column=0, sticky="ew")
        ttk.Button(controls, text="选择图片…", command=self.open_image).pack(side="left")
        ttk.Label(controls, text="  颗粒大小（像素）：").pack(side="left")
        self.block = tk.StringVar(value="12")
        ttk.Spinbox(controls, from_=1, to=256, width=6, textvariable=self.block).pack(side="left")
        self.generate_button = ttk.Button(controls, text="生成像素图", command=self.generate, state="disabled")
        self.generate_button.pack(side="left", padx=12)
        self.save_button = ttk.Button(controls, text="保存 PNG…", command=self.save, state="disabled")
        self.save_button.pack(side="left")

        effects = ttk.LabelFrame(root, text="个性化 · Blingee", padding=10)
        effects.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.blingee = tk.BooleanVar(value=False)
        self.glitter = tk.BooleanVar(value=True)
        self.playing = tk.BooleanVar(value=True)
        ttk.Checkbutton(effects, text="启用 Blingee", variable=self.blingee, command=self.refresh_effects).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(effects, text="闪粉特效", variable=self.glitter, command=self.refresh_effects).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Checkbutton(effects, text="播放预览", variable=self.playing, command=self.toggle_playback).grid(row=0, column=2, sticky="w")
        self.gif_button = ttk.Button(effects, text="导出 GIF…", command=self.export_gif, state="disabled")
        self.gif_button.grid(row=0, column=3, padx=8)
        ttk.Label(effects, text="贴纸：").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.sticker_kind = tk.StringVar(value=STICKERS[0])
        ttk.Combobox(effects, textvariable=self.sticker_kind, values=STICKERS, state="readonly", width=9).grid(row=1, column=1, sticky="w", pady=(10, 0))
        self.sticker_size = tk.StringVar(value="15")
        size_controls = ttk.Frame(effects)
        size_controls.grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Label(size_controls, text="大小 %：").pack(side="left")
        ttk.Spinbox(size_controls, from_=5, to=40, textvariable=self.sticker_size, width=4).pack(side="left")
        ttk.Button(effects, text="撤销最后贴纸", command=self.undo_sticker).grid(row=1, column=3, pady=(10, 0), padx=8)
        ttk.Button(effects, text="清空贴纸", command=self.clear_stickers).grid(row=1, column=4, pady=(10, 0))
        ttk.Label(effects, text="生成后启用 Blingee，选好贴纸，再点击右侧图片放置。关闭开关保留贴纸，重新生成保留布局；换图清空。").grid(row=2, column=0, columnspan=5, sticky="w", pady=(10, 0))

        message_controls = ttk.LabelFrame(root, text="文字留言", padding=10)
        message_controls.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.message_enabled = tk.BooleanVar(value=False)
        self.edit_message = tk.BooleanVar(value=False)
        ttk.Checkbutton(message_controls, text="显示留言", variable=self.message_enabled, command=self.refresh_effects).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(message_controls, text="调整留言区域", variable=self.edit_message, command=self.redraw).grid(row=0, column=1, sticky="w")
        self.color_button = tk.Button(message_controls, text="选择颜色", command=self.choose_message_color, background=self.message_color)
        self.color_button.grid(row=0, column=2, padx=8)
        ttk.Button(message_controls, text="重置区域", command=self.reset_message_box).grid(row=0, column=3)
        self.message_input = tk.Text(message_controls, height=2, width=55, wrap="word", font=("Microsoft YaHei UI", 11), undo=True)
        self.message_input.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 4))
        message_controls.columnconfigure(1, weight=1)
        self.message_input.bind("<<Modified>>", self.message_changed)
        ttk.Label(message_controls, text="最多 300 字，支持换行；字体固定为微软雅黑，自动换行并适应区域。勾选调整后拖动虚线框移动，拖右下角缩放；编辑框不导出。").grid(row=2, column=0, columnspan=4, sticky="w")

        previews = ttk.Frame(root, padding=(20, 0, 20, 10))
        previews.grid(row=4, column=0, sticky="nsew")
        previews.rowconfigure(0, weight=1)
        self.canvases = {}
        for column, (key, title) in enumerate((("original", "原图"), ("result", "像素图"))):
            previews.columnconfigure(column, weight=1, uniform="preview")
            frame = ttk.LabelFrame(previews, text=title, padding=8)
            frame.grid(row=0, column=column, sticky="nsew", padx=(0, 7) if column == 0 else (7, 0))
            canvas = tk.Canvas(frame, background="#202432", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.bind("<Configure>", self.schedule_redraw)
            self.canvases[key] = canvas
        self.canvases["result"].bind("<Button-1>", self.canvas_press)
        self.canvases["result"].bind("<B1-Motion>", self.canvas_drag)
        self.canvases["result"].bind("<ButtonRelease-1>", self.canvas_release)

        self.status = tk.StringVar(value="尚未选择图片。支持 PNG、JPEG、WebP、BMP、GIF（仅首帧）。")
        ttk.Label(root, textvariable=self.status, padding=(20, 10, 20, 16), wraplength=1000).grid(row=5, column=0, sticky="ew")
        self.redraw()

    def open_image(self):
        path = filedialog.askopenfilename(title="选择本地图片", filetypes=[
            ("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            # Bound memory and processing time before decoding the full image.
            with Image.open(path) as probe:
                if probe.width * probe.height > 20_000_000:
                    raise ValueError("图片超过 2000 万像素，请先缩小后再选择。")
            image = load_image(path)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
            messagebox.showerror("无法打开图片", str(error))
            return
        self.original = image
        self.source_path = Path(path)
        self.result = None
        self.stickers.clear()
        self.refresh_effects()
        self.generate_button.configure(state="normal")
        self.save_button.configure(state="disabled")
        self.status.set(f"已读取 {self.source_path.name} · {image.width} × {image.height}。调整颗粒大小后点击生成。")
        self.redraw()

    def generate(self):
        if self.original is None:
            return
        try:
            size = int(self.block.get())
            if not 1 <= size <= 256:
                raise ValueError()
        except ValueError:
            messagebox.showerror("参数不正确", "请输入 1～256 之间的整数。数字越大，像素块越大。")
            return
        try:
            result = pixelate(self.original, size)
        except (OSError, ValueError, MemoryError) as error:
            messagebox.showerror("转换失败", str(error))
            return
        self.result = result
        self.save_button.configure(state="normal")
        self.status.set(f"生成完成 · 颗粒约 {size} 像素 · 输出 {result.width} × {result.height} · 透明背景保留。可反复调整后重新生成。")
        self.refresh_effects()

    def save(self):
        if self.result is None:
            return
        path = filedialog.asksaveasfilename(title="保存像素图片", defaultextension=".png",
            initialfile=f"{self.source_path.stem}_pixel.png", filetypes=[("PNG 图片", "*.png")])
        if not path:
            return
        if Path(path).resolve() == self.source_path.resolve():
            messagebox.showerror("请选择新文件名", "请另存为新文件，以保留原图。")
            return
        try:
            output = render_frame(self.result, self.stickers if self.blingee.get() else (),
                                  self.blingee.get() and self.glitter.get(), 0, self.message_data())
            output.save(path, format="PNG")
        except (OSError, ValueError, MemoryError) as error:
            messagebox.showerror("保存失败", str(error))
            return
        self.status.set(f"已保存：{path}")

    def refresh_effects(self):
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        self.frame_index = 0
        self.frames = []
        if self.result is not None and (self.blingee.get() or self.message_enabled.get()):
            self.frames = animation_frames(self.result, self.stickers if self.blingee.get() else (),
                                          self.blingee.get() and self.glitter.get(), message=self.message_data())
        self.gif_button.configure(state="normal" if self.frames else "disabled")
        self.redraw()
        self.toggle_playback()

    def toggle_playback(self):
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        if len(self.frames) > 1 and self.playing.get():
            self.animation_job = self.root.after(160, self.animate)

    def message_data(self):
        if not self.message_enabled.get():
            return None
        return dict(text=self.message_input.get("1.0", "end-1c")[:300], color=self.message_color, box=self.message_box.copy())

    def message_changed(self, _event=None):
        if not self.message_input.edit_modified():
            return
        if len(self.message_input.get("1.0", "end-1c")) > 300:
            self.message_input.delete("1.0+300c", "end-1c")
        self.message_input.edit_modified(False)
        if self.text_job is not None:
            self.root.after_cancel(self.text_job)
        self.text_job = self.root.after(200, self.apply_message_change)

    def apply_message_change(self):
        self.text_job = None
        self.refresh_effects()

    def choose_message_color(self):
        color = colorchooser.askcolor(color=self.message_color, title="选择留言颜色", parent=self.root)[1]
        if color:
            self.message_color = color
            self.color_button.configure(background=color)
            self.refresh_effects()

    def reset_message_box(self):
        self.message_box = [.1, .65, .8, .25]
        self.refresh_effects()

    def canvas_press(self, event):
        if not self.edit_message.get():
            self.place_sticker(event)
            return
        if self.result is None or self.result_bounds is None:
            return
        left, top, width, height = self.result_bounds
        bx, by, bw, bh = self.message_box
        x0, y0 = left + bx * width, top + by * height
        x1, y1 = x0 + bw * width, y0 + bh * height
        if abs(event.x - x1) <= 12 and abs(event.y - y1) <= 12:
            mode = "resize"
        elif x0 <= event.x <= x1 and y0 <= event.y <= y1:
            mode = "move"
        else:
            return
        self.text_drag = (mode, event.x, event.y, self.message_box.copy(), width, height)

    def canvas_drag(self, event):
        if self.text_drag is None:
            return
        mode, x, y, old, width, height = self.text_drag
        dx, dy = (event.x - x) / width, (event.y - y) / height
        bx, by, bw, bh = old
        if mode == "move":
            self.message_box = [max(0, min(1-bw, bx+dx)), max(0, min(1-bh, by+dy)), bw, bh]
        else:
            self.message_box = [bx, by, max(.1, min(1-bx, bw+dx)), max(.08, min(1-by, bh+dy))]
        self.refresh_effects()

    def canvas_release(self, _event):
        self.text_drag = None

    def animate(self):
        self.animation_job = None
        if len(self.frames) > 1 and self.playing.get():
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.redraw(result_only=True)
            self.animation_job = self.root.after(160, self.animate)

    def place_sticker(self, event):
        if self.result is None or not self.blingee.get():
            self.status.set("请先生成像素图并启用 Blingee，再点击右侧图片放置贴纸。")
            return
        if self.result_bounds is None:
            return
        left, top, width, height = self.result_bounds
        if not (left <= event.x < left + width and top <= event.y < top + height):
            return
        try:
            size = int(self.sticker_size.get())
            if not 5 <= size <= 40:
                raise ValueError()
        except ValueError:
            messagebox.showerror("贴纸大小不正确", "请输入 5～40 之间的整数。")
            return
        if len(self.stickers) >= 100:
            messagebox.showinfo("贴纸数量", "最多可添加 100 张贴纸，请先撤销或清空。")
            return
        self.stickers.append(dict(kind=self.sticker_kind.get(), x=(event.x-left)/width,
                                  y=(event.y-top)/height, size=size/100))
        self.refresh_effects()
        self.status.set(f"已放置 {len(self.stickers)} 张贴纸。PNG 保存静态首帧，GIF 导出循环闪粉（最长边不超过 720 像素、白色底）。")

    def undo_sticker(self):
        if self.stickers:
            self.stickers.pop()
            self.refresh_effects()

    def clear_stickers(self):
        self.stickers.clear()
        self.refresh_effects()

    def export_gif(self):
        # Export the latest text even when its debounced preview is still pending.
        if self.text_job is not None:
            self.root.after_cancel(self.text_job)
            self.text_job = None
        self.refresh_effects()
        if not self.frames:
            return
        path = filedialog.asksaveasfilename(title="导出 GIF（最长边 720 像素，透明处转白色）", defaultextension=".gif",
            initialfile=f"{self.source_path.stem}_blingee.gif", filetypes=[("GIF 动画", "*.gif")])
        if not path:
            return
        if Path(path).resolve() == self.source_path.resolve():
            messagebox.showerror("请选择新文件名", "请另存为新文件，以保留原图。")
            return
        try:
            save_gif(path, self.frames)
        except (OSError, ValueError, MemoryError) as error:
            messagebox.showerror("GIF 导出失败", str(error))
            return
        self.status.set(f"已导出 GIF：{path} · {len(self.frames)} 帧 · 每帧 160 毫秒 · 白色底；未启用闪粉时为单帧。")

    def schedule_redraw(self, _event):
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self.redraw)

    def redraw(self, result_only=False):
        for key, canvas in self.canvases.items():
            if result_only and key != "result":
                continue
            canvas.delete("all")
            width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
            image = self.original if key == "original" else (self.frames[self.frame_index] if self.frames else self.result)
            if image is None:
                canvas.create_text(width // 2, height // 2, text="请选择图片" if key == "original" else "生成后在此预览", fill="#c9d0e4")
                continue
            scale = min((max(1, width - 20)) / image.width, (max(1, height - 20)) / image.height, 1)
            dimensions = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
            if key == "result":
                self.result_bounds = (width // 2 - dimensions[0] // 2, height // 2 - dimensions[1] // 2, *dimensions)
            preview = image.resize(dimensions, Image.Resampling.LANCZOS if key == "original" else Image.Resampling.NEAREST)
            # Checkerboard makes transparent regions visible without changing the exported image.
            background = Image.new("RGBA", dimensions, "#e1e3ea")
            from PIL import ImageDraw
            draw = ImageDraw.Draw(background)
            for y in range(0, dimensions[1], 12):
                for x in range(0, dimensions[0], 12):
                    if (x // 12 + y // 12) % 2:
                        draw.rectangle((x, y, x + 11, y + 11), fill="#bfc4d0")
            background.alpha_composite(preview)
            self.photos[key] = ImageTk.PhotoImage(background)
            canvas.create_image(width // 2, height // 2, image=self.photos[key])
            if key == "result" and self.edit_message.get():
                left, top, dw, dh = self.result_bounds
                bx, by, bw, bh = self.message_box
                x0, y0 = left + bx * dw, top + by * dh
                x1, y1 = x0 + bw * dw, y0 + bh * dh
                canvas.create_rectangle(x0, y0, x1, y1, outline="#00ffff", width=2, dash=(5, 3))
                canvas.create_rectangle(x1-6, y1-6, x1+6, y1+6, fill="#00ffff", outline="black")


if __name__ == "__main__":
    window = tk.Tk()
    PixelStudio(window)
    window.mainloop()

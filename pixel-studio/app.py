"""Local image-to-pixel desktop application. Run: python app.py"""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from pixelate import load_image, pixelate


class PixelStudio:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.original = None
        self.result = None
        self.source_path = None
        self.photos = {}
        self.resize_job = None
        root.title("像素工坊 · 图片转像素")
        root.geometry("1080x730")
        root.minsize(760, 520)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, padding=(20, 18))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="像素工坊", font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w")
        ttk.Label(header, text="选择本地图片 → 调整颗粒 → 生成像素图 → 保存 PNG。图片仅在本机处理。").pack(anchor="w", pady=(5, 0))

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

        previews = ttk.Frame(root, padding=(20, 0, 20, 10))
        previews.grid(row=2, column=0, sticky="nsew")
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

        self.status = tk.StringVar(value="尚未选择图片。支持 PNG、JPEG、WebP、BMP、GIF（仅首帧）。")
        ttk.Label(root, textvariable=self.status, padding=(20, 10, 20, 16), wraplength=1000).grid(row=3, column=0, sticky="ew")
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
        self.redraw()

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
            self.result.save(path, format="PNG")
        except (OSError, ValueError) as error:
            messagebox.showerror("保存失败", str(error))
            return
        self.status.set(f"已保存：{path}")

    def schedule_redraw(self, _event):
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self.redraw)

    def redraw(self):
        self.resize_job = None
        for key, canvas in self.canvases.items():
            canvas.delete("all")
            width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
            image = self.original if key == "original" else self.result
            if image is None:
                canvas.create_text(width // 2, height // 2, text="请选择图片" if key == "original" else "生成后在此预览", fill="#c9d0e4")
                continue
            scale = min((max(1, width - 20)) / image.width, (max(1, height - 20)) / image.height, 1)
            dimensions = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
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


if __name__ == "__main__":
    window = tk.Tk()
    PixelStudio(window)
    window.mainloop()

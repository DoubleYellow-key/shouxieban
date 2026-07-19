import io
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

try:
    from PIL import Image
except ImportError:  # Pillow is optional; the app works without it.
    Image = None


BACKGROUND = "#fffdf7"
DEFAULT_INK = "#202124"
MAX_UNDO_STEPS = 50


class HandwritingPad:
    def __init__(self, root):
        self.root = root
        self.root.title("手写板")
        self.root.geometry("1000x680")
        self.root.minsize(720, 460)

        self.tool = tk.StringVar(value="pen")
        self.color = DEFAULT_INK
        self.size = tk.IntVar(value=6)
        self.last_x = None
        self.last_y = None
        self.current_stroke = []
        self.undo_stack = []

        self._build_ui()
        self._update_status("准备书写")

    def _build_ui(self):
        self.root.configure(bg="#f5f2ea")

        toolbar = tk.Frame(self.root, bg="#f5f2ea", padx=12, pady=10)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        title = tk.Label(
            toolbar,
            text="手写板",
            font=("TkDefaultFont", 18, "bold"),
            fg="#202124",
            bg="#f5f2ea",
        )
        title.pack(side=tk.LEFT, padx=(0, 14))

        self.pen_button = tk.Radiobutton(
            toolbar,
            text="画笔",
            variable=self.tool,
            value="pen",
            indicatoron=False,
            command=lambda: self._update_status("正在使用画笔"),
            width=6,
        )
        self.pen_button.pack(side=tk.LEFT, padx=3)

        self.eraser_button = tk.Radiobutton(
            toolbar,
            text="橡皮",
            variable=self.tool,
            value="eraser",
            indicatoron=False,
            command=lambda: self._update_status("正在使用橡皮"),
            width=6,
        )
        self.eraser_button.pack(side=tk.LEFT, padx=3)

        self.color_button = tk.Button(
            toolbar,
            text="颜色",
            command=self.choose_color,
            width=6,
        )
        self.color_button.pack(side=tk.LEFT, padx=(12, 3))

        self.color_preview = tk.Label(
            toolbar,
            text="",
            width=3,
            bg=self.color,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.color_preview.pack(side=tk.LEFT, padx=(0, 12), ipady=9)

        size_label = tk.Label(toolbar, text="粗细", bg="#f5f2ea", fg="#6f6a61")
        size_label.pack(side=tk.LEFT, padx=(0, 4))

        self.size_scale = tk.Scale(
            toolbar,
            from_=1,
            to=36,
            orient=tk.HORIZONTAL,
            variable=self.size,
            showvalue=True,
            length=160,
            bg="#f5f2ea",
            highlightthickness=0,
        )
        self.size_scale.pack(side=tk.LEFT, padx=(0, 12))

        self.undo_button = tk.Button(toolbar, text="撤销", command=self.undo, width=6, state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT, padx=3)

        clear_button = tk.Button(toolbar, text="清空", command=self.clear, width=6, fg="#a94532")
        clear_button.pack(side=tk.LEFT, padx=3)

        save_button = tk.Button(toolbar, text="保存", command=self.save, width=6)
        save_button.pack(side=tk.LEFT, padx=3)

        self.status = tk.Label(toolbar, text="", bg="#f5f2ea", fg="#6f6a61", anchor=tk.E)
        self.status.pack(side=tk.RIGHT, padx=(12, 0))

        self.canvas = tk.Canvas(
            self.root,
            bg=BACKGROUND,
            highlightthickness=1,
            highlightbackground="#d8d1c3",
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.canvas.bind("<ButtonPress-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_stroke)

    def _update_status(self, text):
        self.status.configure(text=text)

    def choose_color(self):
        selected = colorchooser.askcolor(color=self.color, title="选择画笔颜色")
        if not selected or not selected[1]:
            return
        self.color = selected[1]
        self.color_preview.configure(bg=self.color)
        self.tool.set("pen")
        self.canvas.configure(cursor="crosshair")
        self._update_status("已选择颜色")

    def start_stroke(self, event):
        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []
        self._update_status("书写中" if self.tool.get() == "pen" else "擦除中")

    def draw(self, event):
        if self.last_x is None or self.last_y is None:
            return

        width = self.size.get()
        if self.tool.get() == "eraser":
            color = BACKGROUND
            width = max(width * 3, 8)
        else:
            color = self.color

        line = {
            "coords": [self.last_x, self.last_y, event.x, event.y],
            "options": {
                "fill": color,
                "width": width,
                "capstyle": tk.ROUND,
                "joinstyle": tk.ROUND,
                "smooth": True,
            },
        }
        line["id"] = self._create_line(line)
        self.current_stroke.append(line)
        self.last_x = event.x
        self.last_y = event.y

    def end_stroke(self, _event):
        self.last_x = None
        self.last_y = None
        if self.current_stroke:
            self.undo_stack.append(("stroke", self.current_stroke))
            self.undo_stack = self.undo_stack[-MAX_UNDO_STEPS:]
            self.current_stroke = []
            self._set_undo_enabled()
            self._update_status("已记录笔迹")
        else:
            self._update_status("准备书写")

    def _set_undo_enabled(self):
        state = tk.NORMAL if self.undo_stack else tk.DISABLED
        self.undo_button.configure(state=state)

    def undo(self):
        if not self.undo_stack:
            return

        action, payload = self.undo_stack.pop()
        if action == "stroke":
            for line in payload:
                self.canvas.delete(line["id"])
        elif action == "clear":
            restored_ids = {}
            for item in payload:
                restored_ids[item["id"]] = self._create_line(item)
            self._refresh_stroke_ids(restored_ids)

        self._set_undo_enabled()
        self._update_status("已撤销一步")

    def clear(self):
        items = self.canvas.find_all()
        if not items:
            self._update_status("画布已经是空的")
            return

        snapshot = [self._serialize_item(item_id) for item_id in items]
        self.undo_stack.append(("clear", snapshot))
        self.undo_stack = self.undo_stack[-MAX_UNDO_STEPS:]
        self.canvas.delete("all")
        self._set_undo_enabled()
        self._update_status("画布已清空")

    def _serialize_item(self, item_id):
        return {
            "id": item_id,
            "coords": self.canvas.coords(item_id),
            "options": {
                "fill": self.canvas.itemcget(item_id, "fill"),
                "width": float(self.canvas.itemcget(item_id, "width")),
                "capstyle": self.canvas.itemcget(item_id, "capstyle"),
                "joinstyle": self.canvas.itemcget(item_id, "joinstyle"),
                "smooth": self.canvas.itemcget(item_id, "smooth") in {"1", "true"},
            },
        }

    def _create_line(self, item):
        return self.canvas.create_line(*item["coords"], **item["options"])

    def _refresh_stroke_ids(self, restored_ids):
        for action, payload in self.undo_stack:
            if action != "stroke":
                continue
            for line in payload:
                if line["id"] in restored_ids:
                    line["id"] = restored_ids[line["id"]]

    def save(self):
        if Image is not None:
            filename = filedialog.asksaveasfilename(
                title="保存手写内容",
                defaultextension=".png",
                filetypes=[("PNG 图片", "*.png"), ("PostScript 文件", "*.ps")],
            )
        else:
            filename = filedialog.asksaveasfilename(
                title="保存手写内容",
                defaultextension=".ps",
                filetypes=[("PostScript 文件", "*.ps")],
            )

        if not filename:
            return

        try:
            self._save_to_file(filename)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            self._update_status("保存失败")
            return

        self._update_status(f"已保存：{filename}")

    def _save_to_file(self, filename):
        self.canvas.update()
        ps_data = self.canvas.postscript(
            colormode="color",
            pagewidth=self.canvas.winfo_width(),
            pageheight=self.canvas.winfo_height(),
        )

        if filename.lower().endswith(".png"):
            if Image is None:
                raise RuntimeError("当前环境未安装 Pillow，无法导出 PNG。请改存为 .ps 文件。")
            image = Image.open(io.BytesIO(ps_data.encode("utf-8")))
            image.save(filename, "png")
            return

        with open(filename, "w", encoding="utf-8") as file:
            file.write(ps_data)


def main():
    root = tk.Tk()
    app = HandwritingPad(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()

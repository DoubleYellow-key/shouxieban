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
APP_BG = "#f7f8fb"
PANEL_BG = "#ffffff"
PANEL_ALT = "#f0f3f7"
TEXT = "#1f2933"
MUTED = "#687385"
ACCENT = "#1f9d95"
ACCENT_DARK = "#14736d"
DANGER = "#c2412d"
LINE = "#d8dee8"
SWATCHES = ["#202124", "#d14335", "#1d6f9f", "#2d7a46", "#7c3aed", "#b7791f"]


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
        self.root.configure(bg=APP_BG)

        header = tk.Frame(self.root, bg=APP_BG, padx=22, pady=16)
        header.pack(side=tk.TOP, fill=tk.X)

        title_block = tk.Frame(header, bg=APP_BG)
        title_block.pack(side=tk.LEFT)

        title = tk.Label(
            title_block,
            text="Ink Studio",
            font=("Avenir Next", 24, "bold"),
            fg=TEXT,
            bg=APP_BG,
        )
        title.pack(anchor=tk.W)

        subtitle = tk.Label(
            title_block,
            text="Python 桌面手写板",
            font=("TkDefaultFont", 12),
            fg=MUTED,
            bg=APP_BG,
        )
        subtitle.pack(anchor=tk.W, pady=(2, 0))

        self.status = tk.Label(
            header,
            text="",
            bg="#e8f8f6",
            fg=ACCENT_DARK,
            padx=14,
            pady=7,
            font=("TkDefaultFont", 11, "bold"),
        )
        self.status.pack(side=tk.RIGHT)

        workspace = tk.Frame(self.root, bg=APP_BG, padx=22, pady=0)
        workspace.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(workspace, bg=PANEL_BG, width=228, padx=14, pady=16)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self._section_label(sidebar, "工具")
        self.tool_buttons = {
            "pen": self._tool_button(sidebar, "画笔", "pen"),
            "eraser": self._tool_button(sidebar, "橡皮", "eraser"),
        }

        self._section_label(sidebar, "颜色")
        swatch_grid = tk.Frame(sidebar, bg=PANEL_BG)
        swatch_grid.pack(fill=tk.X, pady=(0, 12))
        self.swatch_buttons = []
        for index, swatch in enumerate(SWATCHES):
            button = tk.Button(
                swatch_grid,
                text="",
                command=lambda value=swatch: self.set_color(value),
                width=3,
                height=1,
                bg=swatch,
                activebackground=swatch,
                relief=tk.FLAT,
                borderwidth=0,
                cursor="hand2",
            )
            button.grid(row=index // 3, column=index % 3, padx=4, pady=4, sticky=tk.EW)
            self.swatch_buttons.append((swatch, button))

        for column in range(3):
            swatch_grid.columnconfigure(column, weight=1)

        self.color_button = self._action_button(sidebar, "自定义颜色", self.choose_color)
        self.color_button.pack(fill=tk.X, pady=(0, 14), ipady=5)

        self._section_label(sidebar, "笔触")
        self.size_scale = tk.Scale(
            sidebar,
            from_=1,
            to=36,
            orient=tk.HORIZONTAL,
            variable=self.size,
            command=lambda _value: self._update_brush_preview(),
            showvalue=True,
            length=170,
            bg=PANEL_BG,
            fg=TEXT,
            troughcolor=LINE,
            activebackground=ACCENT,
            highlightthickness=0,
        )
        self.size_scale.pack(fill=tk.X, pady=(0, 8))

        self.brush_preview = tk.Canvas(
            sidebar,
            width=180,
            height=54,
            bg=PANEL_ALT,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.brush_preview.pack(fill=tk.X, pady=(0, 18))

        self._section_label(sidebar, "操作")
        self.undo_button = self._action_button(sidebar, "撤销  Ctrl+Z", self.undo)
        self.undo_button.pack(fill=tk.X, pady=4, ipady=6)
        self._set_clickable_enabled(self.undo_button, False)

        clear_button = self._action_button(sidebar, "清空", self.clear, fg=DANGER)
        clear_button.pack(fill=tk.X, pady=4, ipady=6)

        save_button = self._action_button(sidebar, "保存", self.save, bg=ACCENT, fg="#ffffff", active_bg=ACCENT_DARK)
        save_button.pack(fill=tk.X, pady=(4, 0), ipady=7)

        stage = tk.Frame(workspace, bg=APP_BG, padx=18)
        stage.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_header = tk.Frame(stage, bg=APP_BG)
        canvas_header.pack(fill=tk.X, pady=(0, 10))

        canvas_title = tk.Label(
            canvas_header,
            text="画布",
            font=("Avenir Next", 16, "bold"),
            fg=TEXT,
            bg=APP_BG,
        )
        canvas_title.pack(side=tk.LEFT)

        hint = tk.Label(
            canvas_header,
            text="按住左键拖动书写",
            fg=MUTED,
            bg=APP_BG,
            font=("TkDefaultFont", 11),
        )
        hint.pack(side=tk.RIGHT)

        self.canvas = tk.Canvas(
            stage,
            bg=BACKGROUND,
            highlightthickness=1,
            highlightbackground=LINE,
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
        self.root.bind("<Control-z>", lambda _event: self.undo())
        self.root.bind("<Command-z>", lambda _event: self.undo())
        self.root.bind("<Control-s>", lambda _event: self.save())
        self.root.bind("<Command-s>", lambda _event: self.save())
        self._refresh_tool_buttons()
        self._refresh_swatch_buttons()
        self._update_brush_preview()

    def _section_label(self, parent, text):
        label = tk.Label(
            parent,
            text=text,
            bg=PANEL_BG,
            fg=MUTED,
            font=("TkDefaultFont", 10, "bold"),
        )
        label.pack(anchor=tk.W, pady=(14, 7))
        return label

    def _tool_button(self, parent, text, tool):
        button = tk.Label(
            parent,
            text=text,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            anchor=tk.CENTER,
            font=("TkDefaultFont", 12, "bold"),
        )
        self._bind_clickable(button, lambda: self.select_tool(tool))
        button.pack(fill=tk.X, pady=4, ipady=8)
        return button

    def _action_button(self, parent, text, command, bg=PANEL_ALT, fg=TEXT, active_bg="#e1e7ef"):
        button = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            anchor=tk.CENTER,
            font=("TkDefaultFont", 11, "bold"),
        )
        self._style_clickable(button, bg, fg, active_bg, fg)
        self._bind_clickable(button, command)
        return button

    def _bind_clickable(self, widget, command):
        widget._command = command
        widget._enabled = True
        widget.bind("<Enter>", lambda _event: self._hover_clickable(widget, True))
        widget.bind("<Leave>", lambda _event: self._hover_clickable(widget, False))
        widget.bind("<Button-1>", lambda _event: self._click_clickable(widget))

    def _style_clickable(self, widget, bg, fg, active_bg, active_fg):
        widget._colors = {
            "bg": bg,
            "fg": fg,
            "active_bg": active_bg,
            "active_fg": active_fg,
            "disabled_bg": "#eef1f5",
            "disabled_fg": "#6b7280",
        }
        if getattr(widget, "_enabled", True):
            widget.configure(bg=bg, fg=fg)

    def _hover_clickable(self, widget, hovering):
        if not getattr(widget, "_enabled", True):
            return
        colors = widget._colors
        widget.configure(
            bg=colors["active_bg"] if hovering else colors["bg"],
            fg=colors["active_fg"] if hovering else colors["fg"],
        )

    def _click_clickable(self, widget):
        if getattr(widget, "_enabled", True):
            widget._command()

    def _set_clickable_enabled(self, widget, enabled):
        widget._enabled = enabled
        colors = widget._colors
        if enabled:
            widget.configure(bg=colors["bg"], fg=colors["fg"], cursor="hand2")
        else:
            widget.configure(bg=colors["disabled_bg"], fg=colors["disabled_fg"], cursor="arrow")

    def _update_status(self, text):
        self.status.configure(text=text)

    def select_tool(self, tool):
        self.tool.set(tool)
        self.canvas.configure(cursor="crosshair" if tool == "pen" else "dotbox")
        self._refresh_tool_buttons()
        self._update_brush_preview()
        self._update_status("正在使用画笔" if tool == "pen" else "正在使用橡皮")

    def set_color(self, color):
        self.color = color
        self.tool.set("pen")
        self.canvas.configure(cursor="crosshair")
        self._refresh_tool_buttons()
        self._refresh_swatch_buttons()
        self._update_brush_preview()
        self._update_status("已选择颜色")

    def _refresh_tool_buttons(self):
        for tool, button in self.tool_buttons.items():
            selected = self.tool.get() == tool
            button.configure(
                bg=ACCENT if selected else PANEL_ALT,
                fg="#ffffff" if selected else TEXT,
            )
            self._style_clickable(
                button,
                ACCENT if selected else PANEL_ALT,
                "#ffffff" if selected else TEXT,
                ACCENT_DARK if selected else "#e1e7ef",
                "#ffffff" if selected else TEXT,
            )

    def _refresh_swatch_buttons(self):
        for swatch, button in self.swatch_buttons:
            selected = swatch.lower() == self.color.lower()
            button.configure(
                relief=tk.SOLID if selected else tk.FLAT,
                borderwidth=3 if selected else 0,
                highlightthickness=2 if selected else 0,
                highlightbackground=ACCENT if selected else PANEL_BG,
            )

    def _update_brush_preview(self):
        if not hasattr(self, "brush_preview"):
            return
        self.brush_preview.delete("all")
        width = self.size.get()
        color = BACKGROUND if self.tool.get() == "eraser" else self.color
        outline = "#94a3b8" if self.tool.get() == "eraser" else color
        preview_width = max(width * (3 if self.tool.get() == "eraser" else 1), 8)
        self.brush_preview.create_line(
            22,
            28,
            158,
            28,
            fill=color,
            width=preview_width,
            capstyle=tk.ROUND,
            smooth=True,
        )
        if self.tool.get() == "eraser":
            self.brush_preview.create_line(
                22,
                28,
                158,
                28,
                fill=outline,
                width=1,
                dash=(4, 3),
            )

    def choose_color(self):
        selected = colorchooser.askcolor(color=self.color, title="选择画笔颜色")
        if not selected or not selected[1]:
            return
        self.set_color(selected[1])

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
        self._set_clickable_enabled(self.undo_button, bool(self.undo_stack))

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

# -*- coding: utf-8 -*-
# 从 ImageProcessor_v2.exe 反编译还原的源码（PyInstaller / Python 3.8）
# 还原说明：已人工修复反编译工具产生的语法噪声（多余括号、切片写法、分支缩进等），
# 逻辑经字节码反汇编逐一核对，与原程序行为一致。
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import math


class SimpleImageThresholdTool:

    def __init__(self, root):
        self.root = root
        self.root.title("简易图像二值化处理工具 - 快捷键说明在底部")
        self.root.geometry("1200x800")
        self.original_image = None
        self.gray_image = None
        self.binary_image = None
        self.display_image = None
        self.selected_mask = None
        self.export_dpi = tk.StringVar(value="300")
        self.lasso_points = []
        self.drawing = False
        self.selection_mode = False
        self.pan_mode = False
        self.pan_start = None
        self.global_threshold_min = tk.IntVar(value=100)
        self.global_threshold_max = tk.IntVar(value=255)
        self.local_threshold_min = tk.IntVar(value=100)
        self.local_threshold_max = tk.IntVar(value=255)
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.visual_mode = tk.StringVar(value="彩色覆盖")
        self.lasso_used = False
        self.shortcuts = {
            'Ctrl+O': '打开图像文件',
            'Ctrl+S': '导出二值图',
            'L': '激活套索选择工具',
            'Delete': '清除当前选择',
            'Enter': '应用局部阈值到选中区域',
            'Escape': '取消套索选择',
            '+/=': '放大图像',
            '-': '缩小图像',
            'Ctrl+0': '适合窗口大小',
            'Space+拖拽': '平移图像'}
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        control_frame = ttk.Frame(main_frame, width=320)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        control_frame.pack_propagate(False)
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shortcut_frame = ttk.Frame(self.root)
        shortcut_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        self.setup_control_panel(control_frame)
        self.setup_image_display(image_frame)
        self.setup_shortcut_display(shortcut_frame)

    def setup_control_panel(self, parent):
        canvas = tk.Canvas(parent, width=320)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        file_frame = ttk.LabelFrame(scrollable_frame, text="📁 文件操作", padding=6)
        file_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(file_frame, text="打开图像 (Ctrl+O)", command=self.load_image).pack(fill=tk.X, pady=1)
        ttk.Label(file_frame, text="导出DPI:").pack(anchor=tk.W)
        dpi_frame = ttk.Frame(file_frame)
        dpi_frame.pack(fill=tk.X)
        ttk.Radiobutton(dpi_frame, text="300dpi", variable=self.export_dpi, value="300").pack(side=tk.LEFT)
        ttk.Radiobutton(dpi_frame, text="600dpi", variable=self.export_dpi, value="600").pack(side=tk.LEFT)
        ttk.Button(file_frame, text="导出红白图 (Ctrl+S)", command=self.export_binary).pack(fill=tk.X, pady=1)

        view_frame = ttk.LabelFrame(scrollable_frame, text="🔍 视图控制", padding=6)
        view_frame.pack(fill=tk.X, pady=(0, 8))
        zoom_control = ttk.Frame(view_frame)
        zoom_control.pack(fill=tk.X, pady=1)
        ttk.Button(zoom_control, text="放大 (+)", command=self.zoom_in, width=7).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_control, text="缩小 (-)", command=self.zoom_out, width=7).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_control, text="适合窗口", command=self.fit_to_window, width=9).pack(side=tk.LEFT, padx=1)
        self.zoom_label = ttk.Label(view_frame, text="缩放: 100%", font=('Arial', 8))
        self.zoom_label.pack(pady=1)

        visual_frame = ttk.LabelFrame(scrollable_frame, text="👁️ 显示模式", padding=6)
        visual_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(visual_frame, text="彩色覆盖（白区显示原图）", variable=self.visual_mode,
                        value="彩色覆盖",
                        command=self.update_display).pack(anchor=tk.W)
        ttk.Radiobutton(visual_frame, text="纯黑白图", variable=self.visual_mode,
                        value="纯二值",
                        command=self.update_display).pack(anchor=tk.W)

        info_frame = ttk.LabelFrame(scrollable_frame, text="💡 处理说明", padding=6)
        info_frame.pack(fill=tk.X, pady=(0, 8))
        info_text = "原理：彩色→灰度→亮度过滤\n技巧：调最小值去暗区，调最大值去亮区\n导出：红色=保留区域，白色=背景"
        ttk.Label(info_frame, text=info_text, wraplength=280, justify=tk.LEFT,
                  font=('Arial', 8)).pack(anchor=tk.W)

        global_frame = ttk.LabelFrame(scrollable_frame, text="🌐 全局亮度过滤（仅限首次）", padding=6)
        global_frame.pack(fill=tk.X, pady=(0, 8))
        self.global_info_label = ttk.Label(global_frame, text="💡 使用套索后将锁定", font=('Arial', 8),
                                           foreground="orange")
        self.global_info_label.pack(anchor=tk.W, pady=(0, 3))
        ttk.Label(global_frame, text="最小值:", font=('Arial', 8)).pack(anchor=tk.W)
        self.global_min_scale = ttk.Scale(global_frame, from_=0, to=255, variable=self.global_threshold_min,
                                          orient=tk.HORIZONTAL,
                                          command=self.update_global_threshold)
        self.global_min_scale.pack(fill=tk.X, pady=1)
        ttk.Label(global_frame, textvariable=self.global_threshold_min, font=('Arial', 8)).pack()
        ttk.Label(global_frame, text="最大值:", font=('Arial', 8)).pack(anchor=tk.W, pady=(5, 0))
        self.global_max_scale = ttk.Scale(global_frame, from_=0, to=255, variable=self.global_threshold_max,
                                          orient=tk.HORIZONTAL,
                                          command=self.update_global_threshold)
        self.global_max_scale.pack(fill=tk.X, pady=1)
        ttk.Label(global_frame, textvariable=self.global_threshold_max, font=('Arial', 8)).pack()

        lasso_frame = ttk.LabelFrame(scrollable_frame, text="✂️ 区域选择工具", padding=6)
        lasso_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(lasso_frame, text="⚠️ 首次使用后将锁定全局设置", font=('Arial', 8),
                  foreground="red").pack(anchor=tk.W, pady=(0, 3))
        self.lasso_button = ttk.Button(lasso_frame, text="开始套索选择 (L)", command=self.start_selection)
        self.lasso_button.pack(fill=tk.X, pady=1)
        ttk.Button(lasso_frame, text="清除选择 (Delete)", command=self.clear_selection).pack(fill=tk.X, pady=1)

        local_frame = ttk.LabelFrame(scrollable_frame, text="📍 选中区域亮度过滤", padding=6)
        local_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(local_frame, text="仅对选中区域使用不同参数", font=('Arial', 8),
                  foreground="darkgreen").pack(anchor=tk.W, pady=(0, 3))
        ttk.Label(local_frame, text="最小值:", font=('Arial', 8)).pack(anchor=tk.W)
        local_min_scale = ttk.Scale(local_frame, from_=0, to=255, variable=self.local_threshold_min,
                                    orient=tk.HORIZONTAL,
                                    command=self.update_local_threshold)
        local_min_scale.pack(fill=tk.X, pady=1)
        ttk.Label(local_frame, textvariable=self.local_threshold_min, font=('Arial', 8)).pack()
        ttk.Label(local_frame, text="最大值:", font=('Arial', 8)).pack(anchor=tk.W, pady=(5, 0))
        local_max_scale = ttk.Scale(local_frame, from_=0, to=255, variable=self.local_threshold_max,
                                    orient=tk.HORIZONTAL,
                                    command=self.update_local_threshold)
        local_max_scale.pack(fill=tk.X, pady=1)
        ttk.Label(local_frame, textvariable=self.local_threshold_max, font=('Arial', 8)).pack()
        ttk.Button(local_frame, text="应用到选中区域 (Enter)", command=self.apply_local_threshold).pack(fill=tk.X, pady=3)

        status_frame = ttk.LabelFrame(scrollable_frame, text="📊 状态信息", padding=6)
        status_frame.pack(fill=tk.X, pady=(0, 8))
        self.status_label = ttk.Label(status_frame, text="Please load an image file to start processing",
                                      wraplength=280,
                                      font=('Arial', 8))
        self.status_label.pack()

    def setup_image_display(self, parent):
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="gray20")
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.focus_set()

    def setup_shortcut_display(self, parent):
        """设置快捷键说明显示"""
        ttk.Label(parent, text="💡 快捷键:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        shortcut_text = " | ".join([f"{k}: {v}" for k, v in list(self.shortcuts.items())[:6]])
        ttk.Label(parent, text=shortcut_text, font=('Arial', 8), foreground="darkblue").pack(side=tk.LEFT, padx=5)

    def setup_shortcuts(self):
        """设置快捷键绑定"""
        self.root.bind("<Control-o>", lambda e: self.load_image())
        self.root.bind("<Control-s>", lambda e: self.export_binary())
        self.root.bind("<KeyPress-l>", lambda e: self.start_selection())
        self.root.bind("<KeyPress-L>", lambda e: self.start_selection())
        self.root.bind("<Delete>", lambda e: self.clear_selection())
        self.root.bind("<Return>", lambda e: self.apply_local_threshold())
        self.root.bind("<Escape>", lambda e: self.cancel_selection())
        self.root.bind("<KeyPress-plus>", lambda e: self.zoom_in())
        self.root.bind("<KeyPress-equal>", lambda e: self.zoom_in())
        self.root.bind("<KeyPress-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-Key-0>", lambda e: self.fit_to_window())
        self.root.bind("<KeyPress-space>", self.start_pan_mode)
        self.root.bind("<KeyRelease-space>", self.end_pan_mode)

    def load_image(self):
        file_path = filedialog.askopenfilename(title="Select Image File",
                                               filetypes=[
                                                   ('Image Files', ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif')),
                                                   ('All Files', '*')])
        if file_path:
            self.original_image = cv2.imread(file_path)
            if self.original_image is None:
                messagebox.showerror("Error", "Cannot load image file")
                return
            self.gray_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.lasso_used = False
            self.enable_global_controls()
            self.update_global_threshold()
            h, w = self.original_image.shape[:2]
            self.status_label.config(text=f"Image loaded: {w}x{h}, converted to grayscale")
            self.fit_to_window()

    def enable_global_controls(self):
        """启用全局阈值控件"""
        self.global_min_scale.config(state="normal")
        self.global_max_scale.config(state="normal")
        self.global_info_label.config(text="💡 使用套索后将锁定", foreground="orange")

    def disable_global_controls(self):
        """禁用全局阈值控件"""
        self.global_min_scale.config(state="disabled")
        self.global_max_scale.config(state="disabled")
        self.global_info_label.config(text="🔒 全局设置已锁定，重新加载图像可解锁", foreground="red")

    def apply_range_threshold(self, gray_data, min_val, max_val):
        """应用范围阈值到灰度图"""
        return cv2.inRange(gray_data, min_val, max_val)

    def update_global_threshold(self, event=None):
        if self.gray_image is None:
            return
        if self.lasso_used:
            return
        if self.global_threshold_min.get() > self.global_threshold_max.get():
            if event and hasattr(event, "widget") and "min" in str(event.widget):
                self.global_threshold_max.set(self.global_threshold_min.get())
            else:
                self.global_threshold_min.set(self.global_threshold_max.get())
        self.binary_image = self.apply_range_threshold(self.gray_image,
                                                       self.global_threshold_min.get(),
                                                       self.global_threshold_max.get())
        self.update_display()
        white_pixels = np.sum(self.binary_image == 255)
        total_pixels = self.binary_image.size
        percentage = white_pixels / total_pixels * 100
        self.status_label.config(text=f"White area ratio: {percentage:.1f}% ({white_pixels}/{total_pixels})")

    def update_display(self):
        """更新显示"""
        if self.selected_mask is not None:
            self.display_binary_image_with_preview()
        else:
            self.display_binary_image()

    def create_visual_binary_image(self, binary_mask):
        """创建可视化的二值图像"""
        if self.visual_mode.get() == "彩色覆盖":
            h, w = binary_mask.shape
            result = np.zeros((h, w, 3), dtype=np.uint8)
            white_pixels = binary_mask == 255
            if self.original_image is not None:
                result[white_pixels] = self.original_image[white_pixels]
            return result
        return cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)

    def display_binary_image(self):
        """显示二值图像"""
        if self.binary_image is None:
            return
        display_image = self.create_visual_binary_image(self.binary_image)
        display_scaled = self.apply_zoom_and_pan(display_image)
        if self.selected_mask is not None:
            mask_scaled = self.apply_zoom_and_pan(self.selected_mask)
            if len(mask_scaled.shape) == 2:
                contours, _ = cv2.findContours(mask_scaled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(display_scaled, contours, -1, (0, 0, 255), 2)
        self.show_image_on_canvas(display_scaled)

    def display_binary_image_with_preview(self):
        """显示带有局部阈值预览效果的二值图像"""
        if self.binary_image is None or self.selected_mask is None:
            return
        if self.local_threshold_min.get() > self.local_threshold_max.get():
            return
        preview_binary = self.binary_image.copy()
        if self.gray_image is not None:
            local_binary = self.apply_range_threshold(self.gray_image,
                                                      self.local_threshold_min.get(),
                                                      self.local_threshold_max.get())
            preview_binary = np.where(self.selected_mask > 0, local_binary, preview_binary)
        display_image = self.create_visual_binary_image(preview_binary)
        display_scaled = self.apply_zoom_and_pan(display_image)
        mask_scaled = self.apply_zoom_and_pan(self.selected_mask)
        if len(mask_scaled.shape) == 2:
            contours, _ = cv2.findContours(mask_scaled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(display_scaled, contours, -1, (0, 255, 0), 2)
        self.show_image_on_canvas(display_scaled)
        white_pixels_selected = np.sum((self.selected_mask > 0) & (preview_binary == 255))
        selected_pixels = np.sum(self.selected_mask > 0)
        if selected_pixels > 0:
            preview_percentage = white_pixels_selected / selected_pixels * 100
            self.status_label.config(text=f"Preview mode - Selected area white ratio: {preview_percentage:.1f}%")

    def apply_zoom_and_pan(self, image):
        """应用缩放和平移到图像"""
        if image is None:
            return
        if len(image.shape) == 2:
            h, w = image.shape
        else:
            h, w = image.shape[:2]
        new_w = int(w * self.zoom_level)
        new_h = int(h * self.zoom_level)
        if len(image.shape) == 2:
            scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        else:
            scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return scaled

    def show_image_on_canvas(self, image):
        """在画布上显示图像"""
        if image is None:
            return
        elif len(image.shape) == 2:
            pil_image = Image.fromarray(image)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
        self.display_image = ImageTk.PhotoImage(pil_image)
        self.canvas.delete("all")
        self.canvas.create_image(self.pan_x, self.pan_y, anchor=tk.NW, image=self.display_image)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.zoom_label.config(text=f"缩放: {int(self.zoom_level * 100)}%")

    def zoom_in(self):
        """放大图像"""
        self.zoom_level = min(self.zoom_level * 1.2, 10.0)
        self.update_display()

    def zoom_out(self):
        """缩小图像"""
        self.zoom_level = max(self.zoom_level / 1.2, 0.1)
        self.update_display()

    def fit_to_window(self):
        """适合窗口大小"""
        if self.original_image is None:
            return
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 800
            canvas_height = 600
        img_height, img_width = self.original_image.shape[:2]
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        self.zoom_level = min(scale_x, scale_y) * 0.9
        self.pan_x = 0
        self.pan_y = 0
        self.update_display()

    def start_pan_mode(self, event):
        """开始平移模式"""
        self.pan_mode = True
        self.canvas.config(cursor="fleur")

    def end_pan_mode(self, event):
        """结束平移模式"""
        self.pan_mode = False
        self.canvas.config(cursor="")

    def on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def start_selection(self):
        if self.binary_image is None:
            messagebox.showwarning("Warning", "Please load an image first")
            return
        if not self.lasso_used:
            self.lasso_used = True
            self.disable_global_controls()
        self.selection_mode = True
        self.lasso_points = []
        self.selected_mask = None
        self.canvas.config(cursor="crosshair")
        self.status_label.config(text="Lasso mode: Hold left mouse to draw selection area")

    def clear_selection(self):
        self.selection_mode = False
        self.lasso_points = []
        self.selected_mask = None
        self.canvas.config(cursor="")
        self.display_binary_image()
        self.status_label.config(text="Selection cleared, can select new area or export result")

    def cancel_selection(self):
        """取消套索选择"""
        if self.selection_mode:
            self.selection_mode = False
            self.lasso_points = []
            self.canvas.delete("lasso")
            self.canvas.config(cursor="")
            self.status_label.config(text="Lasso selection cancelled")

    def on_mouse_down(self, event):
        if self.pan_mode:
            self.pan_start = (event.x, event.y)
        else:
            if self.selection_mode and self.binary_image is not None:
                self.drawing = True
                self.lasso_points = []
                self.canvas.delete("lasso")
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                self.lasso_points.append((canvas_x, canvas_y))

    def on_mouse_drag(self, event):
        if self.pan_mode and self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start = (event.x, event.y)
            self.update_display()
        else:
            if self.drawing and self.selection_mode:
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                self.lasso_points.append((canvas_x, canvas_y))
                if len(self.lasso_points) > 1:
                    self.canvas.create_line(self.lasso_points[-2][0],
                                            self.lasso_points[-2][1],
                                            self.lasso_points[-1][0],
                                            self.lasso_points[-1][1], fill="red",
                                            width=2,
                                            tags="lasso")

    def on_mouse_up(self, event):
        if self.pan_mode:
            self.pan_start = None
        else:
            if self.drawing and self.selection_mode:
                self.drawing = False
                if len(self.lasso_points) > 3:
                    if len(self.lasso_points) > 1:
                        self.canvas.create_line(self.lasso_points[-1][0],
                                                self.lasso_points[-1][1],
                                                self.lasso_points[0][0],
                                                self.lasso_points[0][1], fill="red",
                                                width=2,
                                                tags="lasso")
                    self.create_selection_mask()
                    self.selection_mode = False
                    self.canvas.config(cursor="")
                    self.status_label.config(text="Area selected, adjust sliders below for real-time preview (green border = previewing)")
                else:
                    self.lasso_points = []
                self.canvas.delete("lasso")

    def create_selection_mask(self):
        if not self.lasso_points or self.binary_image is None:
            return
        h, w = self.binary_image.shape
        original_points = []
        for x, y in self.lasso_points:
            orig_x = int((x - self.pan_x) / self.zoom_level)
            orig_y = int((y - self.pan_y) / self.zoom_level)
            orig_x = max(0, min(w - 1, orig_x))
            orig_y = max(0, min(h - 1, orig_y))
            original_points.append([orig_x, orig_y])
        self.selected_mask = np.zeros((h, w), dtype=np.uint8)
        points = np.array(original_points, dtype=np.int32)
        cv2.fillPoly(self.selected_mask, [points], 255)
        self.canvas.delete("lasso")
        self.display_binary_image_with_preview()

    def update_local_threshold(self, event=None):
        if self.local_threshold_min.get() > self.local_threshold_max.get():
            if event and hasattr(event, "widget") and "min" in str(event.widget):
                self.local_threshold_max.set(self.local_threshold_min.get())
            else:
                self.local_threshold_min.set(self.local_threshold_max.get())
        if self.selected_mask is not None and self.gray_image is not None:
            self.display_binary_image_with_preview()
        else:
            if self.binary_image is not None:
                self.display_binary_image()

    def apply_local_threshold(self):
        if self.selected_mask is None:
            messagebox.showwarning("Warning", "Please select an area first")
            return
        if self.gray_image is None:
            return
        local_binary = self.apply_range_threshold(self.gray_image,
                                                  self.local_threshold_min.get(),
                                                  self.local_threshold_max.get())
        self.binary_image = np.where(self.selected_mask > 0, local_binary, self.binary_image)
        self.selected_mask = None
        self.display_binary_image()
        self.status_label.config(text="Local processing completed, can select other areas or export result")

    def export_binary(self):
        if self.binary_image is None:
            messagebox.showwarning("Warning", "No processing result to export")
            return
        file_path = filedialog.asksaveasfilename(title="Save Red-White Image",
                                                 defaultextension=".png",
                                                 filetypes=[
                                                     ('PNG Images', '*.png'),
                                                     ('JPEG Images', '*.jpg'),
                                                     ('All Files', '*.*')])
        if not file_path:
            return
        h, w = self.binary_image.shape
        red_white = np.zeros((h, w, 3), dtype=np.uint8)
        red_white[self.binary_image == 255] = [0, 0, 255]
        red_white[self.binary_image == 0] = [255, 255, 255]
        dpi = int(self.export_dpi.get())
        if dpi == 300:
            canvas_w, canvas_h = (2480, 3508)
        else:
            canvas_w, canvas_h = (4960, 7016)
        img_long_edge = max(w, h)
        img_short_edge = min(w, h)
        canvas_long_edge = max(canvas_w, canvas_h)
        canvas_short_edge = min(canvas_w, canvas_h)
        if img_long_edge < canvas_long_edge or img_short_edge < canvas_short_edge:
            canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 255
            x_offset = (canvas_w - w) // 2
            y_offset = (canvas_h - h) // 2
            canvas[y_offset:y_offset + h, x_offset:x_offset + w] = red_white
            final_image = canvas
            final_w, final_h = canvas_w, canvas_h
        else:
            final_image = red_white
            final_w, final_h = w, h
        success = cv2.imwrite(file_path, final_image)
        if success:
            white_count = np.sum(self.binary_image == 255)
            total = self.binary_image.size
            ratio = white_count / total * 100
            messagebox.showinfo("Export Success",
                                f"Image saved to: {file_path}\nFinal size: {final_w}×{final_h} px ({dpi}dpi)\nRed area: {ratio:.1f}%\nWhite background: {100 - ratio:.1f}%")
        else:
            messagebox.showerror("Error", "Save failed")


def main():
    root = tk.Tk()
    app = SimpleImageThresholdTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()

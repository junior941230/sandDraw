import time
import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox,
    QFormLayout, QMessageBox, QComboBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from canvas import previewCanvas


# ── 預設沙畫曲線庫 ──────────────────────────────────────────
PRESETS = {
    "利薩如 3:2（蝴蝶結）": {
        "x_expr": "sin(3*t + pi/4)",
        "y_expr": "sin(2*t)",
        "t_min": 0, "t_max": 2, "n_pts": 200,
        "decay": 0.0,
    },
    "利薩如 5:4（花格）": {
        "x_expr": "sin(5*t + pi/3)",
        "y_expr": "sin(4*t)",
        "t_min": 0, "t_max": 8, "n_pts": 400,
        "decay": 0.0,
    },
    "玫瑰曲線 k=3（三瓣）": {
        "x_expr": "cos(3*t) * cos(t)",
        "y_expr": "cos(3*t) * sin(t)",
        "t_min": 0, "t_max": 2, "n_pts": 150,
        "decay": 0.0,
    },
    "玫瑰曲線 k=3.5（七瓣）": {
        "x_expr": "cos(3.5*t) * cos(t)",
        "y_expr": "cos(3.5*t) * sin(t)",
        "t_min": 0, "t_max": 4, "n_pts": 1000,
        "decay": 0.0,
    },
    "Harmonograph（衰減）": {
        "x_expr": "exp(-0.002*t)*sin(2*t+0.5) + exp(-0.003*t)*sin(3*t)",
        "y_expr": "exp(-0.001*t)*sin(2.01*t) + exp(-0.004*t)*sin(1.99*t+1.2)",
        "t_min": 0, "t_max": 60, "n_pts": 2000,
        "decay": 0.0,
    },
    "阿基米德螺旋": {
        "x_expr": "t * cos(t)",
        "y_expr": "t * sin(t)",
        "t_min": 0, "t_max": 6, "n_pts": 150,
        "decay": 0.0,
    },
    "超級橢圓 n=3": {
        "x_expr": "abs(cos(t))**(2/3) * sign(cos(t))",
        "y_expr": "abs(sin(t))**(2/3) * sign(sin(t))",
        "t_min": 0, "t_max": 2, "n_pts": 150,
        "decay": 0.0,
    },
    "利薩如 7:6（精細網格）": {
        "x_expr": "sin(7*t + pi/6)",
        "y_expr": "sin(6*t)",
        "t_min": 0, "t_max": 12, "n_pts": 2000,
        "decay": 0.0,
    },
    "清除": {
        "x_expr": "t * cos(t)",
        "y_expr": "t * sin(t)",
        "t_min": 0, "t_max": 50, "n_pts": 2000,
        "decay": 0.0,
    }
}

COLORMAPS = ["plasma", "viridis", "inferno",
             "cool", "twilight", "hsv", "rainbow"]


class SandPlotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏖️ 沙畫機函數繪圖器")
        self.setMinimumSize(1050, 680)
        self._init_ui()
        # 啟動時載入第一個預設
        self._load_preset(list(PRESETS.keys())[0])
        self.plot()

    # ────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────
    def _init_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(10)
        main.setContentsMargins(10, 10, 10, 10)
        main.addWidget(self._build_left(), stretch=1)
        main.addWidget(self._build_right(), stretch=3)

    def _build_left(self):
        panel = QGroupBox("⚙️ 沙畫設定")
        panel.setMinimumWidth(240)
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # ── 預設選單 ──
        preset_group = QGroupBox("📚 預設曲線")
        pg_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        pg_layout.addWidget(self.preset_combo)
        layout.addWidget(preset_group)

        # ── 參數式輸入 ──
        expr_group = QGroupBox("函數表達式（參數 t）")
        expr_layout = QFormLayout(expr_group)
        expr_layout.setSpacing(6)

        mono = QFont("Courier New", 10)
        self.x_expr = QLineEdit()
        self.x_expr.setFont(mono)
        self.x_expr.returnPressed.connect(self.plot)
        self.y_expr = QLineEdit()
        self.y_expr.setFont(mono)
        self.y_expr.returnPressed.connect(self.plot)
        expr_layout.addRow("x(t) =", self.x_expr)
        expr_layout.addRow("y(t) =", self.y_expr)

        hint = QLabel("可用：sin cos exp log sqrt abs\nsign pi t")
        hint.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        expr_layout.addRow(hint)
        layout.addWidget(expr_group)

        # ── t 範圍 ──
        t_group = QGroupBox("t 範圍")
        t_form = QFormLayout(t_group)
        self.t_min = QDoubleSpinBox()
        self.t_min.setRange(0, 32)
        self.t_min.setValue(0)
        self.t_min.setSingleStep(0.1)
        self.t_min.valueChanged.connect(self.plot)
        self.t_max = QDoubleSpinBox()
        self.t_max.setRange(0, 1024)
        self.t_max.setValue(2)
        self.t_max.setSingleStep(0.1)
        self.t_max.valueChanged.connect(self.plot)
        self.n_pts = QSpinBox()
        self.n_pts.setRange(100, 200000)
        self.n_pts.setValue(3000)
        self.n_pts.setSingleStep(1000)
        self.n_pts.valueChanged.connect(self.plot)
        t_form.addRow("t 最小(π)：", self.t_min)
        t_form.addRow("t 最大(π)：", self.t_max)
        t_form.addRow("取樣點：", self.n_pts)
        layout.addWidget(t_group)

        # ── 顯示選項 ──
        # vis_group = QGroupBox("🎨 視覺選項")
        # vis_layout = QVBoxLayout(vis_group)

        # # 色彩映射
        # cmap_row = QHBoxLayout()
        # cmap_row.addWidget(QLabel("漸層："))
        # self.cmap_combo = QComboBox()
        # self.cmap_combo.addItems(COLORMAPS)
        # cmap_row.addWidget(self.cmap_combo)
        # vis_layout.addLayout(cmap_row)

        # # 線寬
        # lw_row = QHBoxLayout()
        # lw_row.addWidget(QLabel("線寬："))
        # self.line_width = QDoubleSpinBox()
        # self.line_width.setRange(0.3, 5.0)
        # self.line_width.setValue(1.2)
        # self.line_width.setSingleStep(0.1)
        # lw_row.addWidget(self.line_width)
        # vis_layout.addLayout(lw_row)

        # self.show_grid = QCheckBox("格線")
        # self.show_start = QCheckBox("標示起點 / 終點")
        # self.show_start.setChecked(True)
        # self.dark_mode = QCheckBox("深色背景")
        # self.dark_mode.setChecked(True)
        # vis_layout.addWidget(self.show_grid)
        # vis_layout.addWidget(self.show_start)
        # vis_layout.addWidget(self.dark_mode)
        # layout.addWidget(vis_group)

        # ── 按鈕 ──
        plot_btn = QPushButton("▶  繪製沙畫")
        plot_btn.setDefault(False)       # ← 加這行
        plot_btn.setAutoDefault(False)   # ← 加這行
        plot_btn.setStyleSheet("""
            QPushButton {
                background: #e67e22; color: white;
                border-radius: 6px; padding: 9px;
                font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #d35400; }
            QPushButton:pressed { background: #a04000; }
        """)
        plot_btn.clicked.connect(self.drawFunc)

        # clear_btn = QPushButton("🗑  清除")
        # clear_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #555; color: white;
        #         border-radius: 6px; padding: 6px;
        #     }
        #     QPushButton:hover { background: #333; }
        # """)
        # clear_btn.clicked.connect(self._clear)

        layout.addWidget(plot_btn)
        # layout.addWidget(clear_btn)
        layout.addStretch()
        return panel

    def _build_right(self):
        panel = QGroupBox("📊 沙畫預覽")
        layout = QVBoxLayout(panel)
        self.preview = previewCanvas()
        layout.addWidget(self.preview)
        return panel

    # ────────────────────────────────────────
    #  輔助方法
    # ────────────────────────────────────────

    def _load_preset(self, name):
        p = PRESETS[name]
        self.x_expr.setText(p["x_expr"])
        self.y_expr.setText(p["y_expr"])
        self.t_min.setValue(p["t_min"])
        self.t_max.setValue(p["t_max"])
        self.n_pts.setValue(p["n_pts"])

    def _on_preset_changed(self, name):
        self._load_preset(name)
        self.plot()

    # ────────────────────────────────────────
    #  核心繪圖
    # ────────────────────────────────────────

    def plot(self):
        x_str = self.x_expr.text().strip()
        y_str = self.y_expr.text().strip()
        if not x_str or not y_str:
            QMessageBox.warning(self, "提示", "請輸入 x(t) 和 y(t) 的表達式！")
            return

        # 解析 t 範圍
        safe_ns_eval = {k: getattr(np, k)
                        for k in dir(np) if not k.startswith("_")}
        safe_ns_eval["pi"] = np.pi
        try:
            t_min_val = self.t_min.value() * np.pi
            t_max_val = self.t_max.value() * np.pi
            if t_min_val >= t_max_val:
                raise ValueError("t 最小值必須小於最大值")
        except Exception as e:
            QMessageBox.critical(self, "範圍錯誤", str(e))
            return

        # 計算曲線
        try:
            t = np.linspace(t_min_val, t_max_val, self.n_pts.value())
            ns = {k: getattr(np, k) for k in dir(np) if not k.startswith("_")}
            ns.update({"t": t, "pi": np.pi, "__builtins__": {}})
            self.xArray = np.array(eval(x_str, ns), dtype=float)
            self.yArray = np.array(eval(y_str, ns), dtype=float)

        except Exception as e:
            QMessageBox.critical(self, "函數錯誤", f"無法計算曲線：\n{e}")
            return

        # ── 縮放到 350×350 圓形內 ────────────────────────────
        # x, y = self._fit_to_circle(x, y, diameter=350)

        # ── 繪圖 ──────────────────────────────────────────────
        self.colorList = self.preview.drawPreview(self.xArray, self.yArray)

    def getValues(self):
        return self.xArray, self.yArray, self.colorList

    def drawFunc(self):
        self.accept()  # 關閉對話框


# ── 入口 ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dlg = SandPlotDialog()

    # 用 exec() 阻塞，等待使用者關閉對話框
    if dlg.exec() == QDialog.DialogCode.Accepted:
        xArray, yArray, colorList = dlg.getValues()
        all_points = np.column_stack((xArray, yArray))
        path = greedy_nearest(all_points, start_idx=0)
        path = two_opt(all_points, path, max_iter=500)
        ordered_points = all_points[path]
        print("優化後的點序：", path)

    sys.exit(0)

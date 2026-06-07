
from PyQt6.QtWidgets import QMainWindow, QDialog, QApplication
from PyQt6.QtCore import QTimer
from esp32serial import ESP32Serial
from canvas import mainCanvas
from gcode import GCodeProcessor
from UI import Ui_MainWindow
from dialog import SandPlotDialog
from planner import PathPlannerPro
import sys


class MainController(QMainWindow):
    """主控制器類別，負責協調應用程式的主要邏輯。"""

    def __init__(self):
        self.info_lines = []
        self.line_colors = []
        self.point = (0, 0)
        self.startTimes = 0
        self.planned_paths = []

        """初始化主控制器。"""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        """serial init"""
        self.esp32_serial = ESP32Serial()
        self.gcode_processor = GCodeProcessor(self.esp32_serial)
        self.gcode_processor.text_received.connect(self.infoWindowGcode)

        self.ui.connectButton.clicked.connect(self.handle_connect)
        self.ui.resetButton.clicked.connect(self.handle_reset)
        self.ui.startButton.clicked.connect(self.handle_start)
        self.ui.emsButton.clicked.connect(self.handle_ems)
        self.ui.commandLine.returnPressed.connect(self.handle_command)
        self.ui.funcMode.clicked.connect(self.handle_funcMode)
        self.ui.drawMode.clicked.connect(self.handle_drawMode)
        self.ui.addObstacleButton.clicked.connect(self.handle_addObstacle)

        self.canvas = mainCanvas(self.gcode_processor, self.ui.centralwidget)
        self.ui.canvasLayout.addWidget(self.canvas)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)

    def handle_connect(self):
        """處理連接按鈕的點擊事件，嘗試連接到 ESP32。"""
        if self.esp32_serial.isConnected():
            self.gcode_processor.clearQueue()  # 清除 G-code 命令隊列，確保不會繼續等待已清除的命令回應
            self.gcode_processor.stop()  # 停止 G-code 處理器的執行緒，確保不會繼續處理命令
            self.esp32_serial.disconnect()
            self.infoWindow("已斷開與 ESP32 的連接。", mestype="info")
            self.ui.connectButton.setText("連線")
            self.ui.resetButton.setEnabled(False)
            self.ui.emsButton.setEnabled(False)
        else:
            if self.esp32_serial.connect():
                self.infoWindow("成功連接到 ESP32！", mestype="success")
                self.gcode_processor.start()  # 啟動 G-code 處理器的執行緒
                self.ui.connectButton.setText("斷開連線")
                self.ui.resetButton.setEnabled(True)
                self.ui.emsButton.setEnabled(True)
                self.gcode_processor.getPositionCommand()  # 連接成功後立即獲取當前位置
                self.canvas.update()
            else:
                self.infoWindow("無法連接到 ESP32，請檢查連接並重試。", mestype="error")

    def handle_reset(self):
        self.gcode_processor.reset()
        self.infoWindow("已發送重置命令 (G28) 給 ESP32。", mestype="info")
        self.gcode_processor.getPositionCommand()

    def handle_ems(self):
        self.gcode_processor.clearQueue()
        self.gcode_processor.ems()
        self.infoWindow("已清除 G-code 命令隊列。", mestype="info")

    def handle_command(self):
        command = self.ui.commandLine.text().strip()
        if command.startswith("clear"):
            self.info_lines.clear()
            self.line_colors.clear()
            self.ui.info.clear()
            self.ui.commandLine.clear()
            return
        if command:
            if self.esp32_serial.send(command + "\n"):
                self.infoWindow(f"已發送命令：{command}", mestype="success")
            else:
                self.infoWindow("無法發送命令，請先連接到 ESP32。", mestype="error")
            self.ui.commandLine.clear()
        else:
            self.infoWindow("請輸入一個命令。", mestype="error")

    def handle_start(self):
        # if not self.esp32_serial.isConnected():
        #     self.infoWindow("請先連接到 ESP32。", mestype="error")
        #     return
        self.startTimes += 1

        if self.startTimes == 1:
            paths = []
            if self.canvas.getDrawMode() == "func":
                paths = self.canvas.getFunctionPoints()
            elif self.canvas.getDrawMode() == "draw":
                paths = list(self.canvas.getStrokes())
            self.infoWindow(f"從畫布獲取的路徑點數量：{len(paths)}", mestype="info")
            obstacles = self.canvas.getObstacles()
            # 初始化路徑規劃器，這裡會自動處理單一 tuple 的障礙物
            planner = PathPlannerPro(paths, obstacles)
            self.planned_paths = planner.calculatePath()
            self.canvas.setDrawMode("plan")
            self.canvas.setPaths(self.planned_paths)
            self.infoWindow(
                f"規劃後的路徑點數量：{len(self.planned_paths)}", mestype="info")
            if len(self.planned_paths) >= 0:
                self.infoWindow(
                    "已完成路徑規劃，請再次點擊開始按鈕以執行 G-code 命令。", mestype="success")
                startPoint = self.planned_paths[0][0]
                self.gcode_processor.goTo(
                    startPoint.x, startPoint.y)  # 清除之前的命令，確保不會混入舊命令
        elif self.startTimes == 2:
            self.timer.start(100)
            for path in self.planned_paths:
                self.gcode_processor.goTo(path[0].x, path[0].y)
            self.infoWindow("已開始執行規劃路徑的 G-code 命令。", mestype="success")
            self.startTimes = 0

    def handle_funcMode(self):
        self.startTimes = 0
        dialog = SandPlotDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            xArray, yArray, colorList = dialog.getValues()
            self.canvas.setDrawMode("func")
            self.canvas.drawFunction(xArray, yArray, colorList)

    def handle_drawMode(self):
        self.startTimes = 0
        self.canvas.setDrawMode("draw")

    def handle_addObstacle(self):
        self.startTimes = 0
        self.canvas.addObstacle()

    def infoWindowGcode(self, message):
        self.infoWindow(message, mestype="info")

    def infoWindow(self, message, mestype="info"):
        """顯示信息窗口，接受一個字符串消息並在界面上顯示。"""
        self.info_lines.append(message)
        if mestype == "error":
            self.line_colors.append("#d93025")  # 紅色
        elif mestype == "success":
            self.line_colors.append("#00ff00")  # 綠色
        else:
            self.line_colors.append("#ffffff")  # 白色

        html_lines = []
        for i, line in enumerate(self.info_lines):
            color = self.line_colors[i % len(self.line_colors)]
            # 跳脫 HTML 特殊字元，避免 <、> 等符號破版
            safe_line = (
                line.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
            )
            html_lines.append(
                f'<span style="color:{color};">{safe_line}</span>')

        # 用 <br> 換行，組合成完整 HTML
        self.ui.info.setHtml("<br>".join(html_lines))
        scrollbar = self.ui.info.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())  # type: ignore # 自動滾動到最新消息

    def update_position(self):
        self.canvas.update()  # 強制畫布重繪以更新位置顯示
        if self.gcode_processor.isFinished():
            print("所有 G-code 命令已完成處理。")
            self.infoWindow("所有 G-code 命令已完成處理。", mestype="success")
            self.timer.stop()  # 停止定時器，因為已經完成所有命令的處理

    def closeApp(self):
        """關閉應用程式，確保所有資源被正確釋放。"""
        self.gcode_processor.stop()
        self.esp32_serial.disconnect()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainController()
    window.show()
    print("應用程式已啟動，等待用戶操作...")
    a = app.exec()
    print("應用程式正在關閉...")
    window.closeApp()
    sys.exit(a)

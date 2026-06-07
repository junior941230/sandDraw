from threading import Thread
from esp32serial import ESP32Serial
from PyQt6.QtCore import pyqtSignal, QObject
import time


class GCodeProcessor(QObject):
    text_received = pyqtSignal(str)

    def __init__(self, serial_interface: ESP32Serial, parent=None):
        super().__init__(parent)
        self.serial_interface = serial_interface
        self.running = False
        self.position = (180, 180)  # 用於存儲當前位置的變量
        self.queue = []  # 用於存儲待處理的 G-code 命令的隊列
        self.waiting = False  # 用於指示是否正在等待 ESP32 的回應
        self.moveMsg = ""  # 用於指示是否正在等待位置消息

    def start(self):
        self.running = True
        Thread(target=self.process_gcode).start()

    def stop(self):
        self.running = False

    def clearQueue(self):
        self.queue.clear()
        self.waiting = False  # 重置等待狀態，確保不會繼續等待已清除的命令回應

    def isFinished(self):
        return len(self.queue) == 0 and not self.waiting

    def ems(self):
        self.queue.append("M112")  # 將 M112 命令添加到隊列中以緊急停止機器

    def reset(self):
        self.queue.append("G28")  # 將 G28 命令添加到隊列中

    def getPositionCommand(self):
        self.queue.append("M114")  # 將 M114 命令添加到隊列中以獲取當前位置

    def goTo(self, x: float, y: float):
        x = x + 180
        y = y + 180
        command = f"G1 X{x:.2f} Y{y:.2f}"
        self.queue.append(command)

    def getPosition(self):
        return self.position

    def sendCommandFromQueue(self):
        if self.queue and not self.waiting:
            command = self.queue.pop(0)
            self.serial_interface.send(command + "\n")
            self.waiting = True
            if "G1" in command:
                self.moveMsg = command

    def decodeResponse(self, line):
        if line.startswith("ok"):
            self.waiting = False
            if len(self.moveMsg) > 0:
                X = self.moveMsg.split("X")[1].split()[0]
                Y = self.moveMsg.split("Y")[1].split()[0]
                self.position = (float(X), float(Y))
                self.moveMsg = ""
            return

        if "X=" in line and "Y=" in line:
            try:
                x = float(line.split("X=")[1].split()[0])
                y = float(line.split("Y=")[1].split()[0])
                self.position = (x, y)
            except (IndexError, ValueError):
                pass
            return

        self.text_received.emit(line)

    def process_gcode(self):
        while self.running:
            if not self.serial_interface.isConnected():
                time.sleep(0.1)
                continue

            if self.serial_interface.hasData():
                line = self.serial_interface.receive()
                if line:
                    self.decodeResponse(line)

            self.sendCommandFromQueue()

            # 避免 CPU 空轉
            time.sleep(0.001)

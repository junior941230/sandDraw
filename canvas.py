from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor
from gcode import GCodeProcessor
from planner import Point
import math
import numpy as np


class Stroke:
    """一筆畫 = 一條連續的線"""

    def __init__(self, color: QColor, width: int, eraser: bool = False):
        self.color = QColor(Qt.GlobalColor.white) if eraser else color
        self.width = width * 3 if eraser else width
        self.points: list[QPoint] = []


class mainCanvas(QWidget):
    def __init__(self, gcode_processor: GCodeProcessor, parent=None):
        super().__init__(parent)
        self.gcode_processor = gcode_processor
        self.setMinimumSize(800, 600)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self._current: Stroke | None = None  # 正在畫的這一筆

        # 筆刷設定
        self.pen_color = QColor("#000000")
        self.pen_width = 4
        self.isDrawing = False

        self.plotSize = 180
        self.plotCenter = (180, 180)
        self.scale = 2.5
        self.funcScale = 10.0

        self.drawMode = "draw"

        self.addingObstacle = False
        self.obstacles = []
        self.obstaclesStartPoint = None

        self.paths: list[Point] = []

    def setDrawMode(self, mode: str):
        self.drawMode = mode

    def getDotPosCanvas(self) -> QPoint:
        center = QPoint(self.width() // 2, self.height() // 2)
        pos = self.gcode_processor.getPosition()  # 獲取當前位置
        x = (pos[0] - self.plotCenter[0]) * self.scale + center.x()
        y = (pos[1] - self.plotCenter[1]) * self.scale + center.y()
        # print(
        #     f"當前位置: ({pos[0]:.2f}, {pos[1]:.2f}) -> 畫布坐標: ({x:.2f}, {y:.2f})")
        pos = QPoint(int(x), int(y))
        return pos

    # ── 繪製 ──────────────────────────────────────────
    def paintEvent(self, event):
        center = QPoint(self.width() // 2, self.height() // 2)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), Qt.GlobalColor.gray)

        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawEllipse(center, int(
            self.plotSize * self.scale), int(self.plotSize * self.scale))

        if self.drawMode == "draw":
            # 畫正在進行的筆跡
            if self._current:
                self._paint_stroke(painter, self._current)
        elif self.drawMode == "func":
            # 畫函數預覽
            if len(self._x) > 0 and len(self._y) > 0:
                lastPoint = QPoint(
                    int(self._x[0] * self.scale * self.funcScale) + center.x(), int(self._y[0] * self.scale * self.funcScale) + center.y())
                for i in range(len(self._x) - 1):
                    index = i + 1
                    color = self.colorList[index % len(self.colorList)]

                    pen = QPen(color, 1, Qt.PenStyle.SolidLine,
                               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    point = QPoint(
                        int(self._x[index] * self.scale * self.funcScale) + center.x(), int(self._y[index] * self.scale * self.funcScale) + center.y())
                    painter.drawLine(lastPoint, point)

                    if i == 0 or i == len(self._x) - 2:
                        pen.setWidth(10)
                    else:
                        pen.setWidth(5)
                    painter.setPen(pen)
                    painter.drawPoint(point)
                    lastPoint = point
        elif self.drawMode == "plan":
            if len(self.paths) > 0:
                lastPoint = QPoint(
                    int(self.paths[0].x * self.scale) + center.x(), int(self.paths[0].y * self.scale) + center.y())
                for i in range(1, len(self.paths)):
                    point = QPoint(
                        int(self.paths[i].x * self.scale) + center.x(), int(self.paths[i].y * self.scale) + center.y())
                    pen = QPen(Qt.GlobalColor.green, 2,
                               Qt.PenStyle.SolidLine,
                               Qt.PenCapStyle.RoundCap,
                               Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    painter.drawLine(lastPoint, point)
                    lastPoint = point

        if self.addingObstacle and self.obstaclesStartPoint:
            pen = QPen(Qt.GlobalColor.yellow, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            mousePos = self.mapFromGlobal(QCursor.pos())
            painter.drawRect(QRect(self.obstaclesStartPoint, mousePos))

        for obs in self.obstacles:
            pen = QPen(Qt.GlobalColor.yellow, 2)
            painter.setPen(pen)
            painter.drawRect(
                QRect(obs[0], obs[1], obs[2] - obs[0], obs[3] - obs[1]))

        drawPos = self.getDotPosCanvas()
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(drawPos, 5, 5)

    def _paint_stroke(self, painter: QPainter, stroke: Stroke):
        if len(stroke.points) < 2:
            return
        pen = QPen(stroke.color, stroke.width,
                   Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(1, len(stroke.points)):
            painter.drawLine(stroke.points[i - 1], stroke.points[i])

    # ── 滑鼠事件 ──────────────────────────────────────
    def mousePressEvent(self, event):
        mousePos = event.position().toPoint()
        if self.drawMode == "draw":
            drawPos = self.getDotPosCanvas()
            center = QPoint(self.width() // 2, self.height() // 2)
            if event.button() == Qt.MouseButton.LeftButton:
                # 如果點擊位置接近當前位置
                if abs(mousePos.x() - drawPos.x()) < 10 and abs(mousePos.y() - drawPos.y()) < 10:
                    if not self.isDrawing:
                        self._current = None  # 開始新的一筆
                    self._current = Stroke(
                        self.pen_color, self.pen_width)
                    self._current.points.append(mousePos)
                    self.isDrawing = True
                elif math.hypot(mousePos.x() - center.x(), mousePos.y() - center.y()) > self.plotSize * self.scale:
                    self._current = None  # 點擊位置太遠，忽略
                    self.update()
        if self.addingObstacle:
            self.obstaclesStartPoint = mousePos
            self.mousePos = mousePos
            self.update()  # 實時更新障礙物預覽

    def mouseMoveEvent(self, event):
        if self.drawMode == "draw":
            mousePos = event.position().toPoint()
            if self._current and (event.buttons() & Qt.MouseButton.LeftButton) and self.isDrawing:
                overLimit, mousePos = self.caculateLimitAndClamp(
                    mousePos.x(), mousePos.y(), (self.plotSize-5) * self.scale)
                mousePos = QPoint(int(mousePos[0]), int(mousePos[1]))
                self._current.points.append(mousePos)
                self.update()
        if self.addingObstacle and self.obstaclesStartPoint:
            self.update()  # 實時更新障礙物預覽

    def mouseReleaseEvent(self, event):
        if self.drawMode == "draw":
            if event.button() == Qt.MouseButton.LeftButton and self._current:
                self.isDrawing = False
        if self.addingObstacle:
            self.addingObstacle = False
            if self.obstaclesStartPoint:
                endPoint = event.position().toPoint()
                xMin = min(self.obstaclesStartPoint.x(), endPoint.x())
                yMin = min(self.obstaclesStartPoint.y(), endPoint.y())
                xMax = max(self.obstaclesStartPoint.x(), endPoint.x())
                yMax = max(self.obstaclesStartPoint.y(), endPoint.y())
                obs = (xMin, yMin, xMax, yMax)
                self.obstacles.append(obs)
                self.setCursor(Qt.CursorShape.CrossCursor)
                self.update()
        else:
            if event.button() == Qt.MouseButton.RightButton:
                index = self.isPointInObstacle(event.position().toPoint())
                if index != -1:
                    # 右鍵點擊障礙物，移除該障礙物
                    del self.obstacles[index]
                    self.update()

    def wheelEvent(self, event):
        if self.drawMode == "draw":
            pass
        elif self.drawMode == "func":
            delta = event.angleDelta().y() / 120  # 每格 120
            self.scaleCaculate(delta)
            self.update()

    # ── 功能 ──────────────────────────────────────────
    def isPointInObstacle(self, point: QPoint) -> int:
        for i in range(len(self.obstacles)):
            obs = self.obstacles[i]
            p1 = QPoint(obs[0], obs[1])
            p2 = QPoint(obs[2], obs[3])
            rect = QRect(p1, p2)
            if rect.contains(point):
                return i
        return -1

    def getDrawMode(self):
        return self.drawMode

    def getFunctionPoints(self):
        if self.drawMode == "func":
            paths = []
            for i in range(len(self._x)):
                p = Point(self._x[i] * self.funcScale,
                          self._y[i] * self.funcScale)
                paths.append(p)
            return paths
        else:
            return []

    def getStrokes(self):
        if self._current:
            for point in self._current.points:
                # 將畫布坐標轉換回 G-code 坐標
                center = QPoint(self.width() // 2, self.height() // 2)
                gcode_x = (point.x() - center.x()) / self.scale
                gcode_y = (point.y() - center.y()) / self.scale
                p = Point(gcode_x, gcode_y)
                yield p

    def getObstacles(self):
        obstacles = []
        for obs in self.obstacles:
            center = QPoint(self.width() // 2, self.height() // 2)
            gcode_x_min = (obs[0] - center.x()) / self.scale
            gcode_y_min = (obs[1] - center.y()) / self.scale
            gcode_x_max = (obs[2] - center.x()) / self.scale
            gcode_y_max = (obs[3] - center.y()) / self.scale
            obstacles.append((gcode_x_min, gcode_y_min,
                              gcode_x_max, gcode_y_max))
        return obstacles

    def caculateLimitAndClamp(self, x, y, maxRadius):
        cx, cy = self.width() // 2, self.height() // 2

        dx = x - cx
        dy = y - cy
        radius = math.hypot(dx, dy)

        if radius > maxRadius:
            # 縮放到剛好貼邊
            ratio = maxRadius / radius
            x = cx + dx * ratio
            y = cy + dy * ratio
            return True, (x, y)

        return False, (x, y)

    def scaleCaculate(self, delta):
        # 用 numpy 向量化計算所有點的半徑，找最大值
        radii = np.hypot(self._x, self._y)  # shape: (N,)
        maxRadius = float(np.max(radii)) if len(radii) > 0 else 0

        if maxRadius == 0:
            return

        # 目前縮放後的最大半徑
        self.funcScale += delta * 10
        scaledMax = maxRadius * self.funcScale
        plotLimit = self.plotSize - 5
        if scaledMax > plotLimit:
            # 超出邊界時，強制縮回剛好貼邊
            self.funcScale = plotLimit / maxRadius
        elif scaledMax < -plotLimit:
            # 超出負邊界時，強制縮回剛好貼邊
            self.funcScale = -plotLimit / maxRadius

    def drawFunction(self, x: np.ndarray, y: np.ndarray, colorList: list[QColor]):
        # 將函數值轉換為畫布坐標
        self._x = x
        self._y = y
        self.colorList = colorList

        # 繪製函數曲線
        self.update()

    def addObstacle(self):
        self.addingObstacle = True
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def setPaths(self, paths):
        self.paths = paths
        self.update()


class previewCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._x = []
        self._y = []
        self.colorList = []

    def paintEvent(self, event):
        h = self.height()
        w = self.width()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), Qt.GlobalColor.gray)
        # 繪製預覽點
        if len(self._x) > 0 and len(self._y) > 0:
            lastPoint = QPoint(
                int(self._x[0]) + w // 2, int(self._y[0]) + h // 2)
            for i in range(len(self._x) - 1):
                index = i + 1
                color = self.colorList[i % len(self.colorList)]
                pen = QPen(color, 1, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                point = QPoint(int(self._x[index]) + w //
                               2, int(self._y[index]) + h // 2)
                painter.drawLine(lastPoint, point)

                pen.setWidth(5)
                painter.setPen(pen)
                painter.drawPoint(point)
                lastPoint = point
                self.colorList.append(color)

    def colorPreview(self, index, total):
        # hue 從 0.0(紅) 到 0.85(紫)，避免繞回紅色
        hue = index / total * 0.85
        return QColor.fromHsvF(hue, 1.0, 1.0)

    def _buildColorList(self, total: int):
        """資料更新時預先計算所有顏色"""
        self.colorList = [self.colorPreview(i, total) for i in range(total)]

    def autoScale(self, x: np.ndarray, y: np.ndarray):
        max_val = max(max(x), max(y))
        min_val = min(min(x), min(y))
        scale = min(self.width() / (max_val - min_val),
                    self.height() / (max_val - min_val)) * 0.9
        return x * scale, y * scale

    def drawPreview(self, x: np.ndarray, y: np.ndarray):
        self._x, self._y = self.autoScale(x, y)
        self._buildColorList(len(self._x))
        self.update()
        return self.colorList

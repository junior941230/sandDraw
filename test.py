import math
import cv2
import numpy as np


class RobotArm:
    def __init__(self, x, y, L):
        self.L = L
        self.currentX = x
        self.currentY = y
        self.prevDeltaAngle = 0.0
        result = self.inverse_kinematics(x, y, L)
        self.angleM0, self.angleM1 = self.findNearestAngle(0.0, result)

    def fixAngle(self, angle):
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        return angle

    def findNearestAngle(self, current, IKresult):
        angle1 = IKresult["angle1U"]
        angle2 = IKresult["angle1D"]

        diff1 = abs(current - angle1)
        diff2 = abs(current - angle2)
        diff1 = min(diff1, 360 - diff1)
        diff2 = min(diff2, 360 - diff2)
        if diff1 < diff2:
            return IKresult["angle1U"], IKresult["angle2U"]
        else:
            return IKresult["angle1D"], IKresult["angle2D"]

    def inverse_kinematics(self, x: float, y: float, L: float):

        # 逆向運動學計算
        cosVal = (x**2 + y**2 - L**2 - L**2) / (2 * L**2)

        if cosVal < -1.0 or cosVal > 1.0:
            print("目標位置超出機械臂工作範圍！")
            valid = False
            return {"angle1U": 0.0, "angle2U": 0.0, "angle1D": 0.0, "angle2D": 0.0, "valid": valid}

        if abs(x) * abs(y) < 0.0001:
            print("目標位置過於接近坐標軸，可能導致不穩定的運動！")
            valid = False
            return {"angle1U": 0.0, "angle2U": 0.0, "angle1D": 0.0, "angle2D": 0.0, "valid": valid}

        theta2U = math.acos(cosVal)
        theta2D = -math.acos(cosVal)

        alpha = math.atan2(y, x)
        betaU = math.atan2(L * math.sin(theta2U), L + L * math.cos(theta2U))
        betaD = math.atan2(L * math.sin(theta2D), L + L * math.cos(theta2D))

        theta1U = alpha - betaU
        theta1D = alpha - betaD

        angle1U = math.degrees(theta1U)
        angle2U = math.degrees(theta2U + theta1U)
        angle1D = math.degrees(theta1D)
        angle2D = math.degrees(theta2D + theta1D)
        valid = True

        return {"angle1U": self.fixAngle(angle1U), "angle2U": self.fixAngle(angle2U), "angle1D": self.fixAngle(angle1D), "angle2D": self.fixAngle(angle2D), "valid": valid}

    def pathPlanner(self, tx, ty):
        dist = math.sqrt((tx - self.currentX) ** 2 + (ty - self.currentY) ** 2)

        seg = max(int(dist), 10)  # 固定密度，每10單位距離一個插值點，至少10段

        anglePath = []
        i = 1
        ratio = 1.0
        lastX = self.currentX
        lastY = self.currentY
        while True:
            x = self.currentX + (tx - self.currentX) * (i / seg)
            y = self.currentY + (ty - self.currentY) * (i / seg)
            result = self.inverse_kinematics(x, y, self.L)
            if result["valid"]:
                angle1, angle2 = self.findNearestAngle(self.angleM0, result)

                deltaAngle = abs(angle1 - self.angleM0)
                if abs(self.prevDeltaAngle - deltaAngle) > 0.05 and self.prevDeltaAngle != 0:
                    ratio = abs(self.prevDeltaAngle - deltaAngle) / 0.3
                    if ratio > 1.0 and ratio < 1000.0:
                        print(f"調整插值密度，當前密度: {ratio:.2f}倍")
                        print(
                            f"前一角度變化: {self.prevDeltaAngle:.2f}, 當前角度變化: {deltaAngle:.2f}")
                        for i2 in range(1, int(ratio)):
                            x2 = lastX + (x - lastX) * (i2 / ratio)
                            y2 = lastY + (y - lastY) * (i2 / ratio)
                            result2 = self.inverse_kinematics(x2, y2, self.L)
                            if result2["valid"]:
                                angle1_2, angle2_2 = self.findNearestAngle(
                                    self.angleM0, result2)
                                anglePath.append((angle1_2, angle2_2, ratio))

                anglePath.append((angle1, angle2, ratio))
                self.angleM0 = angle1
                self.angleM1 = angle2
                self.prevDeltaAngle = deltaAngle
                lastX = x
                lastY = y
            i += 1
            if i >= seg:
                break

        self.currentX = tx
        self.currentY = ty
        print(
            f"目標位置: ({tx}, {ty}), 最終角度: ({self.angleM0:.2f}, {self.angleM1:.2f}), 總步數: {len(anglePath)}")
        return anglePath


def animation(anglePath):
    img = np.zeros((1000, 1000, 3), dtype=np.uint8)
    scale = 3
    i = 0
    pause = False
    while True:
        angle1, angle2, ratio = anglePath[i]
        print(
            f"Step {i+1}/{len(anglePath)}: Angle1={angle1:.2f}, Angle2={angle2:.2f}, Density={ratio:.2f}x")
        img.fill(0)
        # 計算機械臂末端位置
        x1 = int(90 * math.cos(math.radians(angle1)) * scale + 500)
        y1 = int(90 * math.sin(math.radians(angle1)) * scale + 500)
        x2 = int(x1 + 90 * math.cos(math.radians(angle2)) * scale)
        y2 = int(y1 + 90 * math.sin(math.radians(angle2)) * scale)

        x1 = 1000 - x1  # 水平翻轉q
        x2 = 1000 - x2  # 水平翻轉
        y1 = 1000 - y1  # 水平翻轉q
        y2 = 1000 - y2  # 水平翻轉

        # 繪製機械臂
        cv2.line(img, (500, 500), (x1, y1), (255, 0, 0), 5)
        cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 5)
        cv2.putText(img, f"step: {i+1}/{len(anglePath)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Angle1: {angle1:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Angle2: {angle2:.2f}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Density: {ratio:.2f}x", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.circle(img, (600, 100), 5, (0, 0, 255), -1)  # 繪製末端位置
        cv2.imshow("Robot Arm Simulation", img)
        # 左右箭頭
        key = cv2.waitKey(10)
        if key == ord('q'):  # 按下ESC鍵退出
            break
        if key == ord('d'):
            i = max(0, i - 1)
        if key == ord('a'):
            i = min(len(anglePath) - 1, i + 1)
        if key == ord(' '):
            pause = not pause
        if not pause:
            i += 1
        if i >= len(anglePath):
            break


if __name__ == "__main__":
    robot_arm = RobotArm(x=26.36, y=63.64, L=90.0)
    anglePath = robot_arm.pathPlanner(50, 50)
    animation(anglePath)
    anglePath = robot_arm.pathPlanner(50, -50)
    animation(anglePath)
    anglePath = robot_arm.pathPlanner(-50, -50)
    animation(anglePath)
    anglePath = robot_arm.pathPlanner(-50, 50)
    animation(anglePath)
    anglePath = robot_arm.pathPlanner(90, -90)
    animation(anglePath)

    cv2.destroyAllWindows()

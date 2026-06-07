import math


class Point:
    """簡單的 2D 點，方便運算"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)


class PathPlanner:
    MARGIN = 5          # 安全邊距（離障礙物角點的偏移量）
    MAX_ITER = 20       # 最大迭代次數，防止無限迴圈

    def __init__(self, paths, obstacles):
        """
        paths     : List[Point]         路徑點列表
        obstacles : List[tuple]         障礙物列表，每個為 (xmin, ymin, xmax, ymax)
                    也接受單一 tuple，會自動包成 list
        """
        self.paths = paths
        # 統一處理成 list，方便支援多障礙物
        if isinstance(obstacles, tuple) and isinstance(obstacles[0], (int, float)):
            self.obstacles = [obstacles]
        else:
            self.obstacles = list(obstacles)

    # ─────────────────────────────────────────
    # 基礎幾何工具
    # ─────────────────────────────────────────

    def distance(self, p1, p2):
        """兩點距離"""
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    def path_length(self, points):
        """計算一串點的總路徑長度"""
        return sum(self.distance(points[i], points[i + 1])
                   for i in range(len(points) - 1))

    def cross_product(self, o, a, b):
        """
        向量 OA × OB 的 z 分量
        > 0 → b 在 OA 左側
        < 0 → b 在 OA 右側
        """
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    def point_in_rect(self, p, rect):
        """判斷點是否在矩形內（含邊界）"""
        xmin, ymin, xmax, ymax = rect
        return xmin <= p.x <= xmax and ymin <= p.y <= ymax

    # ─────────────────────────────────────────
    # 線段與矩形相交偵測（Liang-Barsky）
    # ─────────────────────────────────────────

    def segmentIntersectRect(self, p1, p2, rect):
        xmin, ymin, xmax, ymax = rect

        dx = p2.x - p1.x
        dy = p2.y - p1.y

        p = [-dx, dx, -dy, dy]
        q = [p1.x - xmin, xmax - p1.x, p1.y - ymin, ymax - p1.y]

        t_min, t_max = 0.0, 1.0

        for pi, qi in zip(p, q):
            if pi == 0:
                if qi < 0:
                    return False
            elif pi < 0:
                t_min = max(t_min, qi / pi)
            else:
                t_max = min(t_max, qi / pi)

        return t_min <= t_max

    # ─────────────────────────────────────────
    # 碰撞群組合併
    # ─────────────────────────────────────────

    def group_collisions(self, collisions):
        if not collisions:
            return []

        groups = []
        start = collisions[0]
        end = collisions[0]

        for c in collisions[1:]:
            if c == end + 1:
                end = c
            else:
                groups.append((start, end))
                start = end = c

        groups.append((start, end))
        return groups

    # ─────────────────────────────────────────
    # 繞行角點計算
    # ─────────────────────────────────────────

    def get_corners(self, rect):
        """
        取得矩形四個角點（含安全邊距向外推）
        回傳順序：左上、右上、右下、左下
        """
        xmin, ymin, xmax, ymax = rect
        m = self.MARGIN
        return [
            Point(xmin - m, ymax + m),  # C1 左上
            Point(xmax + m, ymax + m),  # C2 右上
            Point(xmax + m, ymin - m),  # C3 右下
            Point(xmin - m, ymin - m),  # C4 左下
        ]

    def get_left_detour(self, from_point, to_point, rect):
        """
        繞左側的角點序列
        用叉積判斷哪些角點在路徑左側，依序排列
        """
        corners = self.get_corners(rect)
        # 判斷每個角點是否在 from→to 的左側（cross > 0）
        left = [c for c in corners
                if self.cross_product(from_point, to_point, c) > 0]

        # 依照「從 from_point 出發的角度」排序，確保路徑順序正確
        left.sort(key=lambda c: math.atan2(c.y - from_point.y,
                                           c.x - from_point.x))
        return left

    def get_right_detour(self, from_point, to_point, rect):
        """
        繞右側的角點序列
        用叉積判斷哪些角點在路徑右側，依序排列
        """
        corners = self.get_corners(rect)
        right = [c for c in corners
                 if self.cross_product(from_point, to_point, c) < 0]

        # 右側角點排序方向相反
        right.sort(key=lambda c: math.atan2(c.y - from_point.y,
                                            c.x - from_point.x),
                   reverse=True)
        return right

    # ─────────────────────────────────────────
    # 解決單一碰撞群組
    # ─────────────────────────────────────────

    def resolveCollisionGroup(self, path, group, obstacle):
        start_idx, end_idx = group

        # 安全退後：如果 from_point 本身在障礙物內，往前退
        while start_idx > 0 and self.point_in_rect(path[start_idx], obstacle):
            start_idx -= 1

        # 安全前進：如果 to_point 本身在障礙物內，往後推
        while end_idx + 1 < len(path) - 1 and self.point_in_rect(path[end_idx + 1], obstacle):
            end_idx += 1

        from_point = path[start_idx]
        to_point = path[end_idx + 1]

        left_corners = self.get_left_detour(from_point, to_point, obstacle)
        right_corners = self.get_right_detour(from_point, to_point, obstacle)

        left_len = self.path_length([from_point] + left_corners + [to_point])
        right_len = self.path_length([from_point] + right_corners + [to_point])

        best_detour = left_corners if left_len < right_len else right_corners

        new_path = (
            path[:start_idx + 1]
            + best_detour
            + path[end_idx + 1:]
        )
        return new_path

    # ─────────────────────────────────────────
    # 對單一障礙物處理整條路徑
    # ─────────────────────────────────────────

    def resolveObstacle(self, path, obstacle):
        """對一個障礙物，迭代處理直到路徑完全無碰撞"""
        for _ in range(self.MAX_ITER):
            collisions = [
                i for i in range(len(path) - 1)
                if self.segmentIntersectRect(path[i], path[i + 1], obstacle)
            ]

            if not collisions:
                break  # 無碰撞，完成

            groups = self.group_collisions(collisions)

            # 從後往前處理，避免 index 位移
            for group in reversed(groups):
                path = self.resolveCollisionGroup(path, group, obstacle)

        return path

    # ─────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────

    def calculatePath(self):
        """
        對所有障礙物依序處理，回傳最終無碰撞路徑
        """
        path = self.paths[:]  # 複製，不修改原始資料

        for obstacle in self.obstacles:
            path = self.resolveObstacle(path, obstacle)

        return path


class PathPlannerPro:
    MARGIN = 5          # 安全邊距（離障礙物角點的偏移量）
    MAX_ITER = 20       # 最大迭代次數，防止無限迴圈

    def __init__(self, paths, obstacles):
        """
        paths     : List[Point]         路徑點列表
        obstacles : List[tuple]         障礙物列表，每個為 (xmin, ymin, xmax, ymax)
                    也接受單一 tuple，會自動包成 list
        """
        self.paths = paths
        # 統一處理成 list，方便支援多障礙物
        if isinstance(obstacles, tuple) and isinstance(obstacles[0], (int, float)):
            self.obstacles = [obstacles]
        else:
            self.obstacles = list(obstacles)

    # ─────────────────────────────────────────
    # 基礎幾何工具
    # ─────────────────────────────────────────

    def distance(self, p1, p2):
        """兩點距離"""
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    def path_length(self, points):
        """計算一串點的總路徑長度"""
        return sum(self.distance(points[i], points[i + 1])
                   for i in range(len(points) - 1))

    def cross_product(self, o, a, b):
        """
        向量 OA × OB 的 z 分量
        > 0 → b 在 OA 左側
        < 0 → b 在 OA 右側
        """
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    def pointInRects(self, p, rects):
        """判斷點是否在矩形內（含邊界）"""
        for i in range(len(rects)):
            xmin, ymin, xmax, ymax = rects[i]
            if xmin <= p.x <= xmax and ymin <= p.y <= ymax:
                return True, i  # 回傳碰撞狀態與碰撞的障礙物編號
        return False, None

    # ─────────────────────────────────────────
    # 線段與矩形相交偵測（Liang-Barsky）
    # ─────────────────────────────────────────

    def segmentIntersectRect(self, p1, p2, rect):
        xmin, ymin, xmax, ymax = rect

        dx = p2.x - p1.x
        dy = p2.y - p1.y

        p = [-dx, dx, -dy, dy]
        q = [p1.x - xmin, xmax - p1.x, p1.y - ymin, ymax - p1.y]

        t_min, t_max = 0.0, 1.0

        for pi, qi in zip(p, q):
            if pi == 0:
                if qi < 0:
                    return False
            elif pi < 0:
                t_min = max(t_min, qi / pi)
            else:
                t_max = min(t_max, qi / pi)

        return t_min <= t_max

    # ─────────────────────────────────────────
    # 繞行角點計算
    # ─────────────────────────────────────────

    def get_corners(self, rect):
        """
        取得矩形四個角點（含安全邊距向外推）
        回傳順序：左上、右上、右下、左下
        """
        xmin, ymin, xmax, ymax = rect
        points = [Point(xmin, ymax),  # C1 左上
                  Point(xmax, ymax),  # C2 右上
                  Point(xmax, ymin),  # C3 右下
                  Point(xmin, ymin)  # C4 左下
                  ]
        return points

    def get_left_detour(self, from_point, to_point, rect):
        """
        繞左側的角點序列
        用叉積判斷哪些角點在路徑左側，依序排列
        """
        corners = self.get_corners(rect)
        # 判斷每個角點是否在 from→to 的左側（cross > 0）
        left = [c for c in corners
                if self.cross_product(from_point, to_point, c) > 0]

        # 依照「從 from_point 出發的角度」排序，確保路徑順序正確
        left.sort(key=lambda c: math.atan2(c.y - from_point.y,
                                           c.x - from_point.x))
        left.reverse()  # 左側繞行點順序反轉，確保從 from_point 開始的路徑順序正確
        return left

    def get_right_detour(self, from_point, to_point, rect):
        """
        繞右側的角點序列
        用叉積判斷哪些角點在路徑右側，依序排列
        """
        corners = self.get_corners(rect)
        right = [c for c in corners
                 if self.cross_product(from_point, to_point, c) < 0]

        # 右側角點排序方向相反
        right.sort(key=lambda c: math.atan2(c.y - from_point.y,
                                            c.x - from_point.x),
                   reverse=True)
        right.reverse()  # 右側繞行點順序反轉，確保從 from_point 開始的路徑順序正確
        return right

    # ─────────────────────────────────────────
    # 找出最佳繞行方案
    # ─────────────────────────────────────────

    def getBestPath(self, from_point, to_point, obstacle):
        leftCorner = self.get_left_detour(from_point, to_point, obstacle)
        rightCorner = self.get_right_detour(from_point, to_point, obstacle)
        left_len = self.path_length([from_point] + leftCorner + [to_point])
        right_len = self.path_length([from_point] + rightCorner + [to_point])
        best_detour = leftCorner if left_len < right_len else rightCorner
        print(f"左側繞行點: {leftCorner}, 右側繞行點: {rightCorner}")
        return best_detour

    # ─────────────────────────────────────────
    # 膨脹障礙物（將障礙物擴大 MARGIN，簡化繞行邏輯）
    # ─────────────────────────────────────────

    def dilateObstacle(self, rect):
        xmin, ymin, xmax, ymax = rect
        m = self.MARGIN
        return (xmin - m, ymin - m, xmax + m, ymax + m)

    # ─────────────────────────────────────────
    # 對單一障礙物處理整條路徑
    # ─────────────────────────────────────────

    def resolvePath(self, paths, obstacles):
        """對一個障礙物，迭代處理直到路徑完全無碰撞"""
        isLastCollision = False
        newPaths = []
        for point in paths:
            collisions, obsNum = self.pointInRects(
                point, obstacles)  # 先檢查點是否在任何障礙物內，若不在則無需處理
            if collisions and not isLastCollision:
                newPaths[-1] = (newPaths[-1][0], True,
                                obsNum)  # 碰撞開始，標記上一點
            if not collisions:
                newPaths.append((point, False, obsNum))
            isLastCollision = collisions

        resultPaths = []
        for i in range(len(newPaths) - 1):
            resultPaths.append(newPaths[i])  # 加入當前點
            if newPaths[i][1]:  # 如果當前點是標記點
                from_point = newPaths[i][0]  # 從上一個非碰撞點出發
                to_point = newPaths[i + 1][0]    # 到下一個非碰撞點
                obstacle = obstacles[newPaths[i][2]]  # 碰撞的障礙物
                corners = self.getBestPath(from_point, to_point, obstacle)
                resultPaths.extend([(p, True, None)
                                   for p in corners])  # 加入繞行點，這裡不標記為碰撞點
        return resultPaths

    # ─────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────

    def calculatePath(self):
        """
        對所有路徑點依序處理，回傳最終無碰撞路徑
        """
        # 先膨脹障礙物，簡化繞行邏輯
        dilatedObstacles = []
        for obstacle in self.obstacles:
            dilated = self.dilateObstacle(obstacle)
            dilatedObstacles.append(dilated)

        paths = self.resolvePath(
            self.paths, dilatedObstacles)  # 目前只處理第一個障礙物，後續可擴展

        return paths


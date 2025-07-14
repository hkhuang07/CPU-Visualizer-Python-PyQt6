# src/gui_elements.py

from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtGui import QColor, QBrush, QPen
from PyQt6.QtCore import QPropertyAnimation, QPointF, QEasingCurve, Qt, QObject, QSequentialAnimationGroup

class AnimatableEllipseItem(QGraphicsEllipseItem):
    """
    Một đối tượng hình elip có thể được gán hiệu ứng.
    Chỉ kế thừa từ QGraphicsEllipseItem để tránh các lỗi phức tạp.
    """
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)


class SignalAnimator(QObject):
    """
    Quản lý các hiệu ứng di chuyển tín hiệu trên sơ đồ.
    Sử dụng một đối tượng QObject phụ để làm mục tiêu animation.
    """
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.animation_group = QSequentialAnimationGroup()
        self.active_animations = []

        # Thêm một list để lưu trữ các item cần dọn dẹp
        self.items_to_clean_up = []
        
        # Sửa: Kết nối tín hiệu finished của QSequentialAnimationGroup
        self.animation_group.finished.connect(self._on_group_finished)

    def animate_path(self, path_points, color=Qt.GlobalColor.blue, dot_size=8, duration=500):
        if not path_points or len(path_points) < 2:
            print("Error: Invalid animation path (requires at least 2 points).")
            return

        # Tạo đối tượng hình elip để hiển thị trên màn hình.
        dot = AnimatableEllipseItem(path_points[0].x() - dot_size / 2, path_points[0].y() - dot_size / 2, dot_size, dot_size)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.GlobalColor.black, 0.5))
        dot.setZValue(100)
        self.scene.addItem(dot)
        self.items_to_clean_up.append(dot)

        # Tạo một đối tượng QObject "rỗng" để làm mục tiêu cho animation.
        dummy_target = QObject()
        dummy_target.setProperty(b"pos", QPointF(0, 0))
        
        # Khởi tạo animation trên đối tượng "rỗng" này.
        animation = QPropertyAnimation(dummy_target, b"pos", self)
        animation.setDuration(duration)
        
        # Kết nối sự thay đổi vị trí của animation với vị trí của hình elip.
        # Sử dụng weak reference để tránh reference cycle
        animation.valueChanged.connect(lambda p: dot.setPos(p - QPointF(dot_size / 2, dot_size / 2)))
        
        # Tải các điểm đường đi vào animation
        for i, point in enumerate(path_points):
            progress = i / (len(path_points) - 1.0)
            animation.setKeyValueAt(progress, point)

        animation.setEasingCurve(QEasingCurve.Type.Linear)
        
        # Kết nối tín hiệu finished của animation để dọn dẹp
        animation.finished.connect(lambda: self._cleanup_single_animation(dot, animation))
        
        self.active_animations.append(animation)
        self.animation_group.addAnimation(animation)
        
        return animation

    def _cleanup_single_animation(self, dot_item, animation_object):
        """Dọn dẹp một animation và item tương ứng sau khi nó kết thúc."""
        if dot_item in self.scene.items():
            self.scene.removeItem(dot_item)
            
        if dot_item in self.items_to_clean_up:
            self.items_to_clean_up.remove(dot_item)

        if animation_object in self.active_animations:
            self.active_animations.remove(animation_object)
        
        # Note: Không gọi animation_object.deleteLater() ở đây, để group quản lý.
    
    def _on_group_finished(self):
        """Dọn dẹp sau khi toàn bộ nhóm animation đã kết thúc."""
        self.clear_animations()

    def start_animation(self):
        self.animation_group.start()
        
    def clear_animations(self):
        """Dừng tất cả animation và dọn dẹp các item trên scene."""
        self.animation_group.stop()
        self.animation_group.clear()
        
        # Sửa: Vòng lặp an toàn hơn để dọn dẹp các item còn lại
        for item in list(self.items_to_clean_up):
            if item in self.scene.items():
                self.scene.removeItem(item)
        
        self.items_to_clean_up.clear()
        self.active_animations.clear()
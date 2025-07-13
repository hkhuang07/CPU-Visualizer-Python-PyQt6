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

        # Tạo một đối tượng QObject "rỗng" để làm mục tiêu cho animation.
        dummy_target = QObject(self)
        dummy_target.setProperty(b"pos", QPointF(0, 0))
        
        # Khởi tạo animation trên đối tượng "rỗng" này.
        animation = QPropertyAnimation(dummy_target, b"pos", self)
        animation.setDuration(duration)
        
        # Kết nối sự thay đổi vị trí của animation với vị trí của hình elip.
        animation.valueChanged.connect(lambda p: dot.setPos(p - QPointF(dot_size / 2, dot_size / 2)))
        
        if len(path_points) > 1:
            for i, point in enumerate(path_points):
                progress = i / (len(path_points) - 1.0)
                animation.setKeyValueAt(progress, point)
        else:
            animation.setStartValue(path_points[0])
            animation.setEndValue(path_points[0])

        animation.setEasingCurve(QEasingCurve.Type.Linear)
        animation.finished.connect(lambda: self._cleanup_animation(dot, animation))
        
        self.active_animations.append(animation)
        self.animation_group.addAnimation(animation)
        
        return animation

    def _cleanup_animation(self, dot_item, animation_object):
        self.scene.removeItem(dot_item)
        if animation_object in self.active_animations:
            self.active_animations.remove(animation_object)
        
        self.animation_group.removeAnimation(animation_object)
        
        animation_object.deleteLater()
        # Đã xóa dòng "dot_item.deleteLater()" gây lỗi
    
    def start_animation(self):
        self.animation_group.start()
        
    def clear_animations(self):
        for anim in list(self.active_animations):
            anim.stop()
            
        for item in self.scene.items():
            if isinstance(item, AnimatableEllipseItem):
                self.scene.removeItem(item)
                item.deleteLater()
        self.active_animations.clear()
        self.animation_group.clear()
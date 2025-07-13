# src/gui_elements.py

from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsObject
from PyQt6.QtGui import QColor, QBrush, QPen
from PyQt6.QtCore import QPropertyAnimation, QPointF, QEasingCurve, Qt, QObject, pyqtProperty

class AnimatableEllipseItem(QGraphicsObject, QGraphicsEllipseItem):
    def __init__(self, x, y, w, h):
        super(QGraphicsObject, self).__init__()
        QGraphicsEllipseItem.__init__(self, x, y, w, h)
        
    def _get_pos(self):
        return self.pos()

    def _set_pos(self, pos: QPointF):
        self.setPos(pos)

    pos = pyqtProperty(QPointF, _get_pos, _set_pos)


class SignalAnimator(QObject):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.active_animations = []

    def animate_path(self, path_points, color=Qt.GlobalColor.blue, dot_size=8, duration=500):
        if not path_points or len(path_points) < 2:
            print("Error: Invalid animation path (requires at least 2 points).")
            return

        dot = AnimatableEllipseItem(path_points[0].x(), path_points[0].y(), dot_size, dot_size)
        
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.GlobalColor.black, 0.5))
        dot.setZValue(100)

        self.scene.addItem(dot)

        animation = QPropertyAnimation(dot, b"pos", self)
        animation.setDuration(duration)
        
        if len(path_points) > 1:
            # Sửa đổi: Sử dụng QPropertyAnimation với các key frame
            for i, point in enumerate(path_points):
                progress = i / (len(path_points) - 1.0)
                animation.setKeyValueAt(progress, point)
        else:
            animation.setStartValue(path_points[0])
            animation.setEndValue(path_points[0])

        animation.setEasingCurve(QEasingCurve.Type.Linear)

        animation.finished.connect(lambda: self._cleanup_animation(dot, animation))
        
        self.active_animations.append(animation)
        animation.start()
        
        return animation

    def _cleanup_animation(self, dot_item, animation_object):
        self.scene.removeItem(dot_item)
        if animation_object in self.active_animations:
            self.active_animations.remove(animation_object)
        animation_object.deleteLater()
        dot_item.deleteLater()
    
    def clear_animations(self):
        for anim in list(self.active_animations):
            anim.stop()
        
        # Dọn dẹp tất cả các dot item đang active
        for item in self.scene.items():
            if isinstance(item, AnimatableEllipseItem):
                self.scene.removeItem(item)
                item.deleteLater()
        self.active_animations.clear()
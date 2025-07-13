import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QGraphicsView,
    QGraphicsScene, QComboBox, QLineEdit, QFormLayout, QMessageBox, QGraphicsRectItem
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QTimer, QPointF, QPropertyAnimation, QRectF

from .cpu_core import CPU
from .gui_elements import SignalAnimator

# Định nghĩa TỌA ĐỘ cho các thành phần trên sơ đồ (BẠN CẦN THAY ĐỔI THEO HÌNH CỦA BẠN!)
# Các tọa độ này là giả định, bạn phải thay đổi chúng dựa trên file ảnh của bạn.
# Nên có khoảng cách đủ lớn giữa các thành phần để đặt giá trị
DIAGRAM_COORDS = {
    # Các tọa độ này cần được điều chỉnh lại SAU KHI bạn quyết định tỷ lệ phóng to ảnh.
    # Vì nếu ảnh lớn hơn, các vị trí cũ sẽ bị lệch.
    # Nên dùng tỷ lệ với kích thước mới của ảnh.
    'IAR_TEXT_POS': QPointF(420, 130),
    'IR_OPCODE_TEXT_POS': QPointF(570, 120),
    'IR_ADDRDATA_TEXT_POS': QPointF(570, 150),
    'REG_A_TEXT_POS': QPointF(170, 70),
    'REG_B_TEXT_POS': QPointF(370, 70),
    'ALU_OUT_TEXT_POS': QPointF(180, 230),
    'FLAG_Z_POS': QPointF(470, 200),
    'FLAG_N_POS': QPointF(520, 200),
    'FLAG_O_POS': QPointF(570, 200),

    'RAM_CELL_POSITIONS': {
        0: QPointF(730, 55 + 17 * 0),
        1: QPointF(730, 55 + 17 * 1),
        2: QPointF(730, 55 + 17 * 2),
        3: QPointF(730, 55 + 17 * 3),
        4: QPointF(730, 55 + 17 * 4),
        5: QPointF(730, 55 + 17 * 5),
        6: QPointF(730, 55 + 17 * 6),
        7: QPointF(730, 55 + 17 * 7),
        8: QPointF(730, 55 + 17 * 8),
        9: QPointF(730, 55 + 17 * 9),
        10: QPointF(730, 55 + 17 * 10),
        11: QPointF(730, 55 + 17 * 11),
        12: QPointF(730, 55 + 17 * 12),
        13: QPointF(730, 55 + 17 * 13),
        14: QPointF(730, 55 + 17 * 14),
        15: QPointF(730, 55 + 17 * 15),
    },

    'IAR_RECT': QRectF(400, 115, 220, 60),
    'IR_RECT': QRectF(550, 110, 130, 70),
    'REG_A_RECT': QRectF(130, 50, 140, 50),
    'REG_B_RECT': QRectF(330, 50, 140, 50),
    'ALU_RECT': QRectF(80, 170, 220, 120),
    'CONTROL_UNIT_RECT': QRectF(420, 180, 200, 150),
}

SIGNAL_PATHS = {
    # Các đường tín hiệu cũng cần điều chỉnh lại theo ảnh đã được phóng to
    'IAR_TO_RAM_ADDR_BUS': [QPointF(530, 115), QPointF(530, 30), QPointF(700, 30), QPointF(700, 45)],
    'RAM_DATA_TO_IR': [QPointF(780, 80), QPointF(600, 80), QPointF(600, 120)],
    'IR_TO_CONTROL_UNIT': [QPointF(620, 170), QPointF(520, 170), QPointF(520, 250)],
    'RAM_DATA_TO_REG_A': [QPointF(780, 100), QPointF(200, 100), QPointF(200, 80)],
    'REG_A_TO_RAM_DATA_BUS': [QPointF(200, 100), QPointF(750, 100)],
    'REG_A_TO_ALU': [QPointF(200, 100), QPointF(180, 180)],
    'REG_B_TO_ALU': [QPointF(400, 100), QPointF(220, 180)],
    'ALU_TO_REG_A': [QPointF(180, 260), QPointF(200, 260), QPointF(200, 100)],
    'ADDR_TO_IAR_JUMP': [QPointF(530, 330), QPointF(530, 175)]
}


class CPUVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing CPUVisualizerApp...")
        self.setWindowTitle("CPU Execution Visualizer")
        self.setGeometry(100, 100, 1800, 1000) # Tăng kích thước cửa sổ để có không gian

        self.cpu = CPU()

        self.scene = QGraphicsScene()
        self.signal_animator = SignalAnimator(self.scene)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.diagram_text_items = {}
        self.diagram_rect_highlights = {}

        self.cpu_current_phase = 'IDLE'
        self.cpu_phase_timer = QTimer(self)
        self.cpu_phase_timer.setInterval(200)
        self.cpu_phase_timer.timeout.connect(self._advance_cpu_phase)

        self.animation_step_duration = 500

        self.init_ui()
        self.update_gui_cpu_status()
        print("CPUVisualizerApp initialized successfully.")


    def init_ui(self):
        self.left_panel = QVBoxLayout()
        self.main_layout.addLayout(self.left_panel, 1)

        self.right_panel = QVBoxLayout()
        self.main_layout.addLayout(self.right_panel, 4) # Tăng tỷ lệ cho panel chứa sơ đồ CPU (từ 3 lên 4 hoặc hơn)

        # --- Right Panel: CPU Diagram ---
        self.view = QGraphicsView(self.scene)
        self.right_panel.addWidget(self.view)

        try:
            self.cpu_diagram_pixmap = QPixmap("assets/cpu-diagram.PNG")
            if self.cpu_diagram_pixmap.isNull():
                QMessageBox.critical(self, "Lỗi tải ảnh", "Không thể tải ảnh sơ đồ CPU. Kiểm tra đường dẫn 'assets/cpu-diagram.PNG'.")
                self.scene.addRect(0, 0, 800, 400, QPen(QColor("red")), QColor("lightgray"))
            else:
                # ĐIỀU CHỈNH KÍCH THƯỚC CỦA ẢNH TẠI ĐÂY
                # Ví dụ: Phóng to ảnh gấp 1.5 lần
                scale_factor = 1.5 # Bạn có thể thay đổi giá trị này (ví dụ: 1.2, 1.8, 2.0)
                new_width = int(self.cpu_diagram_pixmap.width() * scale_factor)
                new_height = int(self.cpu_diagram_pixmap.height() * scale_factor)
                self.cpu_diagram_pixmap = self.cpu_diagram_pixmap.scaled(new_width, new_height,
                                                                          Qt.AspectRatioMode.KeepAspectRatio,
                                                                          Qt.TransformationMode.SmoothTransformation)

                # Sau khi thay đổi kích thước, thêm pixmap mới vào scene
                self.scene.addPixmap(self.cpu_diagram_pixmap)
                
                # Quan trọng: Cập nhật sceneRect để khớp với kích thước mới của pixmap
                self.scene.setSceneRect(QRectF(self.cpu_diagram_pixmap.rect()))
                
                # fitInView sẽ điều chỉnh view để hiển thị toàn bộ sceneRect đã được cập nhật
                self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi tải ảnh", f"Xảy ra lỗi khi tải ảnh: {e}")
            print(f"Lỗi tải ảnh: {e}")
            self.scene.addRect(0, 0, 800, 400, QPen(QColor("red")), QColor("lightgray"))

        # --- Thêm các thành phần hiển thị trên SƠ ĐỒ CPU ---
        # LƯU Ý: SAU KHI PHÓNG TO ẢNH, BẠN CŨNG CẦN ĐIỀU CHỈNH LẠI CÁC TỌA ĐỘ TRONG DIAGRAM_COORDS
        # Bằng cách nhân các tọa độ cũ với 'scale_factor' hoặc ước tính lại thủ công.
        # Ví dụ: nếu IAR_TEXT_POS cũ là QPointF(50, 60) và scale_factor là 1.5,
        # thì IAR_TEXT_POS mới có thể là QPointF(50*1.5, 60*1.5) = QPointF(75, 90)
        # Tốt nhất là mở ứng dụng lên, phóng to ảnh, sau đó dùng công cụ đo pixel trên ảnh
        # đã phóng to để cập nhật lại các tọa độ trong DIAGRAM_COORDS và SIGNAL_PATHS.
        self.setup_diagram_elements()

        # ... (phần còn lại của init_ui không thay đổi)
        self.control_buttons_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.step_button = QPushButton("Step")
        self.reset_button = QPushButton("Reset")

        self.control_buttons_layout.addWidget(self.run_button)
        self.control_buttons_layout.addWidget(self.step_button)
        self.control_buttons_layout.addWidget(self.reset_button)
        self.left_panel.addLayout(self.control_buttons_layout)

        self.run_button.clicked.connect(self.run_cpu)
        self.step_button.clicked.connect(self.step_cpu)
        self.reset_button.clicked.connect(self.reset_cpu)

        self.ram_group_box = QWidget()
        self.ram_group_box_layout = QVBoxLayout(self.ram_group_box)
        self.left_panel.addWidget(self.ram_group_box)

        self.ram_table = QTableWidget(16, 2)
        self.ram_table.setHorizontalHeaderLabels(["Address", "Data (8-bit)"])
        for i in range(16):
            self.ram_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.ram_table.setItem(i, 1, QTableWidgetItem("00000000"))
        self.ram_table.setColumnWidth(0, 50)
        self.ram_table.setColumnWidth(1, 90)
        self.ram_table.verticalHeader().setVisible(False)
        self.ram_group_box_layout.addWidget(QLabel("RAM (Instruction/Data)"))
        self.ram_group_box_layout.addWidget(self.ram_table)

        self.instr_loader_layout = QFormLayout()
        self.left_panel.addLayout(self.instr_loader_layout)

        self.instr_address_input = QLineEdit("0")
        self.instr_address_input.setPlaceholderText("0-15")
        self.instr_address_input.setFixedWidth(50)

        self.opcode_combo = QComboBox()
        for opcode_bits, info in self.cpu.opcode_map.items():
            self.opcode_combo.addItem(f"{info['name']} ({opcode_bits})", opcode_bits)

        self.operand_input = QLineEdit("0000")
        self.operand_input.setPlaceholderText("4-bit binary (e.g., 0101)")
        self.operand_input.setFixedWidth(80)

        self.load_instr_button = QPushButton("Load Instruction to RAM")
        self.load_instr_button.clicked.connect(self.load_instruction_gui)

        self.instr_loader_layout.addRow(QLabel("Địa chỉ RAM:"), self.instr_address_input)
        self.instr_loader_layout.addRow(QLabel("Opcode:"), self.opcode_combo)
        self.instr_loader_layout.addRow(QLabel("Operand/Addr:"), self.operand_input)
        self.instr_loader_layout.addRow(self.load_instr_button)

        self.register_display_labels = {}
        self.flags_display_labels = {}
        self.setup_register_and_flag_display()

        self.run_timer = QTimer(self)
        self.run_timer.setInterval(500)
        self.run_timer.timeout.connect(self.step_cpu)

    def setup_register_and_flag_display(self):
        """Thiết lập các QLabel để hiển thị giá trị của Registers và Flags."""

        reg_flag_layout = QVBoxLayout()
        self.left_panel.addLayout(reg_flag_layout)

        reg_flag_layout.addWidget(QLabel("<b>CPU Registers & Flags:</b>"))

        # Registers
        self.register_display_labels['A'] = QLabel("Reg A: 0 (00000000)")
        self.register_display_labels['B'] = QLabel("Reg B: 0 (00000000)")
        self.register_display_labels['IAR'] = QLabel("IAR: 0 (0000)")
        self.register_display_labels['IR_Opcode'] = QLabel("IR (Opcode): 0000")
        self.register_display_labels['IR_AddrData'] = QLabel("IR (Addr/Data): 0000")

        for label_key in ['A', 'B', 'IAR', 'IR_Opcode', 'IR_AddrData']:
            reg_flag_layout.addWidget(self.register_display_labels[label_key])

        # Flags
        self.flags_display_labels['Z'] = QLabel("Z: F")
        self.flags_display_labels['N'] = QLabel("N: F")
        self.flags_display_labels['O'] = QLabel("O: F")

        for label_key in ['Z', 'N', 'O']:
            reg_flag_layout.addWidget(self.flags_display_labels[label_key])


    def setup_diagram_elements(self):
        """Thiết lập các QGraphicsItem để hiển thị giá trị và highlight trên sơ đồ CPU."""
        # Font size có thể cần điều chỉnh nếu bạn phóng to ảnh quá nhiều
        font = QFont("Arial", 10, QFont.Weight.Bold)

        # IAR (Program Counter)
        self.diagram_text_items['IAR'] = self.scene.addText("IAR: 0", font)
        self.diagram_text_items['IAR'].setPos(DIAGRAM_COORDS['IAR_TEXT_POS'])
        self.diagram_rect_highlights['IAR'] = self.scene.addRect(DIAGRAM_COORDS['IAR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        # IR (Instruction Register) - Opcode and Addr/Data parts
        self.diagram_text_items['IR_Opcode'] = self.scene.addText("Op:0000", font)
        self.diagram_text_items['IR_Opcode'].setPos(DIAGRAM_COORDS['IR_OPCODE_TEXT_POS'])
        self.diagram_text_items['IR_AddrData'] = self.scene.addText("Ad:0000", font)
        self.diagram_text_items['IR_AddrData'].setPos(DIAGRAM_COORDS['IR_ADDRDATA_TEXT_POS'])
        self.diagram_rect_highlights['IR'] = self.scene.addRect(DIAGRAM_COORDS['IR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))


        # Registers A & B
        self.diagram_text_items['A'] = self.scene.addText("A: 0 (00)", font)
        self.diagram_text_items['A'].setPos(DIAGRAM_COORDS['REG_A_TEXT_POS'])
        self.diagram_rect_highlights['A'] = self.scene.addRect(DIAGRAM_COORDS['REG_A_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['B'] = self.scene.addText("B: 0 (00)", font)
        self.diagram_text_items['B'].setPos(DIAGRAM_COORDS['REG_B_TEXT_POS'])
        self.diagram_rect_highlights['B'] = self.scene.addRect(DIAGRAM_COORDS['REG_B_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        # Flags (Z, N, O)
        self.diagram_text_items['Z_flag'] = self.scene.addText("Z: F", font)
        self.diagram_text_items['Z_flag'].setPos(DIAGRAM_COORDS['FLAG_Z_POS'])
        self.diagram_text_items['N_flag'] = self.scene.addText("N: F", font)
        self.diagram_text_items['N_flag'].setPos(DIAGRAM_COORDS['FLAG_N_POS'])
        self.diagram_text_items['O_flag'] = self.scene.addText("O: F", font)
        self.diagram_text_items['O_flag'].setPos(DIAGRAM_COORDS['FLAG_O_POS'])

        # RAM Cells on Diagram
        self.diagram_ram_cells = {} # Lưu trữ QGraphicsTextItem cho mỗi ô RAM trên sơ đồ
        for i in range(16):
            if i in DIAGRAM_COORDS['RAM_CELL_POSITIONS']:
                text_item = self.scene.addText(f"RAM[{i}]: 00000000", QFont("Arial", 8))
                text_item.setPos(DIAGRAM_COORDS['RAM_CELL_POSITIONS'][i])
                self.diagram_ram_cells[i] = text_item

        # Highlight for ALU (will be activated during ADD/SUB)
        self.diagram_rect_highlights['ALU'] = self.scene.addRect(DIAGRAM_COORDS['ALU_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))
        # Highlight for Control Unit (will be activated during Decode/Execute phases)
        self.diagram_rect_highlights['CONTROL_UNIT'] = self.scene.addRect(DIAGRAM_COORDS['CONTROL_UNIT_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))


    def update_gui_cpu_status(self):
        """Cập nhật các giá trị của RAM, Registers, và Flags lên GUI (cả bảng và sơ đồ)."""
        # 1. Update RAM Table (bên trái)
        for i in range(16):
            self.ram_table.setItem(i, 1, QTableWidgetItem(self.cpu.ram[i]))
            # Cập nhật RAM cells trên sơ đồ
            if i in self.diagram_ram_cells:
                self.diagram_ram_cells[i].setPlainText(f"RAM[{i}]: {self.cpu.ram[i]}")

        # 2. Update Register Labels (bên trái)
        self.register_display_labels['A'].setText(f"Reg A: {self.cpu.registers['A']} ({self.cpu.registers['A']:08b})")
        self.register_display_labels['B'].setText(f"Reg B: {self.cpu.registers['B']} ({self.cpu.registers['B']:08b})")
        self.register_display_labels['IAR'].setText(f"IAR: {self.cpu.registers['IAR']} ({self.cpu.registers['IAR']:04b})")
        self.register_display_labels['IR_Opcode'].setText(f"IR (Opcode): {self.cpu.registers['IR_Opcode']}")
        self.register_display_labels['IR_AddrData'].setText(f"IR (Addr/Data): {self.cpu.registers['IR_AddrData']}")

        # 3. Update Register/IR/IAR Labels ON DIAGRAM
        self.diagram_text_items['IAR'].setPlainText(f"IAR: {self.cpu.registers['IAR']:04b}") # IAR display as 4-bit binary
        self.diagram_text_items['IR_Opcode'].setPlainText(f"Op:{self.cpu.registers['IR_Opcode']}")
        self.diagram_text_items['IR_AddrData'].setPlainText(f"Ad:{self.cpu.registers['IR_AddrData']}")
        self.diagram_text_items['A'].setPlainText(f"A: {self.cpu.registers['A']:08b}") # Reg A display as 8-bit binary
        self.diagram_text_items['B'].setPlainText(f"B: {self.cpu.registers['B']:08b}") # Reg B display as 8-bit binary

        # 4. Update Flag Labels (bên trái và trên sơ đồ)
        z_flag_status = 'T' if self.cpu.flags['Z'] else 'F'
        n_flag_status = 'T' if self.cpu.flags['N'] else 'F'
        o_flag_status = 'T' if self.cpu.flags['O'] else 'F'

        self.flags_display_labels['Z'].setText(f"Z: {z_flag_status}")
        self.flags_display_labels['N'].setText(f"N: {n_flag_status}")
        self.flags_display_labels['O'].setText(f"O: {o_flag_status}")

        self.diagram_text_items['Z_flag'].setPlainText(f"Z: {z_flag_status}")
        self.diagram_text_items['N_flag'].setPlainText(f"N: {n_flag_status}")
        self.diagram_text_items['O_flag'].setPlainText(f"O: {o_flag_status}")

        # Reset tất cả các highlight
        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

    def load_instruction_gui(self):
        """Tải một lệnh từ GUI vào RAM."""
        try:
            address_str = self.instr_address_input.text()
            address = int(address_str)
            if not (0 <= address <= 15):
                QMessageBox.warning(self, "Lỗi đầu vào", "Địa chỉ RAM phải từ 0 đến 15.")
                return

            opcode_bits = self.opcode_combo.currentData()
            operand_bits = self.operand_input.text()

            if not (len(operand_bits) == 4 and all(c in '01' for c in operand_bits)):
                QMessageBox.warning(self, "Lỗi đầu vào", "Toán hạng/Địa chỉ phải là 4 bit nhị phân.")
                return

            full_instruction = opcode_bits + operand_bits
            self.cpu.load_ram(address, full_instruction)
            self.update_gui_cpu_status()
            QMessageBox.information(self, "Thành công", f"Đã tải lệnh '{full_instruction}' vào RAM[{address}].")

        except ValueError:
            QMessageBox.critical(self, "Lỗi đầu vào", "Vui lòng nhập địa chỉ và toán hạng/địa chỉ hợp lệ.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {e}")


    def _clear_all_highlights_and_animations(self):
        """Xóa tất cả highlights và dừng/dọn dẹp animations."""
        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

        # Đảm bảo tất cả animations cũ được dừng và dọn dẹp
        for anim in list(self.signal_animator.active_animations):
            anim.stop()
            if anim.targetObject() and self.scene.items().count(anim.targetObject()) > 0:
                self.scene.removeItem(anim.targetObject())
            anim.deleteLater()
        self.signal_animator.active_animations.clear()


    def highlight_component(self, component_key, color=Qt.GlobalColor.yellow, duration=200):
        """Hàm dùng để highlight một thành phần trên sơ đồ và tự động tắt."""
        if component_key in self.diagram_rect_highlights:
            rect_item = self.diagram_rect_highlights[component_key]
            original_pen = rect_item.pen()
            original_brush = rect_item.brush()

            rect_item.setPen(QPen(color, 2))
            rect_item.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 50)))

            QTimer.singleShot(duration, lambda: self._reset_single_highlight(component_key, original_pen, original_brush))

    def _reset_single_highlight(self, component_key, original_pen, original_brush):
        if component_key in self.diagram_rect_highlights:
            self.diagram_rect_highlights[component_key].setPen(original_pen)
            self.diagram_rect_highlights[component_key].setBrush(original_brush)


    def _animate_signal(self, path_name, color=Qt.GlobalColor.red):
        """Gọi SignalAnimator để chạy hoạt ảnh trên đường dây."""
        if path_name in SIGNAL_PATHS:
            self.signal_animator.animate_path(SIGNAL_PATHS[path_name], color, duration=self.animation_step_duration)
        else:
            print(f"Lỗi: Đường dẫn tín hiệu '{path_name}' không được định nghĩa.")


    def step_cpu(self):
        """Kích hoạt chu kỳ CPU từng bước (kiểm soát pha)."""
        if self.cpu.is_halted:
            self.run_timer.stop()
            QMessageBox.information(self, "CPU Halted", "CPU đã dừng thực thi.")
            self.cpu_current_phase = 'IDLE'
            return

        self._clear_all_highlights_and_animations()

        if self.cpu_current_phase == 'IDLE':
            self.cpu_current_phase = 'FETCH'

        self.run_timer.stop()
        self.cpu_phase_timer.start()

        self.run_button.setEnabled(False)
        self.step_button.setEnabled(False)


    def _advance_cpu_phase(self):
        """Tiến lên một pha trong chu kỳ CPU."""
        if self.cpu.is_halted:
            self.cpu_phase_timer.stop()
            self.cpu_current_phase = 'IDLE'
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)
            return

        if self.cpu_current_phase == 'FETCH':
            print("--- PHASE: FETCH ---")
            self.highlight_component('IAR', Qt.GlobalColor.red)
            self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.red)

            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu.fetch_instruction()
            self.update_gui_cpu_status()

            self.highlight_component('IR', Qt.GlobalColor.red)
            self._animate_signal('RAM_DATA_TO_IR', Qt.GlobalColor.green)

            self.cpu_current_phase = 'DECODE'

        elif self.cpu_current_phase == 'DECODE':
            print("--- PHASE: DECODE ---")
            self.cpu_phase_timer.setInterval(200)
            self.highlight_component('IR', Qt.GlobalColor.darkYellow)
            self.highlight_component('CONTROL_UNIT', Qt.GlobalColor.cyan)
            self._animate_signal('IR_TO_CONTROL_UNIT', Qt.GlobalColor.darkMagenta)

            decoded_instruction = self.cpu.decode_instruction()

            self.cpu_current_phase = 'EXECUTE'
            self.cpu.last_decoded_instruction = decoded_instruction


        elif self.cpu_current_phase == 'EXECUTE':
            print("--- PHASE: EXECUTE ---")
            self.cpu_phase_timer.stop()

            decoded_instruction = self.cpu.last_decoded_instruction

            op_name = decoded_instruction['name']

            if op_name == 'ADD' or op_name == 'SUB':
                self.highlight_component('ALU', Qt.GlobalColor.magenta)
                self.highlight_component('A', Qt.GlobalColor.green)
                self.highlight_component('B', Qt.GlobalColor.green)
                self._animate_signal('REG_A_TO_ALU', Qt.GlobalColor.darkCyan)
                self._animate_signal('REG_B_TO_ALU', Qt.GlobalColor.darkCyan)
                self.cpu_phase_timer.setInterval(self.animation_step_duration * 2)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_ALU_RESULT'
                return

            elif op_name == 'LOAD_A':
                self.highlight_component('A', Qt.GlobalColor.green)
                self._animate_signal('RAM_DATA_TO_REG_A', Qt.GlobalColor.darkCyan)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
                return
            elif op_name == 'LOAD_B':
                self.highlight_component('B', Qt.GlobalColor.green)
                self._animate_signal('RAM_DATA_TO_REG_B', Qt.GlobalColor.darkCyan)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
                return
            elif op_name == 'STORE_A':
                self.highlight_component('A', Qt.GlobalColor.darkGreen)
                self._animate_signal('REG_A_TO_RAM_DATA_BUS', Qt.GlobalColor.darkRed)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
                return
            elif op_name == 'STORE_B':
                self.highlight_component('B', Qt.GlobalColor.darkGreen)
                self._animate_signal('REG_B_TO_RAM_DATA_BUS', Qt.GlobalColor.darkRed)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
                return
            elif op_name == 'JUMP' or op_name == 'JUMP_NEG' or op_name == 'JUMP_ZERO':
                self.highlight_component('IAR', Qt.GlobalColor.blue)
                self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.blue)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_phase_timer.start()
                self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
                return

            self._finish_execute_phase()

        elif self.cpu_current_phase == 'EXECUTE_ALU_RESULT':
            print("--- PHASE: EXECUTE (ALU Result) ---")
            self._animate_signal('ALU_TO_REG_A', Qt.GlobalColor.red)
            self.highlight_component('A', Qt.GlobalColor.red)
            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu_phase_timer.start()
            self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
            return

        elif self.cpu_current_phase == 'EXECUTE_WAIT_ANIM':
            print("--- PHASE: EXECUTE (Waiting for Animation) ---")
            self.cpu.execute_instruction(self.cpu.last_decoded_instruction)
            self.update_gui_cpu_status()
            self._finish_execute_phase()

        self.update_gui_cpu_status()

    def _finish_execute_phase(self):
        """Kết thúc pha Execute và chuẩn bị cho chu kỳ tiếp theo."""
        self.cpu_phase_timer.stop()
        self.cpu_current_phase = 'IDLE'
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        if self.run_button.isEnabled() and not self.cpu.is_halted:
            if not self.run_timer.isActive():
                self.run_timer.start()


    def run_cpu(self):
        """Chạy CPU tự động từng bước."""
        if self.cpu.is_halted:
            QMessageBox.information(self, "CPU Halted", "CPU đã dừng. Vui lòng Reset trước khi chạy.")
            return

        self.run_timer.start()
        self.run_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.step_cpu()


    def reset_cpu(self):
        """Đặt lại trạng thái CPU và GUI."""
        self.run_timer.stop()
        self.cpu_phase_timer.stop()
        self.cpu_current_phase = 'IDLE'
        self._clear_all_highlights_and_animations()
        self.cpu.reset()
        self.update_gui_cpu_status()
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        QMessageBox.information(self, "Reset CPU", "CPU đã được đặt lại trạng thái ban đầu.")

# Phần chạy ứng dụng ở cuối file main.py
if __name__ == "__main__":
    print("Starting application execution block...")
    try:
        app = QApplication(sys.argv)
        window = CPUVisualizerApp()
        window.show()
        print("Application window created and attempting to show.")
        sys.exit(app.exec())
    except Exception as e:
        print(f"An unhandled error occurred during application execution: {e}")
        import traceback
        traceback.print_exc()
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QGraphicsView,
    QGraphicsScene, QComboBox, QLineEdit, QFormLayout, QMessageBox, QGraphicsRectItem,
    QGroupBox
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QFont, QBrush, QTransform, QResizeEvent
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF

from .cpu_core import CPU
from .gui_elements import SignalAnimator

# Định nghĩa TỌA ĐỘ cho các thành phần trên sơ đồ (BẠN CẦN THAY ĐỔI THEO HÌNH CỦA BẠN!)
# Các tọa độ này là giả định DỰA TRÊN KÍCH THƯỚC GỐC CỦA ẢNH (trước khi scale_factor được áp dụng).
# Chúng ta sẽ tính toán lại trong hàm setup_diagram_elements hoặc adjust_diagram_scale.
# Tốt nhất là bạn nên xác định các tọa độ này TƯƠNG ĐỐI hoặc SAU KHI ẢNH ĐÃ ĐƯỢC SCALE MỘT LẦN CỐ ĐỊNH.
# Hoặc, bạn có thể định nghĩa các tọa độ này dựa trên ảnh gốc, và sau đó nhân với `current_scale_factor`
# trong hàm setup_diagram_elements.
DIAGRAM_COORDS_ORIGINAL = {
    'IAR_TEXT_POS': QPointF(500, 300),
    'IR_OPCODE_TEXT_POS': QPointF(500, 300),
    'IR_ADDRDATA_TEXT_POS': QPointF(500, 300),
    'REG_A_TEXT_POS': QPointF(500, 300),
    'REG_B_TEXT_POS': QPointF(500, 300),
    'ALU_OUT_TEXT_POS': QPointF(500, 300),
    'FLAG_Z_POS': QPointF(500, 300),
    'FLAG_N_POS': QPointF(500, 300),
    'FLAG_O_POS': QPointF(500, 300),

    'RAM_CELL_POSITIONS': {
        0: QPointF(796, 55 + 17 * 2.5),
        1: QPointF(796, 55 + 17 * 4),
        2: QPointF(796, 55 + 17 * 5.5),
        3: QPointF(796, 55 + 17 * 7),
        4: QPointF(796, 55 + 17 * 8.5),
        5: QPointF(796, 55 + 17 * 10),
        6: QPointF(796, 55 + 17 * 11.5),
        7: QPointF(796, 55 + 17 * 13),
        8: QPointF(796, 55 + 17 * 14.5),
        9: QPointF(796, 55 + 17 * 16),
        10: QPointF(796, 55 + 17 * 17.5),
        11: QPointF(796, 55 + 17 * 19),
        12: QPointF(796, 55 + 17 * 20.5),
        13: QPointF(796, 55 + 17 * 22),
        14: QPointF(796, 55 + 17 * 23.5),
        15: QPointF(796, 55 + 17 * 25),
    },

    'IAR_RECT': QRectF(400, 115, 220, 60),
    'IR_RECT': QRectF(550, 110, 130, 70),
    'REG_A_RECT': QRectF(130, 50, 140, 50),
    'REG_B_RECT': QRectF(330, 50, 140, 50),
    'ALU_RECT': QRectF(80, 170, 220, 120),
    'CONTROL_UNIT_RECT': QRectF(420, 180, 200, 150),
}

SIGNAL_PATHS_ORIGINAL = {
    'IAR_TO_RAM_ADDR_BUS': [QPointF(530, 115), QPointF(530, 30), QPointF(700, 30), QPointF(700, 45)],
    'RAM_DATA_TO_IR': [QPointF(780, 80), QPointF(600, 80), QPointF(600, 120)],
    'IR_TO_CONTROL_UNIT': [QPointF(620, 170), QPointF(520, 170), QPointF(520, 250)],
    'RAM_DATA_TO_REG_A': [QPointF(780, 100), QPointF(200, 100), QPointF(200, 80)],
    'RAM_DATA_TO_REG_B': [QPointF(780, 100), QPointF(400, 100), QPointF(400, 80)],
    'REG_A_TO_RAM_DATA_BUS': [QPointF(200, 100), QPointF(750, 100)],
    'REG_B_TO_RAM_DATA_BUS': [QPointF(400, 100), QPointF(750, 100)],
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
        self.setGeometry(100, 100, 1500, 1000)

        self.cpu = CPU()

        self.scene = QGraphicsScene()
        self.signal_animator = SignalAnimator(self.scene)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.diagram_text_items = {}
        self.diagram_rect_highlights = {}
        self.diagram_ram_cells = {}
        # KHẮC PHỤC LỖI: Khởi tạo các từ điển ở đây
        self.register_display_labels = {}
        self.flags_display_labels = {}

        self.cpu_current_phase = 'IDLE'
        self.cpu_phase_timer = QTimer(self)
        self.cpu_phase_timer.setInterval(200)
        self.cpu_phase_timer.timeout.connect(self._advance_cpu_phase)

        self.animation_step_duration = 500
        self.current_diagram_scale = 1.0

        self.init_ui()
        self.update_gui_cpu_status()
        print("CPUVisualizerApp initialized successfully.")

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.adjust_diagram_scale()

    def adjust_diagram_scale(self):
        if self.cpu_diagram_pixmap and self.view and self.scene:
            view_width = self.view.viewport().width()
            
            pixmap_width = self.cpu_diagram_pixmap.width()

            padding_ratio = 0.02
            effective_view_width = view_width * (1 - 2 * padding_ratio)

            if pixmap_width > 0 and effective_view_width > 0:
                new_scale = effective_view_width / pixmap_width
                
                transform = QTransform()
                transform.scale(new_scale, new_scale)
                self.view.setTransform(transform)

                self.current_diagram_scale = new_scale
                
                self.view.centerOn(self.scene.sceneRect().center())

                self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

                self.update_diagram_element_positions()


    def init_ui(self):
        # Tạo layout chính cho toàn bộ ứng dụng
        self.control_panel_layout = QVBoxLayout()
        self.main_layout.addLayout(self.control_panel_layout, 1)

        self.diagram_layout = QVBoxLayout()
        self.main_layout.addLayout(self.diagram_layout, 4)

        # --- CÁC NÚT ĐIỀU KHIỂN Ở TRÊN CÙNG ---
        self.top_buttons_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.step_button = QPushButton("Step")
        self.reset_button = QPushButton("Reset")
        self.top_buttons_layout.addWidget(self.run_button)
        self.top_buttons_layout.addWidget(self.step_button)
        self.top_buttons_layout.addWidget(self.reset_button)
        self.diagram_layout.addLayout(self.top_buttons_layout)

        # --- Right Panel: CPU Diagram ---
        self.view = QGraphicsView(self.scene)
        self.diagram_layout.addWidget(self.view)

        try:
            self.cpu_diagram_pixmap = QPixmap("assets/cpu-diagram.PNG")
            if self.cpu_diagram_pixmap.isNull():
                QMessageBox.critical(self, "Error loading image", "Could not load CPU diagram image. Check path 'assets/cpu-diagram.PNG'.")
                self.scene.addRect(0, 0, 800, 400, QPen(QColor("red")), QColor("lightgray"))
            else:
                self.scene.addPixmap(self.cpu_diagram_pixmap)
                self.scene.setSceneRect(QRectF(self.cpu_diagram_pixmap.rect()))
        except Exception as e:
            QMessageBox.critical(self, "Error loading image", f"An error occurred while loading image: {e}")
            print(f"Error loading image: {e}")
            self.scene.addRect(0, 0, 800, 400, QPen(QColor("red")), QColor("lightgray"))

        self.setup_diagram_elements()
        QTimer.singleShot(0, self.adjust_diagram_scale)

        # --- Left Panel: Các bảng điều khiển ---
        # Bảng RAM ở trên cùng bên trái
        self.ram_group_box = QGroupBox("RAM (Instruction/Data)")
        self.ram_group_box_layout = QVBoxLayout(self.ram_group_box)
        
        self.ram_table = QTableWidget(16, 2)
        self.ram_table.setHorizontalHeaderLabels(["Address", "Data (8-bit)"])
        for i in range(16):
            self.ram_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.ram_table.setItem(i, 1, QTableWidgetItem("00000000"))
        self.ram_table.setColumnWidth(0, 50)
        self.ram_table.setColumnWidth(1, 90)
        self.ram_table.verticalHeader().setVisible(False)
        self.ram_group_box_layout.addWidget(self.ram_table)
        self.control_panel_layout.addWidget(self.ram_group_box, 2) # Tăng stretch factor cho RAM

        # Layout chứa các phần còn lại (CPU Registers, CPU Flags, Instruction Loader)
        self.bottom_control_layout = QVBoxLayout()
        self.control_panel_layout.addLayout(self.bottom_control_layout, 1) # Giảm stretch factor

        # Layout riêng cho phần điều khiển nạp lệnh
        self.instr_loader_group_box = QGroupBox("Load Instruction to RAM")
        self.instr_loader_layout = QVBoxLayout(self.instr_loader_group_box)
        self.instr_loader_form = QFormLayout()

        self.instr_address_input = QLineEdit("0")
        self.instr_address_input.setPlaceholderText("0-15")
        self.instr_address_input.setFixedWidth(50)

        self.opcode_combo = QComboBox()
        for opcode_bits, info in self.cpu.opcode_map.items():
            self.opcode_combo.addItem(f"{info['name']} ({opcode_bits})", opcode_bits)

        self.operand_input = QLineEdit("0000")
        self.operand_input.setPlaceholderText("4-bit binary (e.g., 0101)")
        self.operand_input.setFixedWidth(80)

        self.load_instr_button = QPushButton("Load")
        self.load_instr_button.clicked.connect(self.load_instruction_gui)

        self.instr_loader_form.addRow(QLabel("Địa chỉ RAM:"), self.instr_address_input)
        self.instr_loader_form.addRow(QLabel("Opcode:"), self.opcode_combo)
        self.instr_loader_form.addRow(QLabel("Operand/Addr:"), self.operand_input)
        
        self.instr_loader_layout.addLayout(self.instr_loader_form)
        self.instr_loader_layout.addWidget(self.load_instr_button)
        self.bottom_control_layout.addWidget(self.instr_loader_group_box)
        
        # Bố cục cho CPU Registers và CPU Flags
        self.reg_flag_layout = QHBoxLayout()
        self.reg_group_box = QGroupBox("CPU Registers")
        self.reg_layout = QVBoxLayout(self.reg_group_box)
        self.flags_group_box = QGroupBox("CPU Flags")
        self.flags_layout = QVBoxLayout(self.flags_group_box)

        self.setup_register_and_flag_display(self.reg_layout, self.flags_layout)

        self.reg_flag_layout.addWidget(self.reg_group_box)
        self.reg_flag_layout.addWidget(self.flags_group_box)

        # Thêm các thành phần vào bottom_control_layout
        self.bottom_control_layout.addLayout(self.reg_flag_layout)
        self.bottom_control_layout.addLayout(self.instr_loader_layout)


        self.run_timer = QTimer(self)
        self.run_timer.setInterval(500)
        self.run_timer.timeout.connect(self.step_cpu)

    def update_diagram_element_positions(self):
        if not hasattr(self, 'current_diagram_scale') or self.current_diagram_scale == 0:
            return

        scale = self.current_diagram_scale
        font_size = 10 / scale
        
        font = QFont("Arial", int(font_size), QFont.Weight.Bold)

        for key, item in self.diagram_text_items.items():
            if key in DIAGRAM_COORDS_ORIGINAL:
                original_pos = DIAGRAM_COORDS_ORIGINAL[key]
                new_pos = QPointF(original_pos.x(), original_pos.y())
                item.setPos(new_pos)
                item.setFont(font)
            elif key.endswith('_flag'):
                original_pos_key = key.replace('_flag', '') + '_POS'
                if original_pos_key in DIAGRAM_COORDS_ORIGINAL:
                    original_pos = DIAGRAM_COORDS_ORIGINAL[original_pos_key]
                    new_pos = QPointF(original_pos.x(), original_pos.y())
                    item.setPos(new_pos)
                    item.setFont(font)

        for key, item in self.diagram_rect_highlights.items():
            if key in DIAGRAM_COORDS_ORIGINAL:
                original_rect = DIAGRAM_COORDS_ORIGINAL[key]
                new_rect = QRectF(original_rect.x(), original_rect.y(),
                                    original_rect.width(), original_rect.height())
                item.setRect(new_rect)

        for i in range(16):
            if i in self.diagram_ram_cells and i in DIAGRAM_COORDS_ORIGINAL['RAM_CELL_POSITIONS']:
                original_pos = DIAGRAM_COORDS_ORIGINAL['RAM_CELL_POSITIONS'][i]
                new_pos = QPointF(original_pos.x(), original_pos.y())
                self.diagram_ram_cells[i].setPos(new_pos)
                self.diagram_ram_cells[i].setFont(QFont("Arial", int(8 / scale)))

    def setup_diagram_elements(self):
        font = QFont("Arial", 10, QFont.Weight.Bold)

        self.diagram_text_items['IAR'] = self.scene.addText("IAR: 0", font)
        self.diagram_rect_highlights['IAR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IAR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['IR_Opcode'] = self.scene.addText("Op:0000", font)
        self.diagram_text_items['IR_AddrData'] = self.scene.addText("Ad:0000", font)
        self.diagram_rect_highlights['IR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['A'] = self.scene.addText("A: 0 (00)", font)
        self.diagram_rect_highlights['A'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_A_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['B'] = self.scene.addText("B: 0 (00)", font)
        self.diagram_rect_highlights['B'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_B_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['Z_flag'] = self.scene.addText("Z: F", font)
        self.diagram_text_items['N_flag'] = self.scene.addText("N: F", font)
        self.diagram_text_items['O_flag'] = self.scene.addText("O: F", font)

        for i in range(16):
            if i in DIAGRAM_COORDS_ORIGINAL['RAM_CELL_POSITIONS']:
                text_item = self.scene.addText(f"RAM[{i}]: 00000000", QFont("Arial", 12))
                self.diagram_ram_cells[i] = text_item

        self.diagram_rect_highlights['ALU'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['ALU_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))
        self.diagram_rect_highlights['CONTROL_UNIT'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['CONTROL_UNIT_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.update_diagram_element_positions()

    def update_gui_cpu_status(self):
        for i in range(16):
            self.ram_table.setItem(i, 1, QTableWidgetItem(self.cpu.ram[i]))
            if i in self.diagram_ram_cells:
                self.diagram_ram_cells[i].setPlainText(f"RAM[{i}]: {self.cpu.ram[i]}")

        # KHẮC PHỤC: Thêm kiểm tra trước khi truy cập
        if hasattr(self, 'register_display_labels'):
            self.register_display_labels['A'].setText(f"Reg A: {self.cpu.registers['A']} ({self.cpu.registers['A']:08b})")
            self.register_display_labels['B'].setText(f"Reg B: {self.cpu.registers['B']} ({self.cpu.registers['B']:08b})")
            self.register_display_labels['IAR'].setText(f"IAR: {self.cpu.registers['IAR']} ({self.cpu.registers['IAR']:04b})")
            self.register_display_labels['IR_Opcode'].setText(f"IR (Opcode): {self.cpu.registers['IR_Opcode']}")
            self.register_display_labels['IR_AddrData'].setText(f"IR (Addr/Data): {self.cpu.registers['IR_AddrData']}")

        self.diagram_text_items['IAR'].setPlainText(f"IAR: {self.cpu.registers['IAR']:04b}")
        self.diagram_text_items['IR_Opcode'].setPlainText(f"Op:{self.cpu.registers['IR_Opcode']}")
        self.diagram_text_items['IR_AddrData'].setPlainText(f"Ad:{self.cpu.registers['IR_AddrData']}")
        self.diagram_text_items['A'].setPlainText(f"A: {self.cpu.registers['A']:08b}")
        self.diagram_text_items['B'].setPlainText(f"B: {self.cpu.registers['B']:08b}")

        z_flag_status = 'T' if self.cpu.flags['Z'] else 'F'
        n_flag_status = 'T' if self.cpu.flags['N'] else 'F'
        o_flag_status = 'T' if self.cpu.flags['O'] else 'F'

        if hasattr(self, 'flags_display_labels'):
            self.flags_display_labels['Z'].setText(f"Z: {z_flag_status}")
            self.flags_display_labels['N'].setText(f"N: {n_flag_status}")
            self.flags_display_labels['O'].setText(f"O: {o_flag_status}")

        self.diagram_text_items['Z_flag'].setPlainText(f"Z: {z_flag_status}")
        self.diagram_text_items['N_flag'].setPlainText(f"N: {n_flag_status}")
        self.diagram_text_items['O_flag'].setPlainText(f"O: {o_flag_status}")

        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

    def load_instruction_gui(self):
        try:
            address_str = self.instr_address_input.text()
            address = int(address_str)
            if not (0 <= address <= 15):
                QMessageBox.warning(self, "Input error", "RAM address must be between 0 and 15.")
                return

            opcode_bits = self.opcode_combo.currentData()
            operand_bits = self.operand_input.text()

            if not (len(operand_bits) == 4 and all(c in '01' for c in operand_bits)):
                QMessageBox.warning(self, "Input error", "Operand/Address must be 4-bit binary.")
                return

            full_instruction = opcode_bits + operand_bits
            self.cpu.load_ram(address, full_instruction)
            self.update_gui_cpu_status()
            QMessageBox.information(self, "Success", f"Loaded instruction '{full_instruction}' into RAM[{address}].")
        except ValueError:
            QMessageBox.critical(self, "Input error", "Please enter valid address and operand/address.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def _clear_all_highlights_and_animations(self):
        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

        self.signal_animator.clear_animations()

    def highlight_component(self, component_key, color=Qt.GlobalColor.yellow, duration=200):
        if component_key in self.diagram_rect_highlights:
            rect_item = self.diagram_rect_highlights[component_key]
            
            pen = QPen(color, 2)
            brush_color = QColor(color)
            brush_color.setAlpha(50)
            brush = QBrush(brush_color)

            rect_item.setPen(pen)
            rect_item.setBrush(brush)
            
            QTimer.singleShot(duration, lambda: self._reset_single_highlight(component_key))

    def _reset_single_highlight(self, component_key):
        if component_key in self.diagram_rect_highlights:
            self.diagram_rect_highlights[component_key].setPen(QPen(Qt.GlobalColor.transparent))
            self.diagram_rect_highlights[component_key].setBrush(QBrush(Qt.GlobalColor.transparent))

    def _animate_signal(self, path_name, color=Qt.GlobalColor.red):
        if path_name in SIGNAL_PATHS_ORIGINAL:
            scaled_path = []
            for point in SIGNAL_PATHS_ORIGINAL[path_name]:
                scaled_path.append(QPointF(point.x(), point.y()))
            
            self.signal_animator.animate_path(scaled_path, color, duration=self.animation_step_duration)
        else:
            print(f"Error: Signal path '{path_name}' is not defined.")

    def step_cpu(self):
        if self.cpu.is_halted:
            self.run_timer.stop()
            QMessageBox.information(self, "CPU Halted", "CPU has stopped executing.")
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
            self.cpu.fetch_instruction()
            self.update_gui_cpu_status()
            
            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu_current_phase = 'FETCH_ANIM_WAIT'

        elif self.cpu_current_phase == 'FETCH_ANIM_WAIT':
            self.highlight_component('IR', Qt.GlobalColor.green)
            self._animate_signal('RAM_DATA_TO_IR', Qt.GlobalColor.green)
            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu_current_phase = 'DECODE'

        elif self.cpu_current_phase == 'DECODE':
            print("--- PHASE: DECODE ---")
            self.cpu_phase_timer.setInterval(200)
            self.highlight_component('IR', Qt.GlobalColor.darkYellow)
            self.highlight_component('CONTROL_UNIT', Qt.GlobalColor.cyan)
            self._animate_signal('IR_TO_CONTROL_UNIT', Qt.GlobalColor.darkMagenta)

            self.cpu.decode_instruction()

            self.cpu_phase_timer.setInterval(200) # Reset timer interval
            self.cpu_current_phase = 'EXECUTE'

        elif self.cpu_current_phase == 'EXECUTE':
            print("--- PHASE: EXECUTE ---")
            decoded_instruction = self.cpu.last_decoded_instruction
            op_name = decoded_instruction['name']

            if op_name == 'ADD' or op_name == 'SUB':
                self.highlight_component('ALU', Qt.GlobalColor.magenta)
                self.highlight_component('A', Qt.GlobalColor.green)
                self.highlight_component('B', Qt.GlobalColor.green)
                self._animate_signal('REG_A_TO_ALU', Qt.GlobalColor.darkCyan)
                self._animate_signal('REG_B_TO_ALU', Qt.GlobalColor.darkCyan)
                self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
                self.cpu_current_phase = 'EXECUTE_ALU_RESULT'
                self.cpu_phase_timer.start()
                return

            elif op_name == 'LOAD_A':
                self.highlight_component('A', Qt.GlobalColor.green)
                self._animate_signal('RAM_DATA_TO_REG_A', Qt.GlobalColor.darkCyan)
            elif op_name == 'LOAD_B':
                self.highlight_component('B', Qt.GlobalColor.green)
                self._animate_signal('RAM_DATA_TO_REG_B', Qt.GlobalColor.darkCyan)
            elif op_name == 'STORE_A':
                self.highlight_component('A', Qt.GlobalColor.darkGreen)
                self._animate_signal('REG_A_TO_RAM_DATA_BUS', Qt.GlobalColor.darkRed)
            elif op_name == 'STORE_B':
                self.highlight_component('B', Qt.GlobalColor.darkGreen)
                self._animate_signal('REG_B_TO_RAM_DATA_BUS', Qt.GlobalColor.darkRed)
            elif op_name == 'JUMP' or op_name == 'JUMP_NEG' or op_name == 'JUMP_ZERO':
                self.highlight_component('IAR', Qt.GlobalColor.blue)
                self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.blue)
            
            # Execute the instruction immediately for non-ALU operations
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            
            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
            self.cpu_phase_timer.start()
            return

        elif self.cpu_current_phase == 'EXECUTE_ALU_RESULT':
            print("--- PHASE: EXECUTE (ALU Result) ---")
            self._animate_signal('ALU_TO_REG_A', Qt.GlobalColor.red)
            self.highlight_component('A', Qt.GlobalColor.red)
            self.cpu_phase_timer.setInterval(self.animation_step_duration + 50)
            self.cpu_current_phase = 'EXECUTE_WAIT_ANIM'
            self.cpu_phase_timer.start()

        elif self.cpu_current_phase == 'EXECUTE_WAIT_ANIM':
            print("--- PHASE: EXECUTE (Waiting for Animation) ---")
            # For non-ALU operations, this is where the execution happens.
            # But we already executed them above.
            # For ALU, this is where we wait for the final animation and update.
            decoded_instruction = self.cpu.last_decoded_instruction
            op_name = decoded_instruction['name']
            if op_name in ['ADD', 'SUB']:
                self.cpu.execute_instruction()
            
            self.update_gui_cpu_status()
            self._finish_execute_phase()

        self.update_gui_cpu_status()

    def _finish_execute_phase(self):
        self.cpu_phase_timer.stop()
        self.cpu_current_phase = 'IDLE'
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        if self.run_button.isEnabled() and not self.cpu.is_halted and self.run_timer.isActive():
            self.run_timer.start()

    def run_cpu(self):
        if self.cpu.is_halted:
            QMessageBox.information(self, "CPU Halted", "CPU has stopped. Please reset before running.")
            return

        self.run_timer.start()
        self.run_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.step_cpu()

    def reset_cpu(self):
        self.run_timer.stop()
        self.cpu_phase_timer.stop()
        self.cpu_current_phase = 'IDLE'
        self._clear_all_highlights_and_animations()
        self.cpu.reset()
        self.update_gui_cpu_status()
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        QMessageBox.information(self, "Reset CPU", "CPU has been reset to factory state.")
        
    def setup_register_and_flag_display(self, reg_layout, flags_layout):
        self.register_display_labels['A'] = QLabel("Reg A: 0 (00000000)")
        self.register_display_labels['B'] = QLabel("Reg B: 0 (00000000)")
        self.register_display_labels['IAR'] = QLabel("IAR: 0 (0000)")
        self.register_display_labels['IR_Opcode'] = QLabel("IR (Opcode): 0000")
        self.register_display_labels['IR_AddrData'] = QLabel("IR (Addr/Data): 0000")

        reg_layout.addWidget(self.register_display_labels['A'])
        reg_layout.addWidget(self.register_display_labels['B'])
        reg_layout.addWidget(self.register_display_labels['IAR'])
        reg_layout.addWidget(self.register_display_labels['IR_Opcode'])
        reg_layout.addWidget(self.register_display_labels['IR_AddrData'])

        self.flags_display_labels['Z'] = QLabel("Z: False")
        self.flags_display_labels['N'] = QLabel("N: False")
        self.flags_display_labels['O'] = QLabel("O: False")
        
        flags_layout.addWidget(self.flags_display_labels['Z'])
        flags_layout.addWidget(self.flags_display_labels['N'])
        flags_layout.addWidget(self.flags_display_labels['O'])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CPUVisualizerApp()
    window.show()
    sys.exit(app.exec())
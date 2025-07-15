import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QGraphicsView,
    QGraphicsScene, QComboBox, QLineEdit, QFormLayout, QMessageBox, QGraphicsRectItem,
    QGroupBox, QGraphicsPathItem, QGraphicsProxyWidget, QScrollArea
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QFont, QBrush, QTransform, QResizeEvent, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QSequentialAnimationGroup

# Import các file của bạn từ cùng một gói (package)
from .cpu_core import CPU
from .gui_elements import SignalAnimator

# Định nghĩa TỌA ĐỘ đã cập nhật cho các thành phần trên sơ đồ
# Các tọa độ này đã được điều chỉnh để khớp với hình ảnh
DIAGRAM_COORDS_ORIGINAL = {
    # Tọa độ chữ (text) cho các giá trị thanh ghi/cờ
    'IAR_VALUE_POS': QPointF(430, 400),
    'IR_OPCODE_VALUE_POS': QPointF(430, 330),
    'IR_ADDRDATA_VALUE_POS': QPointF(500, 330),
    'REG_A_VALUE_POS': QPointF(50, 120),
    'REG_B_VALUE_POS': QPointF(200, 120),

    'ALU_OUT_VALUE_POS': QPointF(80, 430),
    'FLAG_Z_VALUE_POS': QPointF(380, 495),
    'FLAG_N_VALUE_POS': QPointF(340, 495),
    'FLAG_O_VALUE_POS': QPointF(300, 495),
    
    # Tọa độ mới cho bảng RAM (Proxy Widget)
    'RAM_TABLE_POS': QPointF(695, 67),
    
    # Tọa độ khung highlight (Rect)
    'IAR_RECT': QRectF(460, 100, 120, 60),
    'IR_RECT': QRectF(610, 210, 160, 80),
    'REG_A_RECT': QRectF(150, 220, 140, 50),
    'REG_B_RECT': QRectF(320, 220, 140, 50),
    'ALU_RECT': QRectF(190, 360, 220, 100),
    'CONTROL_UNIT_RECT': QRectF(500, 320, 150, 100),
}
SIGNAL_PATHS_ORIGINAL = {
    'IAR_TO_RAM_ADDR_BUS': [QPointF(530, 120), QPointF(530, 50), QPointF(800, 50), QPointF(800, 100)],
    'RAM_DATA_TO_IR': [QPointF(800, 250), QPointF(700, 250), QPointF(700, 220), QPointF(670, 220)],
    'IR_TO_CONTROL_UNIT': [QPointF(690, 290), QPointF(690, 350), QPointF(650, 350)],
    'RAM_DATA_TO_REG_A': [QPointF(800, 250), QPointF(450, 250), QPointF(450, 240), QPointF(290, 240)],
    'RAM_DATA_TO_REG_B': [QPointF(800, 250), QPointF(450, 250), QPointF(450, 240), QPointF(460, 240)],
    'REG_A_TO_RAM_DATA_BUS': [QPointF(290, 240), QPointF(450, 240), QPointF(450, 250), QPointF(800, 250)],
    'REG_B_TO_RAM_DATA_BUS': [QPointF(460, 240), QPointF(450, 240), QPointF(450, 250), QPointF(800, 250)],
    'REG_A_TO_ALU': [QPointF(290, 240), QPointF(290, 360)],
    'REG_B_TO_ALU': [QPointF(460, 240), QPointF(460, 360), QPointF(390, 360)],
    'ALU_TO_REG_A': [QPointF(280, 460), QPointF(280, 270)],
    'ADDR_TO_IAR_JUMP': [QPointF(690, 270), QPointF(690, 120), QPointF(580, 120)],
}


class CPUVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPU Execution Visualizer")
        self.setGeometry(100, 100, 1500, 1000)

        self.cpu = CPU()
        self.scene = QGraphicsScene()
        self.signal_animator = SignalAnimator(self.scene)
        self.signal_animator.animation_group.finished.connect(self._on_animation_finished)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.diagram_text_items = {}
        self.diagram_rect_highlights = {}
        self.register_display_labels = {}
        self.flags_display_labels = {}
        
        self.ram_proxy_widget = None

        self.cpu_current_phase = 'IDLE'
        self.is_running_mode = False
        self.is_animating = False

        self.animation_step_duration = 500
        self.current_diagram_scale = 1.0
        
        # Đã được kiểm tra và đúng
        self.cpu_phase_timer = QTimer(self)
        self.cpu_phase_timer.setSingleShot(True)
        self.cpu_phase_timer.timeout.connect(self._advance_cpu_phase)

        self.init_ui()
        self.update_gui_cpu_status()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        QTimer.singleShot(10, self.adjust_diagram_scale)

    def adjust_diagram_scale(self):
        if not hasattr(self, 'cpu_diagram_pixmap') or self.cpu_diagram_pixmap.isNull():
            return

        view_rect = self.view.viewport().rect()
        pixmap_rect = self.cpu_diagram_pixmap.rect()

        if pixmap_rect.width() > 0 and pixmap_rect.height() > 0:
            scale_x = view_rect.width() / pixmap_rect.width()
            scale_y = view_rect.height() / pixmap_rect.height()
            new_scale = min(scale_x, scale_y) * 0.95
            
            transform = QTransform()
            transform.scale(new_scale, new_scale)
            self.view.setTransform(transform)
            
            self.current_diagram_scale = new_scale
            self.view.centerOn(self.scene.sceneRect().center())
            self.update_diagram_element_positions()

    def init_ui(self):
        self.control_panel_layout = QVBoxLayout()
        self.main_layout.addLayout(self.control_panel_layout, 1)

        self.diagram_layout = QVBoxLayout()
        self.main_layout.addLayout(self.diagram_layout, 4)
        
        self.top_buttons_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.step_button = QPushButton("Step")
        self.reset_button = QPushButton("Reset")
        
        self.run_button.clicked.connect(self.run_cpu)
        self.step_button.clicked.connect(self.step_cpu)
        self.reset_button.clicked.connect(self.reset_cpu)

        self.top_buttons_layout.addWidget(self.run_button)
        self.top_buttons_layout.addWidget(self.step_button)
        self.top_buttons_layout.addWidget(self.reset_button)
        self.diagram_layout.addLayout(self.top_buttons_layout)
        
        self.view = QGraphicsView(self.scene)
        self.diagram_layout.addWidget(self.view)
        
        try:
            self.cpu_diagram_pixmap = QPixmap("assets/cpu-diagram01.PNG")
            if self.cpu_diagram_pixmap.isNull():
                QMessageBox.critical(self, "Error loading image", "Could not load CPU diagram image. Check path 'assets/cpu-diagram01.PNG'.")
                self.scene.addRect(0, 0, 1000, 600, QPen(QColor("red")), QBrush(QColor("lightgray")))
            else:
                self.scene.addPixmap(self.cpu_diagram_pixmap)
                self.scene.setSceneRect(QRectF(self.cpu_diagram_pixmap.rect()))
        except Exception as e:
            QMessageBox.critical(self, "Error loading image", f"An error occurred while loading image: {e}")
            self.scene.addRect(0, 0, 1000, 600, QPen(QColor("red")), QBrush(QColor("lightgray")))
        
        self.ram_group_box = QGroupBox("RAM (Instruction/Data)")
        self.ram_group_box_layout = QVBoxLayout(self.ram_group_box)
        
        self.ram_group_box.setFixedSize(180, 440) 
        
        self.ram_table = QTableWidget(16, 2)
        self.ram_table.setHorizontalHeaderLabels(["Addr", "Data (8-bit)"])
        for i in range(16):
            self.ram_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.ram_table.setItem(i, 1, QTableWidgetItem("00000000"))
        
        self.ram_table.setColumnWidth(0, 50)
        self.ram_table.setColumnWidth(1, 85)
        self.ram_table.verticalHeader().setDefaultSectionSize(20)
        
        self.ram_table.verticalHeader().setVisible(False)
        self.ram_group_box_layout.addWidget(self.ram_table)
        
        self.ram_proxy_widget = self.scene.addWidget(self.ram_group_box)
        
        self.setup_diagram_elements()
        QTimer.singleShot(0, self.adjust_diagram_scale)

        self.bottom_control_layout = QVBoxLayout()
        self.control_panel_layout.addLayout(self.bottom_control_layout, 1)
        
        self.loader_layout = QHBoxLayout()

        self.instr_loader_group_box = QGroupBox("Load Instruction")
        self.instr_loader_layout = QVBoxLayout(self.instr_loader_group_box)
        self.instr_loader_form = QFormLayout()
        
        self.instr_loader_group_box.setFixedHeight(130)

        self.instr_address_input = QLineEdit("0")
        self.instr_address_input.setPlaceholderText("0-15")
        self.instr_address_input.setFixedWidth(50)

        self.opcode_combo = QComboBox()
        for opcode_bits, info in self.cpu.opcode_map.items():
            self.opcode_combo.addItem(f"{info['name']} ({opcode_bits})", opcode_bits)
        
        self.opcode_combo.currentIndexChanged.connect(self._handle_opcode_change)

        self.data_for_instr_input = QLineEdit("0")
        self.data_for_instr_input.setPlaceholderText("4-bit value (0-15)")
        self.data_for_instr_input.setFixedWidth(80)

        self.load_instr_button = QPushButton("Load")
        self.load_instr_button.clicked.connect(self.load_instruction_gui)

        self.instr_loader_form.addRow(QLabel("Address:"), self.instr_address_input)
        self.instr_loader_form.addRow(QLabel("Opcode:"), self.opcode_combo)
        self.instr_loader_form.addRow(QLabel("Operand/Addr:"), self.data_for_instr_input)
        
        self.instr_loader_layout.addLayout(self.instr_loader_form)
        self.instr_loader_layout.addWidget(self.load_instr_button)
        
        self.loader_layout.addWidget(self.instr_loader_group_box)

        self.data_loader_group_box = QGroupBox("Load Data")
        self.data_loader_layout = QVBoxLayout(self.data_loader_group_box)
        self.data_loader_form = QFormLayout()
        
        self.data_loader_group_box.setFixedHeight(130)
        
        self.data_address_input = QLineEdit("0")
        self.data_address_input.setPlaceholderText("0-15")
        self.data_address_input.setFixedWidth(50)
        
        self.data_value_input = QLineEdit("0")
        self.data_value_input.setPlaceholderText("0-255")
        self.data_value_input.setFixedWidth(80)
        
        self.load_data_button = QPushButton("Load")
        self.load_data_button.clicked.connect(self.load_data_gui)
        
        self.data_loader_form.addRow(QLabel("Address:"), self.data_address_input)
        self.data_loader_form.addRow(QLabel("Value (Dec):"), self.data_value_input)
        
        self.data_loader_layout.addLayout(self.data_loader_form)
        self.data_loader_layout.addWidget(self.load_data_button)
        
        self.loader_layout.addWidget(self.data_loader_group_box)
        
        self.bottom_control_layout.addLayout(self.loader_layout)
        
        self._handle_opcode_change(0)

        self.instruction_guide_box = QGroupBox("Instruction Guide")
        self.instruction_guide_layout = QVBoxLayout(self.instruction_guide_box)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        guide_content_widget = QWidget()
        guide_content_layout = QVBoxLayout(guide_content_widget)
        
        guide_text = """
        <h3>Instruction Set Architecture (ISA) Guide</h3>
        <p><b>8-bit Instruction Structure: [4-bit Opcode] [4-bit Operand/Address]</b></p>
        <p>Each instruction is 8 bits long. The first 4 bits represent the operation code (opcode), and the last 4 bits are the operand or a memory address.</p>

        <p><b>Data Transfer Instructions:</b></p>
        <ul>
            <li>
                <b>LOAD_A (Opcode: 0001)</b>
                <ul>
                    <li><b>4-bit Opcode (0001):</b> Specifies the "Load into Register A" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>RAM Address</b>. The CPU fetches the 8-bit value from this address in RAM and loads it into Register A.</li>
                </ul>
            </li>
            <li>
                <b>LOAD_B (Opcode: 0010)</b>
                <ul>
                    <li><b>4-bit Opcode (0010):</b> Specifies the "Load into Register B" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>RAM Address</b>. The CPU fetches the 8-bit value from this address in RAM and loads it into Register B.</li>
                </ul>
            </li>
            <li>
                <b>STORE_A (Opcode: 0011)</b>
                <ul>
                    <li><b>4-bit Opcode (0011):</b> Specifies the "Store from Register A" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>RAM Address</b>. The 8-bit value from Register A is stored into this memory location in RAM.</li>
                </ul>
            </li>
            <li>
                <b>STORE_B (Opcode: 0100)</b>
                <ul>
                    <li><b>4-bit Opcode (0100):</b> Specifies the "Store from Register B" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>RAM Address</b>. The 8-bit value from Register B is stored into this memory location in RAM.</li>
                </ul>
            </li>
        </ul>

        <p><b>Arithmetic & Logic Instructions:</b></p>
        <ul>
            <li>
                <b>ADD (Opcode: 0101)</b>
                <ul>
                    <li><b>4-bit Opcode (0101):</b> Specifies the "Addition" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This field is hardcoded to <b>'1001'</b>. The first two bits ('10') represent the source Register B, and the last two bits ('01') represent the source Register A. The ALU performs the addition (Register B + Register A), and the 8-bit result is automatically stored back into Register A.</li>
                </ul>
            </li>
            <li>
                <b>SUB (Opcode: 0110)</b>
                <ul>
                    <li><b>4-bit Opcode (0110):</b> Specifies the "Subtraction" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This field is hardcoded to <b>'1001'</b>. The first two bits ('10') represent the source Register B, and the last two bits ('01') represent the source Register A. The ALU performs the subtraction (Register B - Register A), and the 8-bit result is automatically stored back into Register A.</li>
                </ul>
            </li>
        </ul>

        <p><b>Control Flow Instructions:</b></p>
        <ul>
            <li>
                <b>JUMP (Opcode: 0111)</b>
                <ul>
                    <li><b>4-bit Opcode (0111):</b> Specifies an unconditional "Jump" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>New Instruction Address</b>. The value in the Instruction Address Register (IAR) is updated to this new address, causing the CPU to fetch the next instruction from this location.</li>
                </ul>
            </li>
            <li>
                <b>JUMP_NEG (Opcode: 1000)</b>
                <ul>
                    <li><b>4-bit Opcode (1000):</b> Specifies a conditional "Jump if Negative" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>New Instruction Address</b>. The CPU checks the 'N' (Negative) flag. If the flag is set (true), the IAR is updated to this new address. Otherwise, the IAR is simply incremented.</li>
                </ul>
            </li>
            <li>
                <b>JUMP_ZERO (Opcode: 1001)</b>
                <ul>
                    <li><b>4-bit Opcode (1001):</b> Specifies a conditional "Jump if Zero" operation.</li>
                    <li><b>4-bit Operand/Address:</b> This is the <b>New Instruction Address</b>. The CPU checks the 'Z' (Zero) flag. If the flag is set (true), the IAR is updated to this new address. Otherwise, the IAR is simply incremented.</li>
                </ul>
            </li>
        </ul>

        <p><b>Other Instructions:</b></p>
        <ul>
            <li>
                <b>NOP (Opcode: 0000)</b>
                <ul>
                    <li><b>4-bit Opcode (0000):</b> Specifies the "No Operation" instruction.</li>
                    <li><b>4-bit Operand/Address:</b> This field is ignored. The CPU does nothing and simply increments the IAR to fetch the next instruction.</li>
                </ul>
            </li>
            <li>
                <b>HALT (Opcode: 1111)</b>
                <ul>
                    <li><b>4-bit Opcode (1111):</b> Specifies the "Halt" instruction.</li>
                    <li><b>4-bit Operand/Address:</b> This field is ignored. The CPU stops all operations and enters a halted state.</li>
                </ul>
            </li>
        </ul> 
        """
        guide_label = QLabel(guide_text)
        guide_label.setWordWrap(True)
        guide_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        guide_content_layout.addWidget(guide_label)
        guide_content_layout.addStretch()
        
        scroll_area.setWidget(guide_content_widget)
        
        self.instruction_guide_layout.addWidget(scroll_area)
        self.bottom_control_layout.addWidget(self.instruction_guide_box)
        
        self.reg_flag_layout = QHBoxLayout()
        self.reg_group_box = QGroupBox("CPU Registers")
        self.reg_layout = QVBoxLayout(self.reg_group_box)
        self.flags_group_box = QGroupBox("CPU Flags")
        self.flags_layout = QVBoxLayout(self.flags_group_box)

        self.reg_group_box.setFixedHeight(110)
        self.flags_group_box.setFixedHeight(110)

        self.setup_register_and_flag_display(self.reg_layout, self.flags_layout)

        self.reg_flag_layout.addWidget(self.reg_group_box)
        self.reg_flag_layout.addWidget(self.flags_group_box)

        self.bottom_control_layout.addLayout(self.reg_flag_layout)
        
    def _handle_opcode_change(self, index):
        opcode_bits = self.opcode_combo.currentData()
        opcode_info = self.cpu.opcode_map[opcode_bits]
        op_name = opcode_info['name']

        if op_name in ['ADD', 'SUB']:
            self.data_for_instr_input.setText("9")
            self.data_for_instr_input.setPlaceholderText("Fixed: 1001")
            self.data_for_instr_input.setEnabled(False)
        elif op_name in ['NOP', 'HALT']:
            self.data_for_instr_input.setText("0")
            self.data_for_instr_input.setPlaceholderText("Fixed: 0000")
            self.data_for_instr_input.setEnabled(False)
        else:
            self.data_for_instr_input.setText("0")
            self.data_for_instr_input.setPlaceholderText("4-bit value (0-15)")
            self.data_for_instr_input.setEnabled(True)

    def setup_register_and_flag_display(self, reg_layout, flags_layout):
        self.register_display_labels['IAR'] = QLabel("IAR: 0 (0000)")
        self.register_display_labels['IR_Opcode'] = QLabel("IR (Opcode): 0000")
        self.register_display_labels['IR_AddrData'] = QLabel("IR (Addr/Data): 0000")
        self.register_display_labels['A'] = QLabel("Reg A: 0 (00000000)")
        self.register_display_labels['B'] = QLabel("Reg B: 0 (00000000)")

        reg_layout.addWidget(self.register_display_labels['IAR'])
        reg_layout.addWidget(self.register_display_labels['IR_Opcode'])
        reg_layout.addWidget(self.register_display_labels['IR_AddrData'])
        reg_layout.addWidget(self.register_display_labels['A'])
        reg_layout.addWidget(self.register_display_labels['B'])

        self.flags_display_labels['Z'] = QLabel("Z: F")
        self.flags_display_labels['N'] = QLabel("N: F")
        self.flags_display_labels['O'] = QLabel("O: F")

        flags_layout.addWidget(self.flags_display_labels['Z'])
        flags_layout.addWidget(self.flags_display_labels['N'])
        flags_layout.addWidget(self.flags_display_labels['O'])

    def setup_diagram_elements(self):
        font = QFont("Arial", 10, QFont.Weight.Bold)

        self.diagram_text_items['IAR'] = self.scene.addText("00000000", font)
        self.diagram_rect_highlights['IAR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IAR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['IR_Opcode'] = self.scene.addText("0000", font)
        self.diagram_text_items['IR_AddrData'] = self.scene.addText("0000", font)
        self.diagram_rect_highlights['IR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['A'] = self.scene.addText("00000000", font)
        self.diagram_rect_highlights['A'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_A_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['B'] = self.scene.addText("00000000", font)
        self.diagram_rect_highlights['B'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_B_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))
        
        self.diagram_text_items['ALU_OUT'] = self.scene.addText("0", font)
        
        self.diagram_text_items['Z_flag'] = self.scene.addText("F", font)
        self.diagram_text_items['N_flag'] = self.scene.addText("F", font)
        self.diagram_text_items['O_flag'] = self.scene.addText("F", font)
        
        self.diagram_rect_highlights['ALU'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['ALU_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))
        self.diagram_rect_highlights['CONTROL_UNIT'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['CONTROL_UNIT_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.update_diagram_element_positions()
        
    def update_diagram_element_positions(self):
        if not hasattr(self, 'current_diagram_scale') or self.current_diagram_scale == 0:
            return

        font_size = 10 / self.current_diagram_scale
        font = QFont("Arial", int(font_size), QFont.Weight.Bold)

        # Cập nhật vị trí và font cho các giá trị trên sơ đồ
        self.diagram_text_items['IAR'].setPos(DIAGRAM_COORDS_ORIGINAL['IAR_VALUE_POS'])
        self.diagram_text_items['IAR'].setFont(font)

        self.diagram_text_items['IR_Opcode'].setPos(DIAGRAM_COORDS_ORIGINAL['IR_OPCODE_VALUE_POS'])
        self.diagram_text_items['IR_Opcode'].setFont(font)
        
        self.diagram_text_items['IR_AddrData'].setPos(DIAGRAM_COORDS_ORIGINAL['IR_ADDRDATA_VALUE_POS'])
        self.diagram_text_items['IR_AddrData'].setFont(font)

        self.diagram_text_items['A'].setPos(DIAGRAM_COORDS_ORIGINAL['REG_A_VALUE_POS'])
        self.diagram_text_items['A'].setFont(font)

        self.diagram_text_items['B'].setPos(DIAGRAM_COORDS_ORIGINAL['REG_B_VALUE_POS'])
        self.diagram_text_items['B'].setFont(font)

        self.diagram_text_items['ALU_OUT'].setPos(DIAGRAM_COORDS_ORIGINAL['ALU_OUT_VALUE_POS'])
        self.diagram_text_items['ALU_OUT'].setFont(font)
        
        self.diagram_text_items['Z_flag'].setPos(DIAGRAM_COORDS_ORIGINAL['FLAG_Z_VALUE_POS'])
        self.diagram_text_items['Z_flag'].setFont(font)
        
        self.diagram_text_items['N_flag'].setPos(DIAGRAM_COORDS_ORIGINAL['FLAG_N_VALUE_POS'])
        self.diagram_text_items['N_flag'].setFont(font)
        
        self.diagram_text_items['O_flag'].setPos(DIAGRAM_COORDS_ORIGINAL['FLAG_O_VALUE_POS'])
        self.diagram_text_items['O_flag'].setFont(font)

        # Cập nhật vị trí cho các khung highlight
        for key, item in self.diagram_rect_highlights.items():
            if key in DIAGRAM_COORDS_ORIGINAL:
                item.setRect(DIAGRAM_COORDS_ORIGINAL[key])
        
        if self.ram_proxy_widget:
            self.ram_proxy_widget.setPos(DIAGRAM_COORDS_ORIGINAL['RAM_TABLE_POS'])

    def update_gui_cpu_status(self):
        # Cập nhật RAM table
        for i in range(16):
            self.ram_table.setItem(i, 1, QTableWidgetItem(self.cpu.ram[i]))

        # Cập nhật các label trong control panel
        self.register_display_labels['A'].setText(f"Reg A: {self.cpu.registers['A']} ({self.cpu.registers['A']:08b})")
        self.register_display_labels['B'].setText(f"Reg B: {self.cpu.registers['B']} ({self.cpu.registers['B']:08b})")
        self.register_display_labels['IAR'].setText(f"IAR: {self.cpu.registers['IAR']} ({self.cpu.registers['IAR']:04b})")
        self.register_display_labels['IR_Opcode'].setText(f"IR (Opcode): {self.cpu.registers['IR_Opcode']}")
        self.register_display_labels['IR_AddrData'].setText(f"IR (Addr/Data): {self.cpu.registers['IR_AddrData']}")

        z_flag_status = 'T' if self.cpu.flags['Z'] else 'F'
        n_flag_status = 'T' if self.cpu.flags['N'] else 'F'
        o_flag_status = 'T' if self.cpu.flags['O'] else 'F'
        
        self.flags_display_labels['Z'].setText(f"Z: {z_flag_status}")
        self.flags_display_labels['N'].setText(f"N: {n_flag_status}")
        self.flags_display_labels['O'].setText(f"O: {o_flag_status}")

        # Cập nhật các text item trên sơ đồ
        self.diagram_text_items['IAR'].setPlainText(f"IAR: {self.cpu.registers['IAR']:04b}")
        self.diagram_text_items['IR_Opcode'].setPlainText(f"{self.cpu.registers['IR_Opcode']}")
        self.diagram_text_items['IR_AddrData'].setPlainText(f"{self.cpu.registers['IR_AddrData']}")
        self.diagram_text_items['A'].setPlainText(f"A: {self.cpu.registers['A']:08b}")
        self.diagram_text_items['B'].setPlainText(f"B: {self.cpu.registers['B']:08b}")
        
        # Chỉ cập nhật ALU_OUT khi có ALU ops
        if self.cpu.last_decoded_instruction and self.cpu.last_decoded_instruction['name'] in ['ADD', 'SUB']:
            alu_out_value = self.cpu.calculate_alu_output()
            self.diagram_text_items['ALU_OUT'].setPlainText(f"{alu_out_value}")
        else:
            self.diagram_text_items['ALU_OUT'].setPlainText("N/A")

        self.diagram_text_items['Z_flag'].setPlainText(f"Z: {z_flag_status}")
        self.diagram_text_items['N_flag'].setPlainText(f"N: {n_flag_status}")
        self.diagram_text_items['O_flag'].setPlainText(f"O: {o_flag_status}")
        
        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))
    #-------Process Function---------
    def load_instruction_gui(self):
        try:
            address_str = self.instr_address_input.text()
            if not address_str.isdigit():
                raise ValueError("Address must be a number.")

            address = int(address_str)
            if not (0 <= address <= 15):
                QMessageBox.warning(self, "Input error", "RAM address must be between 0 and 15.")
                return

            opcode_bits = self.opcode_combo.currentData()
            op_name = self.cpu.opcode_map[opcode_bits]['name']

            if op_name in ['ADD', 'SUB']:
                operand_bits = "1001"
            elif op_name in ['NOP', 'HALT']:
                operand_bits = "0000"
            else:
                operand_value_str = self.data_for_instr_input.text().strip()
                if not operand_value_str.isdigit():
                    QMessageBox.warning(self, "Input error", "Operand/Address must be a decimal number (0-15).")
                    return
                
                operand_value = int(operand_value_str)
                if not (0 <= operand_value <= 15):
                    QMessageBox.warning(self, "Input error", "Operand/Address value must be between 0 and 15.")
                    return
                
                operand_bits = f"{operand_value:04b}"

            full_instruction = opcode_bits + operand_bits
            self.cpu.load_ram(address, full_instruction)
            self.update_gui_cpu_status()
            QMessageBox.information(self, "Success", f"Loaded instruction '{full_instruction}' into RAM[{address}].")

        except ValueError as ve:
            QMessageBox.critical(self, "Input error", f"An error occurred: {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_data_gui(self):
        try:
            address_str = self.data_address_input.text()
            address = int(address_str)
            if not (0 <= address <= 15):
                QMessageBox.warning(self, "Input error", "RAM address must be between 0 and 15.")
                return

            value_str = self.data_value_input.text()
            value = int(value_str)
            if not (0 <= value <= 255):
                QMessageBox.warning(self, "Input error", "Data value must be between 0 and 255.")
                return

            binary_value = f"{value:08b}"
            
            self.cpu.load_ram(address, binary_value)
            self.update_gui_cpu_status()
            QMessageBox.information(self, "Success", f"Loaded data '{binary_value}' (Dec: {value}) into RAM[{address}].")
        except ValueError:
            QMessageBox.critical(self, "Input error", "Please enter valid address and value.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            
    def _clear_all_highlights_and_animations(self):
        # Sửa: Trước hết dừng timer để không gọi _advance_cpu_phase
        self.cpu_phase_timer.stop()
        
        # Sửa: Gọi clear_animations để xóa các item animation, điều này sẽ trigger finished signal
        self.signal_animator.clear_animations()
        
        # Sửa: Clear highlights sau khi animations đã kết thúc
        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

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
        # Thêm xử lý highlight cho RAM table
        elif component_key == 'RAM_TABLE_POS':
            self.ram_group_box.setStyleSheet("QGroupBox { border: 2px solid red; }")
            QTimer.singleShot(duration, lambda: self.ram_group_box.setStyleSheet("QGroupBox {}"))

    def _reset_single_highlight(self, component_key):
        if component_key in self.diagram_rect_highlights:
            self.diagram_rect_highlights[component_key].setPen(QPen(Qt.GlobalColor.transparent))
            self.diagram_rect_highlights[component_key].setBrush(QBrush(Qt.GlobalColor.transparent))

    def _animate_signal(self, path_name, color=Qt.GlobalColor.red):
        if path_name in SIGNAL_PATHS_ORIGINAL:
            scaled_path = [p for p in SIGNAL_PATHS_ORIGINAL[path_name]]
            # Sửa: gọi animate_path nhưng không gọi start_animation ở đây nữa
            # Việc start sẽ được thực hiện sau đó một cách có chủ đích
            self.signal_animator.animate_path(scaled_path, color, duration=self.animation_step_duration)
        else:
            print(f"Error: Signal path '{path_name}' is not defined.")
            
    def _run_next_phase_after_delay(self, delay=50):
        # Thêm một chút delay để UI có thời gian cập nhật
        QTimer.singleShot(delay, self._advance_cpu_phase)

    def _on_animation_finished(self):
        """Callback được gọi khi một animation kết thúc."""
        self.is_animating = False
        self._clear_all_highlights_and_animations()
        
        # Dựa vào pha hiện tại để quyết định hành động tiếp theo
        if self.cpu_current_phase == 'FETCH':
            # Hoàn thành animation Fetch, giờ chuyển sang Decode
            self._handle_decode_phase()
        elif self.cpu_current_phase == 'DECODE_EXECUTE':
            # Hoàn thành animation Decode/Execute, giờ chuyển sang Fetch tiếp theo
            if self.is_running_mode:
                self._start_new_instruction_cycle()
            else:
                self.step_button.setEnabled(True)
                self.run_button.setEnabled(True)
                self.reset_button.setEnabled(True)
        elif self.cpu_current_phase == 'IDLE':
            # Đã xong một chu kỳ
            if self.is_running_mode:
                self._start_new_instruction_cycle()
            else:
                self.step_button.setEnabled(True)
                self.run_button.setEnabled(True)
                self.reset_button.setEnabled(True)

    def run_cpu(self):
        if not self.is_running_mode:
            # Nếu người dùng bấm Run lần đầu tiên (hoặc sau khi Reset),
            # hãy đảm bảo IAR về 0 để chạy từ đầu
            if self.cpu.registers['IAR'] != 0:
                self.cpu.reset() # Chỉ reset các thanh ghi, KHÔNG reset RAM.
                
        self.is_running_mode = True
        self.step_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.reset_button.setEnabled(True)
        
        # Bắt đầu chu kỳ CPU đầu tiên
        self._start_new_instruction_cycle()

    def step_cpu(self):
        # Nếu đang ở chế độ Run, bạn cần dừng chu kỳ tự động
        if self.is_running_mode:
            self.cpu_phase_timer.stop()
            self.is_running_mode = False
        
        # Kích hoạt lại các nút điều khiển
        self.step_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.reset_button.setEnabled(True)
        
        # Bắt đầu một chu kỳ lệnh duy nhất
        self._start_new_instruction_cycle()

    def reset_cpu(self):
        self._clear_all_highlights_and_animations()
        self.cpu.reset()
        self.cpu_current_phase = 'IDLE'
        self.is_running_mode = False
        self.is_animating = False
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        self.update_gui_cpu_status()
        self.cpu_phase_timer.stop() # Dừng timer nếu đang chạy

    def _start_new_instruction_cycle(self):
        """ Bắt đầu một chu kỳ lệnh mới từ pha FETCH. """
        self.cpu_current_phase = 'FETCH'
        self._advance_cpu_phase()

    def _advance_cpu_phase(self):
        """
        Tiến hành từng pha của chu kỳ lệnh CPU.
        Hàm này sẽ được gọi bởi timer, xử lý đúng một pha rồi dừng.
        Animation finished sẽ gọi lại hàm này.
        """
        # Xóa các highlight và animation của pha trước
        self._clear_all_highlights_and_animations()
        self.update_gui_cpu_status()

        current_phase = self.cpu_current_phase

        if current_phase == 'FETCH':
            self._handle_fetch_phase()
        elif current_phase == 'DECODE':
            self._handle_decode_phase()
        elif current_phase == 'EXECUTE':
            self._handle_execute_phase()
        elif current_phase == 'HALT':
            print("CPU Halted.")
            self.reset_cpu()
            
    def _handle_fetch_phase(self):
        self.highlight_component('IAR')
        self.highlight_component('RAM_TABLE_POS')
        self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.cyan)
        
        # Sau khi animation xong, hàm _on_animation_finished sẽ được gọi để chuyển sang pha DECODE
        # Không gọi timer ở đây nữa

    def _handle_decode_phase(self):
        instruction = self.cpu.fetch_instruction()
        print(f"Fetch: RAM[{self.cpu.registers['IAR']}] -> IR ({instruction})")

        self.highlight_component('RAM_TABLE_POS')
        self.highlight_component('IR')
        self._animate_signal('RAM_DATA_TO_IR', Qt.GlobalColor.green)

        # Chuyển sang pha DECODE chính thức
        self.cpu_current_phase = 'DECODE_EXECUTE'
        # Animation finished sẽ gọi lại hàm _advance_cpu_phase() để thực hiện decode và execute
    
    def _handle_decode_execute_phase(self):
        # Bước này gộp cả Decode và Execute
        self.highlight_component('IR')
        self.highlight_component('CONTROL_UNIT')
        self._animate_signal('IR_TO_CONTROL_UNIT', Qt.GlobalColor.magenta)
        
        # Decode instruction
        decoded_instruction = self.cpu.decode_instruction()
        op_name = decoded_instruction.get('name', 'UNKNOWN')
        operand_value = decoded_instruction.get('operand', 'N/A')
        print(f"Decode: Opcode: {op_name} (Operand: {operand_value})")

        # Execute instruction
        if op_name in ['LOAD_A', 'LOAD_B', 'STORE_A', 'STORE_B']:
            # Lỗi "operand not found" có thể được xử lý ở đây
            if operand_value == 'N/A':
                QMessageBox.warning(self, "Execution Error", "Operand not found for memory instruction!")
                self.reset_cpu()
                return

            addr = int(operand_value, 2)
            if op_name == 'LOAD_A':
                self.cpu.execute_load_a(addr)
                print(f"Execute: LOAD_A from RAM[{addr}] -> A")
                self._animate_signal('RAM_DATA_TO_REG_A', Qt.GlobalColor.blue)
                self.highlight_component('RAM_TABLE_POS')
                self.highlight_component('A')
            elif op_name in ['LOAD_A', 'LOAD_B']:
                self.highlight_component('IR', Qt.GlobalColor.green)
                self.highlight_component('RAM_TABLE_POS', Qt.GlobalColor.red)
                self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.red)
                self.is_animating = True
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'LOAD_DATA_FROM_RAM'
                
            elif op_name in ['STORE_A', 'STORE_B']:
                self.highlight_component('IR', Qt.GlobalColor.green)
                self.highlight_component('A' if op_name == 'STORE_A' else 'B', Qt.GlobalColor.blue)
                self._animate_signal('REG_A_TO_RAM_DATA_BUS' if op_name == 'STORE_A' else 'REG_B_TO_RAM_DATA_BUS', Qt.GlobalColor.blue)
                self.is_animating = True
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'STORE_DATA_TO_RAM'
        
        elif op_name in ['ADD', 'SUB']:
            self.highlight_component('A', Qt.GlobalColor.green)
            self.highlight_component('B', Qt.GlobalColor.green)
            self.highlight_component('ALU', Qt.GlobalColor.magenta)
            self._animate_signal('REG_A_TO_ALU', Qt.GlobalColor.darkCyan)
            self._animate_signal('REG_B_TO_ALU', Qt.GlobalColor.darkCyan)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'EXECUTE_ALU_DONE'
        elif op_name in ['JUMP', 'JUMP_NEG', 'JUMP_ZERO']:
            self.highlight_component('IR', Qt.GlobalColor.yellow)
            self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.red)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'JUMP_DONE'
        elif op_name == 'NOP':
            print("Execute: NOP (No Operation)")
        elif op_name == 'HALT':
            self.cpu_current_phase = 'HALT'
        if op_name not in ['JUMP', 'JUMP_NEG', 'JUMP_ZERO', 'HALT']:
            self.cpu.increment_iar()
            
        self.update_gui_cpu_status()
        self.is_animating = True # Bắt đầu animation cho pha execute

        # Kết thúc chu kỳ, chuyển sang pha IDLE để bắt đầu chu kỳ mới (nếu đang chạy)
        self.cpu_current_phase = 'IDLE'


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CPUVisualizerApp()
    ex.show()
    sys.exit(app.exec())

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
    # Tọa độ chữ (text)
    'IAR_TEXT_POS': QPointF(510, 150),
    'IR_OPCODE_TEXT_POS': QPointF(670, 240),
    'IR_ADDRDATA_TEXT_POS': QPointF(670, 260),
    'REG_A_TEXT_POS': QPointF(200, 260),
    'REG_B_TEXT_POS': QPointF(370, 260),
    'ALU_OUT_TEXT_POS': QPointF(280, 430),
    'FLAG_Z_POS': QPointF(400, 450),
    'FLAG_N_POS': QPointF(400, 470),
    'FLAG_O_POS': QPointF(400, 490),
    
    # Tọa độ mới cho bảng RAM (Proxy Widget)
    'RAM_TABLE_POS': QPointF(640, 60),
    
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

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.diagram_text_items = {}
        self.diagram_rect_highlights = {}
        self.register_display_labels = {}
        self.flags_display_labels = {}
        
        self.ram_proxy_widget = None

        self.cpu_current_phase = 'IDLE'
        self.cpu_phase_timer = QTimer(self)
        self.cpu_phase_timer.setInterval(500)
        self.cpu_phase_timer.timeout.connect(self._advance_cpu_phase)

        self.animation_step_duration = 500
        self.current_diagram_scale = 1.0

        self.init_ui()
        self.update_gui_cpu_status()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        QTimer.singleShot(10, self.adjust_diagram_scale)

    def adjust_diagram_scale(self):
        if not hasattr(self, 'cpu_diagram_pixmap') or not self.cpu_diagram_pixmap or self.cpu_diagram_pixmap.isNull():
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
                QMessageBox.critical(self, "Error loading image", "Could not Fload CPU diagram image. Check path 'assets/cpu-diagram.PNG'.")
                self.scene.addRect(0, 0, 1000, 600, QPen(QColor("red")), QBrush(QColor("lightgray")))
            else:
                self.scene.addPixmap(self.cpu_diagram_pixmap)
                self.scene.setSceneRect(QRectF(self.cpu_diagram_pixmap.rect()))
        except Exception as e:
            QMessageBox.critical(self, "Error loading image", f"An error occurred while loading image: {e}")
            self.scene.addRect(0, 0, 1000, 600, QPen(QColor("red")), QBrush(QColor("lightgray")))
        
        self.ram_group_box = QGroupBox("RAM (Instruction/Data)")
        self.ram_group_box_layout = QVBoxLayout(self.ram_group_box)
        
        self.ram_group_box.setFixedSize(162, 400) 
        
        self.ram_table = QTableWidget(16, 2)
        self.ram_table.setHorizontalHeaderLabels(["Addr", "Data (8-bit)"])
        for i in range(16):
            self.ram_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.ram_table.setItem(i, 1, QTableWidgetItem("00000000"))
        
        self.ram_table.setColumnWidth(0, 40)
        self.ram_table.setColumnWidth(1, 80)
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
        opcode_bits = self.opcode_combo.itemData(index)
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

        self.diagram_text_items['IAR'] = self.scene.addText("IAR: 0000", font)
        self.diagram_rect_highlights['IAR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IAR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['IR_Opcode'] = self.scene.addText("Op:0000", font)
        self.diagram_text_items['IR_AddrData'] = self.scene.addText("Ad:0000", font)
        self.diagram_rect_highlights['IR'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['IR_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['A'] = self.scene.addText("A: 00000000", font)
        self.diagram_rect_highlights['A'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_A_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['B'] = self.scene.addText("B: 00000000", font)
        self.diagram_rect_highlights['B'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['REG_B_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.diagram_text_items['Z_flag'] = self.scene.addText("Z: F", font)
        self.diagram_text_items['N_flag'] = self.scene.addText("N: F", font)
        self.diagram_text_items['O_flag'] = self.scene.addText("O: F", font)
        
        self.diagram_rect_highlights['ALU'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['ALU_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))
        self.diagram_rect_highlights['CONTROL_UNIT'] = self.scene.addRect(DIAGRAM_COORDS_ORIGINAL['CONTROL_UNIT_RECT'], QPen(Qt.GlobalColor.transparent), QBrush(Qt.GlobalColor.transparent))

        self.update_diagram_element_positions()
        
    def update_diagram_element_positions(self):
        if not hasattr(self, 'current_diagram_scale') or self.current_diagram_scale == 0:
            return

        scale = self.current_diagram_scale
        font_size = 10 / scale
        font = QFont("Arial", int(font_size), QFont.Weight.Bold)

        for key, item in self.diagram_text_items.items():
            if key in DIAGRAM_COORDS_ORIGINAL:
                original_pos = DIAGRAM_COORDS_ORIGINAL[key]
                item.setPos(original_pos)
                item.setFont(font)
            elif key.endswith('_flag'):
                original_pos_key = key.replace('_flag', '_POS')
                if original_pos_key in DIAGRAM_COORDS_ORIGINAL:
                    original_pos = DIAGRAM_COORDS_ORIGINAL[original_pos_key]
                    item.setPos(original_pos)
                    item.setFont(font)

        for key, item in self.diagram_rect_highlights.items():
            if key in DIAGRAM_COORDS_ORIGINAL:
                original_rect = DIAGRAM_COORDS_ORIGINAL[key]
                item.setRect(original_rect)

        if self.ram_proxy_widget:
            self.ram_proxy_widget.setPos(DIAGRAM_COORDS_ORIGINAL['RAM_TABLE_POS'])

    def update_gui_cpu_status(self):
        for i in range(16):
            self.ram_table.setItem(i, 1, QTableWidgetItem(self.cpu.ram[i]))

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
        
        self.diagram_text_items['Z_flag'].setPlainText(f"Z: {z_flag_status}")
        self.diagram_text_items['N_flag'].setPlainText(f"N: {n_flag_status}")
        self.diagram_text_items['O_flag'].setPlainText(f"O: {o_flag_status}")
        
        self.flags_display_labels['Z'].setText(f"Z: {z_flag_status}")
        self.flags_display_labels['N'].setText(f"N: {n_flag_status}")
        self.flags_display_labels['O'].setText(f"O: {o_flag_status}")

        for rect_item in self.diagram_rect_highlights.values():
            rect_item.setPen(QPen(Qt.GlobalColor.transparent))
            rect_item.setBrush(QBrush(Qt.GlobalColor.transparent))

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
            scaled_path = [QPointF(p.x(), p.y()) for p in SIGNAL_PATHS_ORIGINAL[path_name]]
            self.signal_animator.animate_path(scaled_path, color, duration=self.animation_step_duration)
        else:
            print(f"Error: Signal path '{path_name}' is not defined.")

    def run_cpu(self):
        if self.cpu.is_halted:
            QMessageBox.information(self, "CPU Halted", "CPU is in a halted state. Please press 'Reset' to restart.")
            return

        if self.cpu_phase_timer.isActive():
            self.cpu_phase_timer.stop()
            self.run_button.setText("Run")
        else:
            self.run_button.setText("Pause")
            self.cpu_phase_timer.start()

    def step_cpu(self):
        if self.cpu.is_halted:
            if hasattr(self, 'cpu_phase_timer') and self.cpu_phase_timer.isActive():
                self.cpu_phase_timer.stop()
            QMessageBox.information(self, "CPU Halted", "CPU has halted. Please press 'Reset' to restart.")
            self.cpu_current_phase = 'IDLE'
            return

        self._clear_all_highlights_and_animations()
        
        self.cpu_phase_timer.start()
        self.run_button.setEnabled(False)
        self.step_button.setEnabled(False)

    def _advance_cpu_phase(self):
        if self.cpu.is_halted:
            self.cpu_phase_timer.stop()
            self.cpu_current_phase = 'IDLE'
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)
            self.update_gui_cpu_status()
            QMessageBox.information(self, "CPU Halted", "CPU đã dừng. Vui lòng nhấn 'Reset' để bắt đầu lại.")
            return

        if self.cpu_current_phase == 'IDLE':
            self.cpu_current_phase = 'FETCH'
            self.cpu_phase_timer.stop()
            QTimer.singleShot(10, self._advance_cpu_phase)
            return

        elif self.cpu_current_phase == 'FETCH':
            self.highlight_component('IAR', Qt.GlobalColor.red)
            self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.red)
            self.signal_animator.start_animation()
            QTimer.singleShot(self.animation_step_duration + 50, self._continue_after_animation)
            self.cpu_current_phase = 'FETCH_DONE'
        
        elif self.cpu_current_phase == 'FETCH_DONE':
            self.cpu.fetch_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.cpu_current_phase = 'DECODE'
            QTimer.singleShot(50, self._advance_cpu_phase)

        elif self.cpu_current_phase == 'DECODE':
            self.highlight_component('IR', Qt.GlobalColor.green)
            self._animate_signal('RAM_DATA_TO_IR', Qt.GlobalColor.green)
            self.signal_animator.start_animation()
            QTimer.singleShot(self.animation_step_duration + 50, self._continue_after_animation)
            self.cpu_current_phase = 'DECODE_DONE'

        elif self.cpu_current_phase == 'DECODE_DONE':
            self.cpu.decode_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.cpu_current_phase = 'EXECUTE'
            QTimer.singleShot(50, self._advance_cpu_phase)

        elif self.cpu_current_phase == 'EXECUTE':
            decoded_instruction = self.cpu.last_decoded_instruction
            op_name = decoded_instruction['name']

            if op_name in ['ADD', 'SUB']:
                self.highlight_component('A', Qt.GlobalColor.green)
                self.highlight_component('B', Qt.GlobalColor.green)
                self.highlight_component('ALU', Qt.GlobalColor.magenta)
                self._animate_signal('REG_A_TO_ALU', Qt.GlobalColor.darkCyan)
                self._animate_signal('REG_B_TO_ALU', Qt.GlobalColor.darkCyan)
                self.signal_animator.start_animation()
                QTimer.singleShot(self.animation_step_duration + 50, self._continue_after_alu_op)
                self.cpu_current_phase = 'EXECUTE_DONE'
                return
            elif op_name in ['LOAD_A', 'LOAD_B']:
                self.highlight_component('IR', Qt.GlobalColor.green)
                self.highlight_component('RAM_TABLE_POS', Qt.GlobalColor.red)
                self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.red)
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'LOAD_DATA_FROM_RAM'
                QTimer.singleShot(self.animation_step_duration + 50, self._advance_cpu_phase)
                return
            elif op_name in ['STORE_A', 'STORE_B']:
                self.highlight_component('IR', Qt.GlobalColor.green)
                self.highlight_component('A' if op_name == 'STORE_A' else 'B', Qt.GlobalColor.blue)
                self._animate_signal('REG_A_TO_RAM_DATA_BUS' if op_name == 'STORE_A' else 'REG_B_TO_RAM_DATA_BUS', Qt.GlobalColor.blue)
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'STORE_DATA_TO_RAM'
                QTimer.singleShot(self.animation_step_duration + 50, self._advance_cpu_phase)
                return
            elif op_name in ['JUMP', 'JUMP_NEG', 'JUMP_ZERO']:
                self.highlight_component('IR', Qt.GlobalColor.yellow)
                self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.red)
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'JUMP_DONE'
                QTimer.singleShot(self.animation_step_duration + 50, self._advance_cpu_phase)
                return
            elif op_name == 'HALT':
                self.cpu.execute_instruction()
                self.update_gui_cpu_status()
                self.highlight_component('CONTROL_UNIT', Qt.GlobalColor.red)
                self.cpu_current_phase = 'IDLE'
                self.cpu.is_halted = True
                self.run_button.setEnabled(True)
                self.step_button.setEnabled(True)
                self.cpu_phase_timer.stop()
                return

            self.cpu_current_phase = 'EXECUTE_DONE'
            self._advance_cpu_phase()
            
        elif self.cpu_current_phase == 'EXECUTE_DONE':
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.cpu_current_phase = 'INCREMENT_IAR'
            QTimer.singleShot(50, self._advance_cpu_phase)

        elif self.cpu_current_phase == 'LOAD_DATA_FROM_RAM':
            op_name = self.cpu.last_decoded_instruction['name']
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.highlight_component('A' if op_name == 'LOAD_A' else 'B', Qt.GlobalColor.blue)
            self._animate_signal('RAM_DATA_TO_REG_A' if op_name == 'LOAD_A' else 'RAM_DATA_TO_REG_B', Qt.GlobalColor.blue)
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'INCREMENT_IAR'
            QTimer.singleShot(self.animation_step_duration + 50, self._advance_cpu_phase)
            
        elif self.cpu_current_phase == 'STORE_DATA_TO_RAM':
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.highlight_component('RAM_TABLE_POS', Qt.GlobalColor.blue)
            self.cpu_current_phase = 'INCREMENT_IAR'
            QTimer.singleShot(50, self._advance_cpu_phase)

        elif self.cpu_current_phase == 'JUMP_DONE':
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.highlight_component('IAR', Qt.GlobalColor.yellow)
            self.cpu_current_phase = 'IDLE'
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)
            
        elif self.cpu_current_phase == 'INCREMENT_IAR':
            self.cpu.increment_iar()
            self.update_gui_cpu_status()
            self._clear_all_highlights_and_animations()
            self.highlight_component('IAR', Qt.GlobalColor.green)
            self.cpu_current_phase = 'IDLE'
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)
            
        else:
            self.cpu_phase_timer.stop()
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)

    def _continue_after_animation(self):
        self.signal_animator.clear_animations()
        self.cpu_phase_timer.start()

    def _continue_after_alu_op(self):
        self.signal_animator.clear_animations()
        self.cpu.execute_instruction()
        self.update_gui_cpu_status()
        self._clear_all_highlights_and_animations()
        
        # Highlight REG A and animate signal back from ALU to A
        self.highlight_component('A', Qt.GlobalColor.green)
        self.highlight_component('ALU', Qt.GlobalColor.magenta)
        self._animate_signal('ALU_TO_REG_A', Qt.GlobalColor.darkCyan)
        self.signal_animator.start_animation()
        
        self.cpu_current_phase = 'INCREMENT_IAR'
        QTimer.singleShot(self.animation_step_duration + 50, self._advance_cpu_phase)

    def reset_cpu(self):
        self.cpu.reset()
        self.update_gui_cpu_status()
        self._clear_all_highlights_and_animations()
        self.cpu_phase_timer.stop()
        self.cpu_current_phase = 'IDLE'
        self.run_button.setText("Run")
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        QMessageBox.information(self, "Reset", "CPU đã được reset về trạng thái ban đầu.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CPUVisualizerApp()
    ex.show()
    sys.exit(app.exec())
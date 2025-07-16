import sys

# Import từ PyQt6.QtWidgets
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QGraphicsView,
    QGraphicsScene, QComboBox, QLineEdit, QFormLayout, QMessageBox,
    QGraphicsRectItem, QGroupBox, QGraphicsPathItem, QGraphicsProxyWidget,
    QScrollArea, QTabWidget, QTextEdit
)

# Import từ PyQt6.QtGui
from PyQt6.QtGui import (
    QPixmap, QColor, QPen, QFont, QBrush, QTransform, QResizeEvent,
    QPainterPath
)

# Import từ PyQt6.QtCore
from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QSequentialAnimationGroup,
    QObject, pyqtSignal, QCoreApplication, QSize # Thêm QSize
)

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
    'IAR_RECT': QRectF(427, 400, 105, 30),
    'IR_RECT': QRectF(425, 320, 115, 37),
    'REG_A_RECT': QRectF(32, 108, 112, 44),
    'REG_B_RECT': QRectF(189, 108, 112, 44),
    'ALU_RECT': QRectF(70, 370, 90, 60),
    'CONTROL_UNIT_RECT': QRectF(292, 280, 265, 200),
}
SIGNAL_PATHS_ORIGINAL = {
    'IAR_TO_RAM_ADDR_BUS': [QPointF(430, 450), QPointF(695, 450)],
    'RAM_DATA_TO_IR': [QPointF(695, 400),  QPointF(430, 400)],
    'IR_TO_CONTROL_UNIT': [QPointF(430, 330), QPointF(500, 330)],
    'RAM_DATA_TO_REG_A': [QPointF(695, 37), QPointF(70,37), QPointF(70, 120)],
    'RAM_DATA_TO_REG_B': [QPointF(695, 37), QPointF(220, 37),  QPointF(230, 120)],
    'REG_A_TO_RAM_DATA_BUS': [QPointF(50, 120), QPointF(450, 240), QPointF(450, 250), QPointF(695, 67)],
    'REG_B_TO_RAM_DATA_BUS': [ QPointF(200, 120), QPointF(450, 240), QPointF(450, 250), QPointF(695, 67)],
    'REG_A_TO_ALU': [QPointF(50, 120),  QPointF(400, 330)],
    'REG_B_TO_ALU': [QPointF(200, 120), QPointF(460, 360), QPointF(400, 330)],
    'ALU_TO_REG_A': [ QPointF(400, 330), QPointF(50, 120)],
    'ADDR_TO_IAR_JUMP': [ QPointF(500, 330), QPointF(690, 120), QPointF(430, 400)],
}

class EmittingStream(QObject):
    textWritten = pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))
        QCoreApplication.processEvents() # Cần thiết để cập nhật ngay lập tức

    def flush(self):
        pass

class CPUVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPU Execution Visualizer")
        self.setGeometry(100, 100, 1500, 1000)

        self.cpu = CPU()
        self.scene = QGraphicsScene()
        # Sửa: Khởi tạo SignalAnimator trong main.py
        self.signal_animator = SignalAnimator(self.scene)
        # Sửa: Kết nối tín hiệu finished của animation group với một hàm callback
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
        # Tạo một widget trung tâm cho QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Thiết lập bố cục tổng thể cho widget trung tâm
        self.main_layout = QHBoxLayout(central_widget)

        # 1. Cột trái: Loaders và Registers/Flags
        self.left_panel_layout = QVBoxLayout()
        self.main_layout.addLayout(self.left_panel_layout, 1)

        # Loaders - Sắp xếp theo chiều dọc
        self.instr_loader_group_box = QGroupBox("Load Instruction")
        self.instr_loader_layout = QVBoxLayout(self.instr_loader_group_box)
        self.instr_loader_form = QFormLayout()
        
        self.instr_address_input = QLineEdit("0")
        self.instr_address_input.setPlaceholderText("0-15")
        self.instr_address_input.setFixedWidth(50)

        self.opcode_combo = QComboBox()
        for opcode_bits, info in self.cpu.opcode_map.items():
            self.opcode_combo.addItem(f"{info['name']} ({opcode_bits})", opcode_bits)
        
        self.opcode_combo.currentIndexChanged.connect(self._handle_opcode_change)

        self.data_for_instr_input = QLineEdit("0")
        self.data_for_instr_input.setPlaceholderText("4-bit value (0-15)")
        self.data_for_instr_input.setFixedWidth(60)

        self.load_instr_button = QPushButton("Load")
        self.load_instr_button.clicked.connect(self.load_instruction_gui)

        self.instr_loader_form.addRow(QLabel("Address:"), self.instr_address_input)
        self.instr_loader_form.addRow(QLabel("Opcode:"), self.opcode_combo)
        self.instr_loader_form.addRow(QLabel("Operand/Addr:"), self.data_for_instr_input)
        
        load_instr_button_layout = QHBoxLayout()
        load_instr_button_layout.addStretch()
        load_instr_button_layout.addWidget(self.load_instr_button)
        load_instr_button_layout.addStretch()
        
        self.instr_loader_layout.addLayout(self.instr_loader_form)
        self.instr_loader_layout.addLayout(load_instr_button_layout)
        
        self.left_panel_layout.addWidget(self.instr_loader_group_box)

        self.data_loader_group_box = QGroupBox("Load Data")
        self.data_loader_layout = QVBoxLayout(self.data_loader_group_box)
        self.data_loader_form = QFormLayout()
        
        self.data_address_input = QLineEdit("0")
        self.data_address_input.setPlaceholderText("0-15")
        self.data_address_input.setFixedWidth(60)
        
        self.data_value_input = QLineEdit("0")
        self.data_value_input.setPlaceholderText("0-255")
        self.data_value_input.setFixedWidth(60)
        
        self.load_data_button = QPushButton("Load")
        self.load_data_button.clicked.connect(self.load_data_gui)
        
        self.data_loader_form.addRow(QLabel("Address:"), self.data_address_input)
        self.data_loader_form.addRow(QLabel("Value (Dec):"), self.data_value_input)
        
        load_data_button_layout = QHBoxLayout()
        load_data_button_layout.addStretch()
        load_data_button_layout.addWidget(self.load_data_button)
        load_data_button_layout.addStretch()
        
        self.data_loader_layout.addLayout(self.data_loader_form)
        self.data_loader_layout.addLayout(load_data_button_layout)
        
        self.left_panel_layout.addWidget(self.data_loader_group_box)

        # Registers and Flags - Sắp xếp theo chiều dọc
        self.reg_group_box = QGroupBox("CPU Registers")
        self.reg_layout = QVBoxLayout(self.reg_group_box)
        self.flags_group_box = QGroupBox("CPU Flags")
        self.flags_layout = QVBoxLayout(self.flags_group_box)

        self.setup_register_and_flag_display(self.reg_layout, self.flags_layout)
        
        self.left_panel_layout.addWidget(self.reg_group_box)
        self.left_panel_layout.addWidget(self.flags_group_box)
        
        self.left_panel_layout.addStretch(1)
        
        # 2. Cột giữa: Sơ đồ CPU
        self.diagram_layout = QVBoxLayout()
        # Giảm chiều rộng của cột sơ đồ CPU
        self.main_layout.addLayout(self.diagram_layout, 4)

        # Các nút điều khiển
        self.top_buttons_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.step_button = QPushButton("Step")
        self.reset_button = QPushButton("Reset")
        
        # Điều chỉnh chiều cao của các nút điều khiển
        button_height = 35
        self.run_button.setFixedSize(QSize(70, button_height))
        self.step_button.setFixedSize(QSize(70, button_height))
        self.reset_button.setFixedSize(QSize(70, button_height))
        
        self.run_button.clicked.connect(self.run_cpu)
        self.step_button.clicked.connect(self.step_cpu)
        self.reset_button.clicked.connect(self.reset_cpu)

        self.top_buttons_layout.addWidget(self.run_button)
        self.top_buttons_layout.addWidget(self.step_button)
        self.top_buttons_layout.addWidget(self.reset_button)
        self.diagram_layout.addLayout(self.top_buttons_layout)
        
        # Vùng hiển thị sơ đồ
        self.view = QGraphicsView(self.scene)
        self.diagram_layout.addWidget(self.view)
        
        # Tải sơ đồ CPU
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
        
        # Bảng RAM
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

        # 3. Cột phải: Tab Widget
        self.right_panel_layout = QVBoxLayout()
        # Giảm chiều rộng của cột bên phải bằng cách giảm stretch factor
        self.main_layout.addLayout(self.right_panel_layout, 2)
        
        self.tab_widget = QTabWidget()
        self.right_panel_layout.addWidget(self.tab_widget)

        # Tab 1: Output Terminal
        self.terminal_tab = QWidget()
        self.terminal_layout = QVBoxLayout(self.terminal_tab)
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("background-color: black; color: #00FF00;")
        
        self.terminal_layout.addWidget(self.terminal_output)
        
        # Thêm các button chức năng cho terminal
        self.terminal_buttons_layout = QHBoxLayout()
        self.clear_terminal_button = QPushButton("Clear Terminal")
        self.clear_terminal_button.clicked.connect(self.terminal_output.clear)
        
        self.terminal_buttons_layout.addStretch()
        self.terminal_buttons_layout.addWidget(self.clear_terminal_button)
        self.terminal_buttons_layout.addStretch()
        
        self.terminal_layout.addLayout(self.terminal_buttons_layout)
        
        self.tab_widget.addTab(self.terminal_tab, "Output Terminal")
        
        # Chuyển hướng stdout
        sys.stdout = EmittingStream()
        sys.stdout.textWritten.connect(self.terminal_output.insertPlainText)
        
        # Tab 2: Instruction Guide
        self.guide_tab = QWidget()
        self.guide_layout = QVBoxLayout(self.guide_tab)
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
        self.guide_layout.addWidget(self.instruction_guide_box)
        self.tab_widget.addTab(self.guide_tab, "Instruction Guide")

        # Gọi hàm xử lý thay đổi opcode lần đầu tiên
        self._handle_opcode_change(0)
            
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
            
            # Sửa: Gọi hàm tải lệnh chuyên biệt để in ra output đúng
            self.cpu.load_instruction(address, full_instruction)
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
            
          
            self.cpu.write_ram(address, binary_value)
            print(f"Loaded data: RAM[{address}] = {binary_value} (Decimal: {value})")
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
        # Đây là callback được gọi khi animation kết thúc
        # Chỉ tiến hành bước tiếp theo của chu kỳ máy khi animation hoàn thành
        self.is_animating = False
        if self.is_running_mode:
            self._run_next_phase_after_delay()
        else:
            self.step_button.setEnabled(True)
            self.run_button.setEnabled(True)
            self._run_next_phase_after_delay()
            
    def _run_next_phase_after_delay(self, delay=300):
        QTimer.singleShot(delay, self._advance_cpu_phase)
    
    
    def run_cpu(self):
        if self.cpu.is_halted:
            QMessageBox.information(self, "CPU Halted", "CPU is in a halted state. Please press 'Reset' to restart.")
            return

        if self.is_running_mode:
            # Nếu đang ở chế độ chạy, bấm nút để tạm dừng
            self.is_running_mode = False
            self.run_button.setText("Run")
        else:
            # Nếu đang tạm dừng, bấm nút để chạy
            self.is_running_mode = True
            self.run_button.setText("Pause")
            self.step_button.setEnabled(False) # Vô hiệu hóa nút Step khi chạy
            self._advance_cpu_phase()

    def step_cpu(self):
        if self.cpu.is_halted:
            QMessageBox.information(self, "CPU Halted", "CPU has halted. Please press 'Reset' to restart.")
            self.cpu_current_phase = 'IDLE'
            return
        
        # Chế độ Step luôn là một lần chạy duy nhất
        self.is_running_mode = False
        self.run_button.setText("Run") # Đảm bảo nút Run trở lại trạng thái ban đầu
        self.step_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self._advance_cpu_phase()
    
    def _advance_cpu_phase(self):
        # Kiểm tra trạng thái animation để tránh chồng chéo
        if self.is_animating:
            print("Animation in progress, waiting...")
            return

        # Kiểm tra trạng thái HALT
        if self.cpu.is_halted:
            self.run_button.setEnabled(True)
            self.step_button.setEnabled(True)
            self.is_running_mode = False
            self.cpu_current_phase = 'IDLE'
            QMessageBox.information(self, "CPU Halted", "CPU has stopped. Please press 'Reset' to restart.")
            return
        
        self._clear_all_highlights_and_animations()

        print(f"Current Phase: {self.cpu_current_phase}")

        if self.cpu_current_phase == 'IDLE':
            self.cpu_current_phase = 'FETCH'
            self._run_next_phase_after_delay()
            
        elif self.cpu_current_phase == 'FETCH':
            # 1. Fetch: Lấy lệnh từ RAM vào IR
            self.cpu.fetch_instruction()
            self.update_gui_cpu_status()
            self.highlight_component('IAR', Qt.GlobalColor.red)
            self._animate_signal('IAR_TO_RAM_ADDR_BUS', Qt.GlobalColor.red)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'DECODE'

        elif self.cpu_current_phase == 'DECODE':
            # 2. Decode: Giải mã lệnh trong IR
            self.cpu.decode_instruction()
            self.update_gui_cpu_status()
            self.highlight_component('IR', Qt.GlobalColor.green)
            self._animate_signal('RAM_DATA_TO_IR', Qt.GlobalColor.green)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'EXECUTE'

        elif self.cpu_current_phase == 'EXECUTE':
            # 3. Execute: Thực thi lệnh
            decoded_instruction = self.cpu.last_decoded_instruction
            op_name = decoded_instruction['name']
            
            # SỬA CHỮA LỖI NÀY: Thực thi lệnh ngay lập tức, trước khi chuyển pha
            self.cpu.execute_instruction()
            self.update_gui_cpu_status()
            
            if op_name in ['ADD', 'SUB']:
                self.highlight_component('A', Qt.GlobalColor.green)
                self.highlight_component('B', Qt.GlobalColor.green)
                self.highlight_component('ALU', Qt.GlobalColor.magenta)
                self._animate_signal('REG_A_TO_ALU', Qt.GlobalColor.darkCyan)
                self._animate_signal('REG_B_TO_ALU', Qt.GlobalColor.darkCyan)
                self.is_animating = True
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'EXECUTE_ALU_WRITEBACK'

            elif op_name in ['LOAD_A', 'LOAD_B', 'STORE_A', 'STORE_B']:
                self.highlight_component('IR', Qt.GlobalColor.green)
                self.highlight_component('RAM_TABLE_POS', Qt.GlobalColor.red)
                # Animation từ IAR_TO_RAM_ADDR_BUS đã diễn ra ở FETCH
                # Animate đường data từ/đến RAM
                if op_name in ['LOAD_A', 'LOAD_B']:
                    self._animate_signal('RAM_DATA_TO_REG_A' if op_name == 'LOAD_A' else 'RAM_DATA_TO_REG_B', Qt.GlobalColor.blue)
                else: # STORE
                    self._animate_signal('REG_A_TO_RAM_DATA_BUS' if op_name == 'STORE_A' else 'REG_B_TO_RAM_DATA_BUS', Qt.GlobalColor.blue)
                
                self.is_animating = True
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'INCREMENT_IAR' # Chuyển thẳng đến INCREMENT_IAR

            elif op_name == 'JUMP':
                self.highlight_component('IR', Qt.GlobalColor.yellow)
                self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.red)
                self.is_animating = True
                self.signal_animator.start_animation()
                self.cpu_current_phase = 'JUMP_DONE'

            elif op_name in ['JUMP_NEG', 'JUMP_ZERO']:
                # SỬA CHỮA LỖI NÀY: Kiểm tra điều kiện JUMP sau khi lệnh đã được thực thi
                # (Lệnh execute_instruction() đã thay đổi IAR nếu điều kiện thỏa mãn)
                self.highlight_component('IR', Qt.GlobalColor.yellow)
                if (op_name == 'JUMP_NEG' and self.cpu.flags['N']) or \
                   (op_name == 'JUMP_ZERO' and self.cpu.flags['Z']):
                    # Nếu JUMP thành công, thực hiện animation và chuyển pha
                    print(f"JUMP_NEG/ZERO: Condition met, jumping to {self.cpu.registers['IAR']}")
                    self._animate_signal('ADDR_TO_IAR_JUMP', Qt.GlobalColor.red)
                    self.is_animating = True
                    self.signal_animator.start_animation()
                    self.cpu_current_phase = 'JUMP_DONE'
                else:
                    # Nếu JUMP không thành công, không có animation JUMP, chuyển thẳng đến INCREMENT_IAR
                    print(f"JUMP_NEG/ZERO: Condition not met, proceeding to next instruction.")
                    self.cpu_current_phase = 'INCREMENT_IAR'
                    self._run_next_phase_after_delay() # Gọi ngay pha tiếp theo vì không có animation cần đợi

            elif op_name == 'HALT':
                self.highlight_component('CONTROL_UNIT', Qt.GlobalColor.red)
                self.is_running_mode = False
                self.run_button.setEnabled(True)
                self.step_button.setEnabled(True)
                self.cpu_current_phase = 'IDLE'
                QMessageBox.information(self, "CPU Halted", "CPU has stopped. Please press 'Reset' to restart.")
                return

            else: # NOP, hoặc các lệnh không cần animation đặc biệt
                self.cpu_current_phase = 'INCREMENT_IAR'
                self._run_next_phase_after_delay()

        elif self.cpu_current_phase == 'EXECUTE_ALU_WRITEBACK':
            # Pha này chỉ để xử lý animation từ ALU về Reg A
            self.highlight_component('A', Qt.GlobalColor.blue)
            self._animate_signal('ALU_TO_REG_A', Qt.GlobalColor.blue)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'INCREMENT_IAR'

        # SỬA CHỮA LỖI NÀY: Pha JUMP_DONE không cần thực thi lại lệnh
        elif self.cpu_current_phase == 'JUMP_DONE':
            self.update_gui_cpu_status()
            self.highlight_component('IAR', Qt.GlobalColor.blue)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'IDLE'

        elif self.cpu_current_phase == 'INCREMENT_IAR':
            # Tăng IAR nếu cần
            op_name = self.cpu.last_decoded_instruction['name']
            
            # SỬA CHỮA LỖI NÀY: Kiểm tra điều kiện chính xác để tăng IAR
            # Chỉ tăng IAR nếu IAR chưa bị thay đổi bởi lệnh JUMP thành công
            if not (op_name == 'JUMP' or \
                    (op_name == 'JUMP_NEG' and self.cpu.flags['N']) or \
                    (op_name == 'JUMP_ZERO' and self.cpu.flags['Z'])):
                self.cpu.increment_iar()
            
            self.update_gui_cpu_status()
            self.highlight_component('IAR', Qt.GlobalColor.yellow)
            self.is_animating = True
            self.signal_animator.start_animation()
            self.cpu_current_phase = 'IDLE'
    
    def reset_cpu(self):
        self._clear_all_highlights_and_animations()
        self.cpu.reset()
        self.cpu_current_phase = 'IDLE'
        self.is_running_mode = False
        self.run_button.setText("Run")
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        self.update_gui_cpu_status()
        self.ram_group_box.setStyleSheet("")
        QMessageBox.information(self, "Reset", "CPU has been reset.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CPUVisualizerApp()
    window.show()
    sys.exit(app.exec())

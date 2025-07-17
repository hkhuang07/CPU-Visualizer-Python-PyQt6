class CPU:
    def __init__(self):
        # Khởi tạo RAM: 16 địa chỉ, mỗi địa chỉ 8 bit (sử dụng list chứa chuỗi bit)
        self.ram = ["00000000"] * 16  # 16 địa chỉ, mỗi địa chỉ 8 bit, khởi tạo là 0

        # Khởi tạo các thanh ghi (Registers)
        self.registers = {
            'A': 0,      # Register A (8-bit value, 0-255)
            'B': 0,      # Register B (8-bit value, 0-255)
            'IR_Opcode': '0000',  # Instruction Register - Opcode part (4 bits string)
            'IR_AddrData': '0000',  # Instruction Register - Address/Data part (4 bits string)
            'IAR': 0,    # Instruction Address Register (Program Counter - PC) - 4 bits (0-15)
        }

        # Khởi tạo các cờ trạng thái (Flags)
        self.flags = {
            'O': False,  # Overflow Flag
            'Z': False,  # Zero Flag
            'N': False   # Negative Flag
        }

        # Bảng mã lệnh (Opcode definitions)
        self.opcode_map = {
            '0000': {'name': 'NOP', 'description': 'No Operation', 'operands': 'None'},
            '0001': {'name': 'LOAD_A', 'description': 'Load value from RAM[Addr] into Reg A', 'operands': 'Addr'},
            '0010': {'name': 'LOAD_B', 'description': 'Load value from RAM[Addr] into Reg B', 'operands': 'Addr'},
            '0011': {'name': 'STORE_A', 'description': 'Store value from Reg A to RAM[Addr]', 'operands': 'Addr'},
            '0100': {'name': 'STORE_B', 'description': 'Store value from Reg B to RAM[Addr]', 'operands': 'Addr'},
            '0101': {'name': 'ADD', 'description': 'Reg A = Reg A + Reg B', 'operands': 'Regs'},
            '0110': {'name': 'SUB', 'description': 'Reg A = Reg A - Reg B', 'operands': 'Regs'},
            '0111': {'name': 'JUMP', 'description': 'Jump to instruction at RAM[Addr]', 'operands': 'Addr'},
            '1000': {'name': 'JUMP_NEG', 'description': 'Jump to RAM[Addr] if N flag is set', 'operands': 'Addr'},
            '1001': {'name': 'JUMP_ZERO', 'description': 'Jump to RAM[Addr] if Z flag is set', 'operands': 'Addr'},
            '1010': {'name': 'ADDI', 'description': 'Reg A = Reg A + Immediate_Value', 'operands': 'Data'}, # <-- Lệnh ADDI mới
            '1111': {'name': 'HALT', 'description': 'Stop program execution', 'operands': 'None'}
        }

        self.is_halted = False  # Cờ báo hiệu CPU đã dừng
        self.last_decoded_instruction = None  # Lưu trữ lệnh đã giải mã

    def read_ram(self, address):
        """Đọc giá trị 8-bit từ địa chỉ RAM."""
        if 0 <= address < len(self.ram):
            return self.ram[address]
        else:
            print(f"Error: Invalid RAM address on read: {address}")
            return "00000000"

    def write_ram(self, address, data_str):
        """Ghi giá trị 8-bit vào địa chỉ RAM."""
        if not isinstance(data_str, str) or len(data_str) != 8 or not all(c in '01' for c in data_str):
            raise ValueError(f"RAM data must be an 8-bit string. Received: {data_str}")
        if 0 <= address < len(self.ram):
            self.ram[address] = data_str
        else:
            print(f"Error: Invalid RAM address while writing: {address}")
            
    def load_instruction(self, address, full_instruction_str):
        """
        Nạp một lệnh 8-bit (chuỗi nhị phân) vào RAM.
        """
        self.write_ram(address, full_instruction_str)
        
        opcode_str = full_instruction_str[:4]
        operand_str = full_instruction_str[4:]
        op_info = self.opcode_map.get(opcode_str, {'name': 'UNKNOWN', 'operands': 'None'})

        operand_display = ''
        if op_info['operands'] == 'Addr':
            operand_display = f" {int(operand_str, 2)}"
        elif op_info['operands'] == 'Data': # Cập nhật để hiển thị hằng số
            operand_display = f" #{int(operand_str, 2)}" # Dùng '#' để ký hiệu hằng số
        elif op_info['operands'] == 'Regs':
            operand_display = " RegA, RegB"
        else:
            operand_display = ''
        
        print(f"Load instruction: RAM[{address}] = {full_instruction_str} ({op_info['name']}{operand_display})")

    def _update_flags_ZN(self, result):
        """
        Cập nhật cờ Zero (Z) và Negative (N) dựa trên kết quả của phép toán.
        Lưu ý: Cờ Overflow (O) phải được xử lý riêng trong các phép toán.
        """
        # Cờ Zero (Z): Bật nếu kết quả bằng 0
        self.flags['Z'] = (result == 0)

        # Cờ Negative (N): Bật nếu bit cao nhất (bit thứ 7) của kết quả là 1.
        # Sử dụng & 0x80 (nhị phân 10000000) để kiểm tra bit thứ 7.
        self.flags['N'] = (result & 0x80) != 0
        print(f"Flags Z: {self.flags['Z']}, N: {self.flags['N']}")


    def _to_signed_8bit(self, value):
        """Chuyển đổi giá trị không dấu 8-bit (0-255) sang có dấu (-128 đến 127)."""
        if value > 127:
            return value - 256
        return value

    def fetch_instruction(self):
        """
        Pha Fetch: Nạp lệnh từ RAM vào thanh ghi lệnh (IR).
        """
        if self.is_halted:
            return None

        current_address = self.registers['IAR']
        instruction_bits = self.read_ram(current_address)

        self.registers['IR_Opcode'] = instruction_bits[:4]
        self.registers['IR_AddrData'] = instruction_bits[4:]

        print(f"Fetch: RAM[{current_address}] -> IR ({self.registers['IR_Opcode']} {self.registers['IR_AddrData']})")

        return instruction_bits

    def decode_instruction(self):
        """
        Pha Decode: Giải mã lệnh từ IR để xác định Opcode và Operand.
        """
        opcode_str = self.registers['IR_Opcode']
        operand_str = self.registers['IR_AddrData']

        instruction_info = self.opcode_map.get(opcode_str)

        if not instruction_info:
            print(f"Decode: Unknown command: {opcode_str}")
            self.last_decoded_instruction = {'name': 'UNKNOWN', 'operands': 'None', 'opcode_str': opcode_str, 'operand_val': None}
            return self.last_decoded_instruction

        operand_display = 'N/A'
        operand_value = None
        if instruction_info['operands'] in ['Addr', 'Data']: # Cập nhật để xử lý cả Addr và Data
            operand_value = int(operand_str, 2)
            if instruction_info['operands'] == 'Data':
                operand_display = f"#{operand_value}" # Dùng '#' cho hằng số
            else:
                operand_display = operand_value
        elif instruction_info['operands'] == 'Regs':
            operand_display = "RegA, RegB"
            
        print(f"Decode: Opcode: {instruction_info['name']} (Operand: {operand_display})")

        self.last_decoded_instruction = {
            'name': instruction_info['name'],
            'operands': instruction_info['operands'],
            'opcode_str': opcode_str,
            'operand_val': operand_value
        }
        return self.last_decoded_instruction
            
    def execute_instruction(self):
        """
        Pha Execute: Thực thi lệnh đã giải mã, sử dụng last_decoded_instruction.
        """
        if not self.last_decoded_instruction:
            print("Execute: No instruction to execute.")
            return

        decoded_instruction = self.last_decoded_instruction
        op_name = decoded_instruction['name']
        operand_val = decoded_instruction['operand_val']

        print(f"Execute: {op_name}")

        # Sửa: Trước khi thực hiện lệnh, reset cờ Overflow vì nó chỉ liên quan đến ALU
        self.flags['O'] = False

        if op_name == 'LOAD_A':
            data_from_ram = self.read_ram(operand_val)
            self.registers['A'] = int(data_from_ram, 2)
            print(f"   Reg A = RAM[{operand_val}] = {self.registers['A']}")
            self._update_flags_ZN(self.registers['A']) # Sửa: cập nhật cờ sau lệnh LOAD/STORE
        elif op_name == 'LOAD_B':
            data_from_ram = self.read_ram(operand_val)
            self.registers['B'] = int(data_from_ram, 2)
            print(f"   Reg B = RAM[{operand_val}] = {self.registers['B']}")
            # Sửa: Không cập nhật cờ sau lệnh LOAD/STORE (theo nguyên tắc chung, LOAD/STORE không thay đổi cờ)
            # Nếu bạn muốn cập nhật cờ cho LOAD/STORE, hãy gọi _update_flags_ZN ở đây
            # self._update_flags_ZN(self.registers['B']) 
        elif op_name == 'STORE_A':
            data_to_store = f"{self.registers['A']:08b}"
            self.write_ram(operand_val, data_to_store)
            print(f"   RAM[{operand_val}] = Reg A ({self.registers['A']})")
        elif op_name == 'STORE_B':
            data_to_store = f"{self.registers['B']:08b}"
            self.write_ram(operand_val, data_to_store)
            print(f"   RAM[{operand_val}] = Reg B ({self.registers['B']})")
        elif op_name == 'ADD':
            val_a_before = self.registers['A']
            val_b_before = self.registers['B']

            result = val_a_before + val_b_before
            
            signed_a = self._to_signed_8bit(val_a_before)
            signed_b = self._to_signed_8bit(val_b_before)
            
            # Kiểm tra overflow cho phép cộng có dấu
            if (signed_a > 0 and signed_b > 0 and self._to_signed_8bit(result) < 0) or \
               (signed_a < 0 and signed_b < 0 and self._to_signed_8bit(result) > 0):
                self.flags['O'] = True
            else:
                self.flags['O'] = False

            self.registers['A'] = result & 0xFF # Cập nhật thanh ghi A với kết quả 8-bit
            
            print(f"   Reg A = {val_a_before} + {val_b_before} = {self.registers['A']}")
            self._update_flags_ZN(self.registers['A'])
            print(f"   Flags updated: O={self.flags['O']}")

        elif op_name == 'SUB':
            val_a_before = self.registers['A']
            val_b_before = self.registers['B']

            result = val_a_before - val_b_before
            
            signed_a = self._to_signed_8bit(val_a_before)
            signed_b = self._to_signed_8bit(val_b_before)

            # Kiểm tra overflow cho phép trừ có dấu
            if (signed_a > 0 and signed_b < 0 and self._to_signed_8bit(result) < 0) or \
               (signed_a < 0 and signed_b > 0 and self._to_signed_8bit(result) > 0):
                self.flags['O'] = True
            else:
                self.flags['O'] = False

            self.registers['A'] = result & 0xFF # Cập nhật thanh ghi A với kết quả 8-bit
            
            print(f"   Reg A = {val_a_before} - {val_b_before} = {self.registers['A']}")
            self._update_flags_ZN(self.registers['A'])
            print(f"   Flags updated: O={self.flags['O']}")
        
        # --- Lệnh ADDI mới ---
        elif op_name == 'ADDI':
            val_a_before = self.registers['A']
            immediate_value = operand_val # operand_val là giá trị hằng số 4-bit

            result = val_a_before + immediate_value
            
            # Kiểm tra cờ Overflow
            signed_a = self._to_signed_8bit(val_a_before)
            # Coi immediate_value là số dương có dấu 8-bit (vì nó từ 0-15)
            signed_immediate = immediate_value 

            if signed_a > 0 and signed_immediate > 0 and self._to_signed_8bit(result) < 0:
                self.flags['O'] = True
            # Không cần trường hợp hai số âm kết quả dương vì immediate_value luôn dương
            else:
                self.flags['O'] = False

            self.registers['A'] = result & 0xFF
            
            print(f"   Reg A = {val_a_before} + #{immediate_value} = {self.registers['A']}")
            self._update_flags_ZN(self.registers['A'])
            print(f"   Flags updated: O={self.flags['O']}")
        # --- Kết thúc lệnh ADDI mới ---

        elif op_name == 'JUMP':
            self.registers['IAR'] = operand_val
            print(f"   JUMP to address {operand_val}")
            # Đánh dấu là đã nhảy, để không tăng IAR sau khi thực thi
            self.jump_occurred = True 

        elif op_name == 'JUMP_NEG':
            if self.flags['N']:
                self.registers['IAR'] = operand_val
                print(f"   N flag set, JUMP to address {operand_val}")
                self.jump_occurred = True
            else:
                print("   N flag not set, JUMP_NEG skipped.")

        elif op_name == 'JUMP_ZERO':
            if self.flags['Z']:
                self.registers['IAR'] = operand_val
                print(f"   Z flag set, JUMP to address {operand_val}")
                self.jump_occurred = True
            else:
                print("   Z flag not set, JUMP_ZERO skipped.")

        elif op_name == 'HALT':
            self.is_halted = True
            print("CPU Halted.")

        elif op_name == 'UNKNOWN':
            print("   Error: Unknown command. Stopping execution.")
            self.is_halted = True
            
    def increment_iar(self):
        """Tăng giá trị của thanh ghi IAR lên 1, trừ khi một lệnh nhảy đã xảy ra."""
        if not hasattr(self, 'jump_occurred') or not self.jump_occurred:
            self.registers['IAR'] = (self.registers['IAR'] + 1) % 16 # Đảm bảo IAR không vượt quá 15
            print(f"IAR incremented to {self.registers['IAR']}")
        else:
            print(f"JUMP_DONE") # Để nhất quán với output trước đó
        self.jump_occurred = False # Reset cờ jump cho chu kỳ tiếp theo


    def calculate_alu_output(self):
        """Tính toán giá trị đầu ra của ALU mà không thực thi lệnh."""
        if self.last_decoded_instruction:
            op_name = self.last_decoded_instruction.get('name')
            operand_val = self.last_decoded_instruction.get('operand_val') # Lấy operand_val
            if op_name == 'ADD':
                return (self.registers['A'] + self.registers['B']) & 0xFF
            elif op_name == 'SUB':
                return (self.registers['A'] - self.registers['B']) & 0xFF
            elif op_name == 'ADDI': # Thêm cho ADDI
                return (self.registers['A'] + operand_val) & 0xFF
        return 0
    
    def reset(self):
        """Đặt lại trạng thái CPU về ban đầu (trừ RAM)."""
        self.registers['A'] = 0
        self.registers['B'] = 0
        self.registers['IR_Opcode'] = '0000'
        self.registers['IR_AddrData'] = '0000'
        self.registers['IAR'] = 0
        self.flags['O'] = False
        self.flags['Z'] = False
        self.flags['N'] = False
        self.is_halted = False
        self.last_decoded_instruction = None
        self.jump_occurred = False # Đặt lại cờ jump
        print("CPU has been reset (registers and flags only).")

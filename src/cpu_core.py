# cpu_core.py

class CPU:
    def __init__(self):
        # Khởi tạo RAM: 16 địa chỉ, mỗi địa chỉ 8 bit (sử dụng list chứa chuỗi bit)
        self.ram = ["00000000"] * 16 # 16 địa chỉ, mỗi địa chỉ 8 bit, khởi tạo là 0

        # Khởi tạo các thanh ghi (Registers)
        self.registers = {
            'A': 0,    # Register A (8-bit value, 0-255)
            'B': 0,    # Register B (8-bit value, 0-255)
            'IR_Opcode': '0000', # Instruction Register - Opcode part (4 bits string)
            'IR_AddrData': '0000', # Instruction Register - Address/Data part (4 bits string)
            'IAR': 0,  # Instruction Address Register (Program Counter - PC) - 4 bits (0-15)
        }

        # Khởi tạo các cờ trạng thái (Flags)
        self.flags = {
            'O': False, # Overflow Flag
            'Z': False, # Zero Flag
            'N': False  # Negative Flag
        }
        
        # Bảng mã lệnh (Opcode definitions)
        self.opcode_map = {
            '0000': {'name': 'NOP', 'description': 'No Operation', 'operands': 'None'},
            '0001': {'name': 'LOAD_A', 'description': 'Load value from RAM[Addr] into Reg A', 'operands': 'Addr'},
            '0010': {'name': 'LOAD_B', 'description': 'Load value from RAM[Addr] into Reg B', 'operands': 'Addr'},
            '0011': {'name': 'STORE_A', 'description': 'Store value from Reg A to RAM[Addr]', 'operands': 'Addr'},
            '0100': {'name': 'STORE_B', 'description': 'Store value from Reg B to RAM[Addr]', 'operands': 'Addr'},
            '0101': {'name': 'ADD', 'description': 'Reg A = Reg A + Reg B', 'operands': 'None'},
            '0110': {'name': 'SUB', 'description': 'Reg A = Reg A - Reg B', 'operands': 'None'},
            '0111': {'name': 'JUMP', 'description': 'Jump to instruction at RAM[Addr]', 'operands': 'Addr'},
            '1000': {'name': 'JUMP_NEG', 'description': 'Jump to RAM[Addr] if N flag is set', 'operands': 'Addr'},
            '1001': {'name': 'JUMP_ZERO', 'description': 'Jump to RAM[Addr] if Z flag is set', 'operands': 'Addr'},
            '1111': {'name': 'HALT', 'description': 'Stop program execution', 'operands': 'None'}
        }

        self.is_halted = False # Cờ báo hiệu CPU đã dừng
        self.last_decoded_instruction = None # Lưu trữ lệnh đã giải mã

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

    def load_ram(self, address, full_instruction_str):
        """
        Nạp một lệnh 8-bit (chuỗi nhị phân) vào RAM.
        Sửa tên hàm cho nhất quán.
        """
        self.write_ram(address, full_instruction_str)
        opcode_str = full_instruction_str[:4]
        operand_str = full_instruction_str[4:]
        op_info = self.opcode_map.get(opcode_str, {'name': 'UNKNOWN'})
        print(f"Load instruction: RAM[{address}] = {full_instruction_str} ({op_info['name']} {int(operand_str, 2) if op_info.get('operands') == 'Addr' else ''})")

    def _update_flags(self, result):
        """
        Cập nhật các cờ trạng thái (Z, N, O) dựa trên giá trị kết quả.
        Các phép toán như ADD/SUB sẽ tự kiểm tra và cập nhật cờ O.
        """
        # Cờ Zero (Z): Bật nếu kết quả bằng 0
        self.flags['Z'] = (result == 0)

        # Cờ Negative (N): Bật nếu bit cao nhất (bit thứ 7) của kết quả là 1.
        self.flags['N'] = (result & 0b10000000) != 0

        # Cờ Overflow (O) được xử lý riêng trong các phép toán.
        # Ở đây chỉ reset nếu không phải là kết quả của phép toán.
        # (Để đảm bảo cờ O không bị xóa nhầm trong quá trình fetch/decode)

    def fetch_instruction(self):
        """
        Pha Fetch: Nạp lệnh từ RAM vào thanh ghi lệnh (IR).
        Cập nhật IAR (Program Counter).
        """
        if self.is_halted:
            return None

        current_address = self.registers['IAR']
        instruction_bits = self.read_ram(current_address)

        self.registers['IR_Opcode'] = instruction_bits[:4]
        self.registers['IR_AddrData'] = instruction_bits[4:]
        
        print(f"Fetch: RAM[{current_address}] -> IR ({self.registers['IR_Opcode']} {self.registers['IR_AddrData']})")
        
        # Tăng IAR lên cho lệnh tiếp theo (nếu không có JUMP)
        self.registers['IAR'] = (self.registers['IAR'] + 1) % len(self.ram)
        
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
            return {'name': 'UNKNOWN', 'operands': 'None', 'opcode_str': opcode_str, 'operand_val': None}

        operand_value = None
        if instruction_info['operands'] == 'Addr':
            operand_value = int(operand_str, 2)

        print(f"Decode: Opcode: {instruction_info['name']} (Operand: {operand_value if operand_value is not None else 'N/A'})")
        
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

        if op_name == 'LOAD_A':
            data_from_ram = self.read_ram(operand_val)
            self.registers['A'] = int(data_from_ram, 2)
            print(f"  Reg A = RAM[{operand_val}] = {self.registers['A']}")
            self._update_flags(self.registers['A'])

        elif op_name == 'LOAD_B':
            data_from_ram = self.read_ram(operand_val)
            self.registers['B'] = int(data_from_ram, 2)
            print(f"  Reg B = RAM[{operand_val}] = {self.registers['B']}")
            self._update_flags(self.registers['B'])

        elif op_name == 'STORE_A':
            data_to_store = f"{self.registers['A']:08b}"
            self.write_ram(operand_val, data_to_store)
            print(f"  RAM[{operand_val}] = Reg A ({self.registers['A']})")

        elif op_name == 'STORE_B':
            data_to_store = f"{self.registers['B']:08b}"
            self.write_ram(operand_val, data_to_store)
            print(f"  RAM[{operand_val}] = Reg B ({self.registers['B']})")

        elif op_name == 'ADD':
            result = self.registers['A'] + self.registers['B']
            self.flags['O'] = (result > 255)
            self.registers['A'] = result & 0xFF
            print(f"  Reg A = {self.registers['A']} + {self.registers['B']} = {self.registers['A']}")
            self._update_flags(self.registers['A'])

        elif op_name == 'SUB':
            result = self.registers['A'] - self.registers['B']
            self.flags['O'] = (result < 0)
            self.registers['A'] = result & 0xFF
            print(f"  Reg A = {self.registers['A']} - {self.registers['B']} = {self.registers['A']}")
            self._update_flags(self.registers['A'])

        elif op_name == 'JUMP':
            self.registers['IAR'] = operand_val
            print(f"  JUMP to address {operand_val}")

        elif op_name == 'JUMP_NEG':
            if self.flags['N']:
                self.registers['IAR'] = operand_val
                print(f"  N flag set, JUMP to address {operand_val}")
            else:
                print("  N flag not set, JUMP_NEG skipped.")

        elif op_name == 'JUMP_ZERO':
            if self.flags['Z']:
                self.registers['IAR'] = operand_val
                print(f"  Z flag set, JUMP to address {operand_val}")
            else:
                print("  Z flag not set, JUMP_ZERO skipped.")

        elif op_name == 'HALT':
            self.is_halted = True
            print("CPU Halted.")

        elif op_name == 'UNKNOWN':
            print("  Error: Unknown command. Stopping execution.")
            self.is_halted = True

    def reset(self):
        """Đặt lại trạng thái CPU về ban đầu."""
        self.ram = ["00000000"] * 16
        self.registers = {
            'A': 0, 'B': 0,
            'IR_Opcode': '0000', 'IR_AddrData': '0000',
            'IAR': 0,
        }
        self.flags = {'O': False, 'Z': False, 'N': False}
        self.is_halted = False
        self.last_decoded_instruction = None
        print("CPU has been reset.")
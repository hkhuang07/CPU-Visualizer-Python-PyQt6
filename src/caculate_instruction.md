# CPU Visualizer: Basic Arithmetic Programs

This repository contains programs demonstrating fundamental arithmetic operations (Addition, Subtraction, Multiplication, and Integer Division with Remainder) on a simplified CPU architecture. The CPU features 16 RAM addresses, two general-purpose registers (A and B), and a defined set of opcodes.

## CPU Architecture Overview

Our CPU is a basic 8-bit architecture with 4-bit opcodes and 4-bit operands (either RAM addresses or immediate data).

### Opcode Map

The following table details the available instructions for our CPU:

| Opcode   | Name          | Description                          | Operands |
| :------- | :------------ | :----------------------------------- | :------- |
| `0000` | `NOP`       | No Operation                         | None     |
| `0001` | `LOAD_A`    | Load value from RAM[Addr] into Reg A | Addr     |
| `0010` | `LOAD_B`    | Load value from RAM[Addr] into Reg B | Addr     |
| `0011` | `STORE_A`   | Store value from Reg A to RAM[Addr]  | Addr     |
| `0100` | `STORE_B`   | Store value from Reg B to RAM[Addr]  | Addr     |
| `0101` | `ADD`       | Reg A = Reg A + Reg B                | Regs     |
| `0110` | `SUB`       | Reg A = Reg A - Reg B                | Regs     |
| `0111` | `JUMP`      | Jump to instruction at RAM[Addr]     | Addr     |
| `1000` | `JUMP_NEG`  | Jump to RAM[Addr] if N flag is set   | Addr     |
| `1001` | `JUMP_ZERO` | Jump to RAM[Addr] if Z flag is set   | Addr     |
| `1010` | `ADDI`      | Reg A = Reg A + Immediate_Value      | Data     |
| `1111` | `HALT`      | Stop program execution               | None     |

## Arithmetic Programs

The following sections provide the assembly-like code for each arithmetic operation, along with explanations of their functionality and memory usage.

### 1. Addition Program

This program adds two integer numbers and stores the result in RAM.

- **Inputs:** `RAM[14]` (Operand 1), `RAM[15]` (Operand 2)
- **Output:** `RAM[13]` (Result)
- **Starting Address:** `RAM[0]`

```assembly
RAM[0]: 00011110   ; LOAD_A 14   ; Load Operand 1 from RAM[14] into Register A
RAM[1]: 00101111   ; LOAD_B 15   ; Load Operand 2 from RAM[15] into Register B
RAM[2]: 01011001   ; ADD         ; Add B to A. Result in A (A = A + B)
RAM[3]: 00111101   ; STORE_A 13  ; Store Result from A into RAM[13]
RAM[4]: 11110000   ; HALT        ; Stop program
```

### 2. Subtract Program

This program subtract two integer numbers and stores the result in RAM.

- **Inputs:** `RAM[14]` (Operand 1), `RAM[15]` (Operand 2)
- **Output:** `RAM[13]` (Result)
- **Starting Address:** `RAM[0]`

```assembly
RAM[0]: 00011110   ; LOAD_A 14   ; Load Operand 1 from RAM[14] into Register A
RAM[1]: 00101111   ; LOAD_B 15   ; Load Operand 2 from RAM[15] into Register B
RAM[2]: 01101001   ; SUB         ; Subtract B from A. Result in A (A = A - B)
RAM[3]: 00111101   ; STORE_A 13  ; Store Result from A into RAM[13]
RAM[4]: 11110000   ; HALT        ; Stop program
```

### 3. Division Program

This program Divide two integer numbers and stores the result in RAM.

- **Inputs:** `RAM[14]` (Operand 1), `RAM[15]` (Operand 2)
- **Output:** `RAM[13]` (Quotient), `RAM[12]` (Remainder)
- **Starting Address:** `RAM[0]`

```assembly
# Input Data (example):
# RAM[10] = 0 (00000000)
# RAM[11] = 1 (00000001)
# RAM[14] = 10 (00001010) - Dividend
# RAM[15]-+ = 3 (00000011) - Divisor

# --- Program Start ---

# Initialization Phase
RAM[0]: 00011110   ; LOAD_A 14   ; Load Dividend (RAM[14]) into Reg A. Reg A = Dividend (initial remainder).
RAM[1]: 00111100   ; STORE_A 12  ; Initialize Remainder (RAM[12]) with the Dividend (from Reg A).
RAM[2]: 00101111   ; LOAD_B 15   ; Load Divisor (RAM[15]) into Reg B. Reg B = Divisor.
RAM[3]: 00011010   ; LOAD_A 10   ; Set Reg A to 0 (to be used as quotient counter).
RAM[4]: 00111101   ; STORE_A 13  ; Store 0 into RAM[13] (Initialize Quotient = 0).


# --- Division Loop ---
# This loop subtracts the Divisor from the Remainder until the Remainder becomes negative.
# For each successful subtraction (non-negative Remainder), the Quotient is incremented by 1.
RAM[5]: 00011100   ; LOAD_A 12   ; L_A_R_loop: Load current Remainder from RAM[12] into Reg A.
RAM[6]: 01101001   ; SUB         ; A = A - B (Remainder - Divisor). N flag will be set if result is negative.
RAM[7]: 10001101   ; JUMP_NEG 13 ; If A < 0 (N flag is set), jump to SUB_CORRECTION (RAM[13]).

RAM[8]: 00111100   ; STORE_A 12  ; STORE_R: If not negative, store the result (new remainder) into RAM[12].
RAM[9]: 00011101   ; LOAD_A 13   ; LOAD_Q: Load current Quotient from RAM[13] into Reg A.
RAM[10]: 10100001  ; ADDI 1      ; ADDI_1: Increment the quotient by 1 (A = A + 1).
RAM[11]: 00111101  ; STORE_A 13  ; STORE_Q: Store the updated Quotient back into RAM[13].
RAM[12]: 01110101  ; JUMP 5      ; JUMP_loop: Jump back to L_A_R_loop (RAM[5]) to continue the loop.

# --- Final Correction (when JUMP_NEG was triggered) ---
# At this point, Reg A holds a negative value (Remainder - Divisor).
# To get the correct positive remainder, we need to add the Divisor back to Reg A.
RAM[13]: 01011001  ; ADD         ; SUB_CORRECTION: A = A + B. (This "undoes" the last subtraction, yielding the correct remainder).
RAM[14]: 00111100  ; STORE_A 12  ; Store the correct remainder into RAM[12].

RAM[15]: 11110000  ; HALT        ; Stop the program.
```

### 4. Multiplicand Program

This program multiplicand two integer numbers and stores the result in RAM.

- **Inputs:** `RAM[14]` (Operand 1), `RAM[15]` (Operand 2)
- **Output:** `RAM[13]` (Result)
- **Starting Address:** `RAM[0]`
```
; Chương trình Nhân (Multiplication Program)
; Thực hiện phép nhân hai số nguyên bằng cách cộng lặp lại.

; Đầu vào:
; RAM[14] = Số bị nhân (Multiplicand)
; RAM[15] = Số nhân (Multiplier)

; Đầu ra:
; RAM[13] = Tích (Product)

; Các giá trị RAM cần được khởi tạo trước khi chạy chương trình:
; RAM[10] = 0 (dùng làm hằng số 0)
; RAM[11] = 1 (dùng làm hằng số 1)

; --- Khởi tạo Tích ban đầu ---
RAM[0]: 00011010   ; LOAD_A 10   ; Tải hằng số 0 (từ RAM[10]) vào Thanh ghi A.
RAM[1]: 00111100   ; STORE_A 12  ; Lưu giá trị từ Thanh ghi A (là 0) vào RAM[12].
                           ; => RAM[12] (Tích) được khởi tạo bằng 0.

; --- Bắt đầu Vòng lặp Cộng lặp lại ---
; Vòng lặp này sẽ lặp lại 'Số nhân' lần.
; Mỗi lần lặp, nó sẽ cộng 'Số bị nhân' vào 'Tích'.
RAM[2]: 00011111   ; LOAD_A 15   ; Tải giá trị 'Số nhân' (từ RAM[15]) vào Thanh ghi A.
                           ; Chúng ta dùng 'Số nhân' làm bộ đếm vòng lặp.
RAM[3]: 10010111   ; JUMP_ZERO 7 ; KIỂM TRA ĐIỀU KIỆN DỪNG:
                           ; Nếu Thanh ghi A (Số nhân) là 0 (cờ Z bật),
                           ; nghĩa là đã cộng đủ số lần, thì nhảy đến địa chỉ RAM[7] (End_Loop).

; --- Thực hiện phép Cộng trong vòng lặp ---
RAM[4]: 00011100   ; LOAD_A 12   ; Tải giá trị 'Tích' hiện tại (từ RAM[12]) vào Thanh ghi A.
RAM[5]: 00101110   ; LOAD_B 14   ; Tải giá trị 'Số bị nhân' (từ RAM[14]) vào Thanh ghi B.
RAM[6]: 01011001   ; ADD         ; Thực hiện phép cộng: Thanh ghi A = Thanh ghi A + Thanh ghi B.
                           ; => Thanh ghi A bây giờ chứa 'Tích' mới (Tích cũ + Số bị nhân).
RAM[7]: 00111100   ; STORE_A 12  ; Lưu giá trị 'Tích' mới (từ Thanh ghi A) trở lại RAM[12].

; --- Giảm Bộ đếm (Số nhân) ---
RAM[8]: 00011111   ; LOAD_A 15   ; Tải giá trị 'Số nhân' hiện tại (từ RAM[15]) vào Thanh ghi A.
RAM[9]: 00101011   ; LOAD_B 11   ; Tải hằng số 1 (từ RAM[11]) vào Thanh ghi B.
RAM[10]: 01101001  ; SUB         ; Thực hiện phép trừ: Thanh ghi A = Thanh ghi A - Thanh ghi B.
                           ; => Thanh ghi A bây giờ chứa 'Số nhân' đã giảm đi 1.
RAM[11]: 00111111  ; STORE_A 15  ; Lưu giá trị 'Số nhân' đã giảm (từ Thanh ghi A) trở lại RAM[15].

RAM[12]: 01110010  ; JUMP 2      ; NHẢY LẶP LẠI:
                           ; Nhảy trở lại địa chỉ RAM[2] để kiểm tra 'Số nhân' và tiếp tục vòng lặp.

; --- Kết thúc Chương trình (End_Loop) ---
; Khi 'Số nhân' về 0, chương trình nhảy đến đây.
RAM[13]: 00011100  ; LOAD_A 12   ; Tải 'Tích' cuối cùng (từ RAM[12]) vào Thanh ghi A.
RAM[14]: 00111101  ; STORE_A 13  ; Lưu 'Tích' cuối cùng (từ Thanh ghi A) vào RAM[13].
                           ; => Kết quả cuối cùng được lưu vào RAM[13].
RAM[15]: 11110000  ; HALT        ; Dừng chương trình.
```

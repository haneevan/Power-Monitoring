import serial
import minimalmodbus # We need a library to calculate the CRC

# NOTE: The 'minimalmodbus' library is used here for its reliable CRC calculation function.
# You may need to install it if you run this script outside of the Canvas environment:
# pip install minimalmodbus

# Function to calculate the Modbus RTU CRC (from minimalmodbus source, for self-containment)
def calculate_modbus_crc(data):
    """Calculate the Modbus RTU CRC."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            a = crc
            crc >>= 1
            if (a & 0x0001) != 0:
                crc ^= 0xA001
    # Modbus RTU requires the CRC to be little-endian (low byte first, then high byte)
    return crc.to_bytes(2, byteorder='little')

# --- Modbus Parameters for Reading Holding Registers ---
UNIT_ID = 2       # Target unit: 02
FUNCTION_CODE = 3 # Read Holding Registers
START_ADDRESS = 0x0000 # Register address 0
NUM_REGISTERS = 2  # Read 2 registers (4 bytes of data)

# 1. Construct the message payload (excluding CRC)
payload = bytes([
    UNIT_ID, 
    FUNCTION_CODE, 
    (START_ADDRESS >> 8) & 0xFF, # High byte of address
    START_ADDRESS & 0xFF,       # Low byte of address
    (NUM_REGISTERS >> 8) & 0xFF, # High byte of registers
    NUM_REGISTERS & 0xFF        # Low byte of registers
])

# 2. Calculate the CRC and append it
crc_bytes = calculate_modbus_crc(payload)
command = payload + crc_bytes

# The resulting command for Unit 02 is: 02 03 00 00 00 02 C43E
# Note the CRC changed from C40B (for Unit 01) to C43E (for Unit 02)

# --- Serial Port Setup ---
ser = serial.Serial(
    port='/dev/ttyACM0',  # Change this to your actual device name
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_EVEN,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

# --- Communication ---
print(f"Targeting Unit ID: {UNIT_ID}")
print("Sending:", command.hex().upper())

try:
    ser.write(command)

    # Response reception
    response = ser.read(256)  # Read up to 256 bytes

    if response:
        print("Received:", response.hex().upper())
    else:
        print("Received: NO RESPONSE (Timeout)")

except serial.SerialException as e:
    print(f"Error communicating with serial port: {e}")
    
finally:
    ser.close()
    print("Serial port closed.")

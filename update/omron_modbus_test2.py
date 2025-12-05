import minimalmodbus
import time
from datetime import datetime
import serial 

# --- CONFIGURATION SETTINGS ---
PORT = '/dev/ttyACM0'  
SLAVE_ADDRESS = 1      
BAUDRATE = 9600        
FUNCTION_CODE = 3      

# REGISTER ADDRESSES (FROM MANUAL/IMAGES)
REGISTER_V = 0x0000    
REGISTER_A = 0x0006    
REGISTER_KW = 0x0010   

# SCALING FACTORS 
SCALE_V  = 0.01        
SCALE_A  = 0.001       
SCALE_KW = 0.0001      

# --- Byte Order Definitions (FIXED FOR OLDER VERSIONS) ---
# Replace constants with their integer values
HIGH_WORD_FIRST = 0 
LOW_WORD_FIRST = 3 
# ----------------------------------------------------

# --- Modbus Connection Setup ---
instrument = minimalmodbus.Instrument(
    PORT, SLAVE_ADDRESS, mode=minimalmodbus.MODE_RTU
)
instrument.serial.baudrate = BAUDRATE
instrument.serial.timeout = 0.5
instrument.serial.parity = serial.PARITY_EVEN  
instrument.serial.bytesize = 8                 
instrument.serial.stopbits = 1                 


# Function to read all three values with custom format settings
def read_and_print_values(instrument, signed, byteorder_val, title):
    # Set the byte order dynamically using the integer value
    instrument.long_byteorder = byteorder_val 
    
    print(f"\n--- TESTING FORMAT: {title} ---")
    
    try:
        # Read and scale Voltage (V)
        raw_v = instrument.read_long(REGISTER_V, FUNCTION_CODE, signed=signed)
        v_value = raw_v * SCALE_V

        # Read and scale Current (A)
        raw_a = instrument.read_long(REGISTER_A, FUNCTION_CODE, signed=signed)
        a_value = raw_a * SCALE_A

        # Read and scale Power (kW)
        raw_kw = instrument.read_long(REGISTER_KW, FUNCTION_CODE, signed=signed)
        kw_value = raw_kw * SCALE_KW

        # If we reach here, communication was successful!
        print("✅ SUCCESS! Communication Established with this format.")
        print(f"Voltage (V): {v_value:.2f} (Raw: {raw_v})")
        print(f"Current (A): {a_value:.3f} (Raw: {raw_a})")
        print(f"Power (kW):  {kw_value:.4f} (Raw: {raw_kw})")
        return True
        
    except minimalmodbus.ModbusException as e:
        print(f"❌ FAILED. Error: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False


def troubleshoot_formats():
    print(f"Modbus RTU initialized on {PORT} at {BAUDRATE} baud.")

    # 1. Default (High Word First - 0) - Signed
    if read_and_print_values(instrument, True, HIGH_WORD_FIRST, "High-Word-First (0), SIGNED"):
        return
    
    # 2. Inverted Byte Order (Low Word First - 3) - Signed (Most common fix)
    if read_and_print_values(instrument, True, LOW_WORD_FIRST, "Low-Word-First (3), SIGNED"):
        return

    # 3. Default (High Word First - 0) - Unsigned
    if read_and_print_values(instrument, False, HIGH_WORD_FIRST, "High-Word-First (0), UNSIGNED"):
        return

    # 4. Inverted Byte Order (Low Word First - 3) - Unsigned
    if read_and_print_values(instrument, False, LOW_WORD_FIRST, "Low-Word-First (3), UNSIGNED"):
        return

    print("\n\n X All software formats failed.")


if __name__ == "__main__":
    try:
        troubleshoot_formats()
    except Exception as e:
        print(f"Fatal error during initialization: {e}")
    finally:
        instrument.serial.close()

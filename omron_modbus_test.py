import minimalmodbus
import time
from datetime import datetime
import serial # Required for parity constants

# --- 1. CONFIGURATION SETTINGS (CONFIRMED) ---
PORT = '/dev/ttyACM0'  # Confirmed USB device name
SLAVE_ADDRESS = 1      # Unit Number (01) from manual
BAUDRATE = 9600        # Confirmed speed from manual

# --- 2. MODBUS REGISTER ADDRESSES (FROM MANUAL/IMAGES) ---
# NOTE: These are 0-indexed (Manual Address - 1)
REGISTER_V = 0x0000    # Voltage 1 (40001)
REGISTER_A = 0x0006    # Current 1 (40007)
REGISTER_KW = 0x0010   # Active Power (40017)
REGISTER_KWH = 0x0222  # Kwh 
FUNCTION_CODE = 3      # Read Holding Registers

# --- 3. SCALING FACTORS (INFERRED FROM IMAGE EXAMPLES) ---
# These scales convert the raw 32-bit integer to the actual float value.
SCALE_V  = 0.1 #0.01        
SCALE_A  = 0.01 #0.001       
SCALE_KW = 0.01 #0.0001
SCALE_KWH = 1      

# --- 4. SCRIPT ---
def read_omron_modbus_test():
    try:
        instrument = minimalmodbus.Instrument(
            PORT,
            SLAVE_ADDRESS,
            mode=minimalmodbus.MODE_RTU
        )
        # --- CRITICAL SERIAL SETTINGS (MUST MATCH MANUAL) ---
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.timeout = 0.5
        instrument.serial.parity = serial.PARITY_EVEN  # Setting from manual
        instrument.serial.bytesize = 8                 # Setting from manual
        instrument.serial.stopbits = 1                 # Setting from manual (1 bit when parity is used)
        # ----------------------------------------------------
        
        print(f"Modbus RTU initialized on {PORT} at {BAUDRATE} baud (Parity: EVEN).")

        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- Reading at {timestamp} ---")
            
            try:
                # 4.1. Read Voltage (V)
                raw_v = instrument.read_long(REGISTER_V, FUNCTION_CODE, signed=True)
                v_value = raw_v * SCALE_V
                print(f"Voltage (V): {v_value:.2f} (Raw: {raw_v})")
                
                # 4.2. Read Current (A)
                raw_a = instrument.read_long(REGISTER_A, FUNCTION_CODE, signed=True)
                a_value = raw_a * SCALE_A
                print(f"Current (A): {a_value:.3f} (Raw: {raw_a})")

                # 4.3. Read Active Power (kW)
                raw_kw = instrument.read_long(REGISTER_KW, FUNCTION_CODE, signed=True)
                kw_value = raw_kw * SCALE_KW
                print(f"Power (kW):  {kw_value:.4f} (Raw: {raw_kw})")
                
                # 4.4. Read (kWh)
                raw_kwh = instrument.read_long(REGISTER_KWH, FUNCTION_CODE, signed=True)
                kwh_value = raw_kwh * SCALE_KWH
                print(f"Power/hour (kWh):  {kw_value:.4f} (Raw: {raw_kw})")

            except minimalmodbus.ModbusException as e:
                print(f"[{timestamp}] MODBUS FAILED. Check wiring polarity. Error: {e}")
                
            time.sleep(5) 

    except Exception as e:
        print(f"An unhandled error occurred: {e}")
    finally:
        if 'instrument' in locals():
            instrument.serial.close()

if __name__ == "__main__":
    read_omron_modbus_test()

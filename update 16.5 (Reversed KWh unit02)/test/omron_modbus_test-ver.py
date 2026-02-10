import minimalmodbus
import time
from datetime import datetime
import serial # Required for parity constants

# --- 1. CONFIGURATION SETTINGS (CONFIRMED) ---
PORT = '/dev/ttyACM0'  # Confirmed USB device name
SLAVE_ADDRESS = 1     # Unit Number (01) from manual
BAUDRATE = 9600        # Confirmed speed from manual
FUNCTION_CODE = 3      # Read Holding Registers

# --- 2. MODBUS REGISTER ADDRESSES (FROM MANUAL/IMAGES) ---
REGISTER_V = 0x0000    # Voltage 1 (40001)
REGISTER_A = 0x0006    # Current 1 (40007)
REGISTER_KW = 0x0010   # Active Power (40017)
REGISTER_KWH = 0x0200  # Kwh accumulated energy
REGISTER_PF = 0x000C   # Power Factor

# --- 3. SCALING FACTORS (MATCHING MANUAL TABLE 5.5.1) ---
SCALE_V   = 0.1      # Recover Volts from 10x value
SCALE_A   = 0.001    # Recover Amps from 1000x value
SCALE_KW  = 0.0001   # Recover Watts (10x) and convert to kW
SCALE_KWH = 0.001    # Convert Wh (Register 0x0200) to kWh
SCALE_PF  = 0.01    # Recover Power Factor Value (based on module)   

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
        
        #print(f"Modbus RTU initialized on {PORT} at {BAUDRATE} baud (Parity: EVEN).")

        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            #print(f"\n--- Reading at {timestamp} ---")
            
            try:
                # 4.1. Read Voltage (V)
                raw_v = instrument.read_long(REGISTER_V, FUNCTION_CODE, signed=True)
                v_value   = raw_v * SCALE_V
                # 4.2. Read Current (A)
                raw_a = instrument.read_long(REGISTER_A, FUNCTION_CODE, signed=True)
                a_value   = raw_a * SCALE_A
                # 4.3. Read Power (kW)
                raw_kw = instrument.read_long(REGISTER_KW, FUNCTION_CODE, signed=True)
                kw_value  = raw_kw * SCALE_KW
                # 4.4. Read Energy (kWh)
                raw_kwh = instrument.read_long(REGISTER_KWH, FUNCTION_CODE, signed=True)
                kwh_value = raw_kwh * SCALE_KWH
                # 4.5. Read Power Factor ()
                raw_pf = instrument.read_long(REGISTER_PF, FUNCTION_CODE, signed=True)
                pf_value  = raw_pf * SCALE_PF
                
                # Print log output
                print(f" {v_value:.2f} V || {a_value:.3f} A || {kw_value:.4f} kW || {kwh_value:.4f} kWh || {pf_value:.4f} ")

            except minimalmodbus.ModbusException as e:
                print(f"[{timestamp}] MODBUS FAILED. Check wiring polarity. Error: {e}")
                
            time.sleep(1) 

    except Exception as e:
        print(f"An unhandled error occurred: {e}")
    finally:
        if 'instrument' in locals():
            instrument.serial.close()

if __name__ == "__main__":
    read_omron_modbus_test()

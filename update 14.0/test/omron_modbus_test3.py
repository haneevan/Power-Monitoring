import minimalmodbus
import time
from datetime import datetime
import serial 

# --- 1. CONFIGURATION SETTINGS (CONFIRMED) ---
PORT = '/dev/ttyACM0'  
SLAVE_ADDRESS = 1      
BAUDRATE = 9600        
FUNCTION_CODE = 3      

# --- 2. MODBUS REGISTER ADDRESSES (FINALIZED) ---
REGISTER_V = 0x0000     # Voltage 1 (40001)
REGISTER_A = 0x0006     # Current 1 (40007)
REGISTER_KW = 0x0010    # Power
REGISTER_KWH = 0x0220   # Accumulated Effective Energy (Wh) (40545)

# --- 3. SCALING FACTORS (FINAL CONFIRMED) ---
SCALE_V  = 0.1          # Confirmed by your live data: Raw * 0.1 = V
SCALE_A  = 0.001        # Confirmed by your live data: Raw * 0.001 = A
SCALE_KW = 0.001
SCALE_KWH = 1       # Wh (Raw Unit) -> kWh (1)

def read_omron_modbus_final():
    try:
        instrument = minimalmodbus.Instrument(
            PORT, SLAVE_ADDRESS, mode=minimalmodbus.MODE_RTU
        )
        # --- CRITICAL SERIAL SETTINGS ---
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.timeout = 0.5
        instrument.serial.parity = serial.PARITY_EVEN  
        instrument.serial.bytesize = 8                 
        instrument.serial.stopbits = 1                 
        # Use Low-Word-First (3) for 32-bit data (longs)
        instrument.long_byteorder = 3 
        
        print(f"Modbus communication initialized on {PORT}.")
        
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- Reading at {timestamp} ---")
            
            try:
                # 1. Read Voltage (V)
                raw_v = instrument.read_long(REGISTER_V, FUNCTION_CODE, signed=True)
                v_value = raw_v * SCALE_V
                print(f"Voltage (V): {v_value:.2f} V (Raw V: {raw_v})")
                
                # 2. Read Current (A)
                raw_a = instrument.read_long(REGISTER_A, FUNCTION_CODE, signed=True)
                a_value = raw_a * SCALE_A
                print(f"Current (A): {a_value:.3f} A (Raw A: {raw_a})")
                
                # 4. Read Power (kW)
                # Register 0010 (kw) is used. Use unsigned (signed=False).
                raw_kw = instrument.read_long(REGISTER_KW, FUNCTION_CODE, signed=True) 
                kw_value = raw_kw * SCALE_KW # Convert Wh to kWh
                print(f"Power (kW): {kw_value:.3f} kW (Raw W: {raw_kw})")

                # 3. Read Accumulated Energy (kWh)
                # Register 0220 (Wh) is used. Use unsigned (signed=False).
                raw_wh = instrument.read_long(REGISTER_KWH, FUNCTION_CODE, signed=False) 
                kwh_value = raw_wh * SCALE_KWH # Convert Wh to kWh
                print(f"Energy (kWh): {kwh_value:.3f} kWh (Raw kWh: {raw_wh})")
            
            except minimalmodbus.ModbusException as e:
                print(f"[{timestamp}] COMMUNICATION FAILED. Error: {e}")
                
            time.sleep(5) 

    except Exception as e:
        print(f"An unhandled error occurred: {e}")
    finally:
        if 'instrument' in locals():
            instrument.serial.close()

if __name__ == "__main__":
    read_omron_modbus_final()

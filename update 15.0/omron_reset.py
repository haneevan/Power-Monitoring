from pymodbus.client import ModbusSerialClient as ModbusClient
import time

#----config (Matches your working omron_modbus.py)
PORT = '/dev/ttyACM0'  # Fixed based on your code
BAUD = 9600
PARITY = 'E'           # Matches PARITY_EVEN
UNIT_IDS = [1, 2]

def reset_all_units():
    # This connection works perfectly in your venv
    client = ModbusClient(port=PORT, baudrate=BAUD, parity=PARITY, timeout=1)
    
    if client.connect():
        print(f"Connected to Modbus on {PORT}")
        try:
            for unit_id in UNIT_IDS:
                print(f"--- Processing Unit {unit_id} ---")
                
                # UNIVERSAL FIX: No keywords like 'slave=' or 'unit='
                # This bypasses the version errors you were seeing in the venv.
                result = client.write_register(0x0005, 0x0001, unit_id)
                
                if not result.isError():
                    print(f"Successfully sent reset signal to Unit {unit_id}!")
                else:
                    # If you see "Exception 6", the meter is still BUSY.
                    print(f"Failed to reset Unit {unit_id}: {result}")
                
                time.sleep(1)
            
        finally:
            client.close()
            print("Connection closed.")

if __name__ == "__main__":
    reset_all_units()

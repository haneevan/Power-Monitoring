from pymodbus.client import ModbusSerialClient as ModbusClient
import time

# ---- config (Matches your working omron_modbus.py)
PORT = '/dev/ttyACM0'
BAUD = 9600
PARITY = 'E'
UNIT_IDS = [1, 2]

def reset_all_units():
    client = ModbusClient(port=PORT, baudrate=BAUD, parity=PARITY, timeout=2)
    
    if client.connect():
        print(f"Connected to Modbus on {PORT}")
        try:
            for unit_id in UNIT_IDS:
                print(f"--- Processing Unit {unit_id} ---")
                
                # FIXED BASED ON MANUAL:
                # Register: 0xFFFF (Operation Command)
                # Value: 0x0300 (Clear Integrated Power / kWh Reset)
                # Command: 0x06 (Write Single Register)
                result = client.write_register(0xFFFF, 0x0300, unit_id)
                
                if not result.isError():
                    print(f"SUCCESS: Reset command accepted by Unit {unit_id}!")
                    print("Note: Meter may take a moment to update the display.")
                else:
                    print(f"FAILED: Unit {unit_id} rejected the command: {result}")
                
                # The manual says EEPROM writing takes time; give it a breather
                time.sleep(2)
            
        finally:
            client.close()
            print("Connection closed.")
    else:
        print(f"Could not connect to {PORT}")

if __name__ == "__main__":
    reset_all_units()

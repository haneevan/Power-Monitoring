import minimalmodbus
from datetime import datetime

class OmronReadError(Exception):
    """Custom exception for Modbus reading errors."""
    pass

class OmronModbusClient:
    def __init__(self, port='/dev/ttyACM0'):
        """
        Initializes the Modbus instrument.
        :param port: The serial port (e.g., '/dev/ttyACM0' or 'COM3')
        """
        try:
            # Initialize with default Slave ID 1
            self.instrument = minimalmodbus.Instrument(port, 1)
            
            # Modbus RTU Settings based on standard Omron defaults
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
            self.instrument.serial.stopbits = 1
            self.instrument.serial.timeout = 0.5
            
            # Crucial for stable communication on some USB-RS485 adapters
            self.instrument.close_port_after_each_call = True
            
        except Exception as e:
            print(f"Failed to initialize Modbus on {port}: {e}")

    def read_data(self, slave_id):
        """
        Reads raw data from registers and converts to usable values.
        """
        try:
            self.instrument.address = slave_id 
            
            # 1. Read Raw Voltage (Addr 0000, 2 registers)
            # Omron often uses a multiplier. If Voltage reads 23000, it means 230.00V
            raw_v = self.instrument.read_registers(0, 2, functioncode=3)
            # Combine two 16-bit registers into one 32-bit integer
            voltage = (raw_v[0] << 16 | raw_v[1]) / 10.0 

            # 2. Read Raw Current (Addr 0006, 2 registers)
            # Multiplier often 1000 (e.g., 1500 = 1.500A)
            raw_a = self.instrument.read_registers(6, 2, functioncode=3)
            current = (raw_a[0] << 16 | raw_a[1]) / 1000.0

            # 3. Read Raw Active Energy (Addr 512, 2 registers)
            raw_wh = self.instrument.read_registers(512, 2, functioncode=3)
            energy_wh = (raw_wh[0] << 16 | raw_wh[1])

            return {
                'val_voltage': round(voltage, 2),
                'val_current': round(current, 3),
                'val_energy_kwh': round(energy_wh / 1000, 3),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            # Re-raise with the slave ID so we know which unit is failing
            raise OmronReadError(f"Slave {slave_id} Read Error: {str(e)}")

# For quick standalone testing
if __name__ == "__main__":
    client = OmronModbusClient()
    try:
        print("Testing Unit 01...")
        print(client.read_data(1))
        print("Testing Unit 02...")
        print(client.read_data(2))
    except Exception as e:
        print(f"Test Failed: {e}")

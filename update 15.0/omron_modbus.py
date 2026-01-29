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
            self.instrument.serial.timeout = 0.1
            
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
            raw_v = self.instrument.read_registers(0, 2, functioncode=3)
            voltage = (raw_v[0] << 16 | raw_v[1]) / 10.0 

            # 2. Read Raw Current (Addr 0006, 2 registers)
            raw_a = self.instrument.read_registers(6, 2, functioncode=3)
            current = (raw_a[0] << 16 | raw_a[1]) / 1000.0

            # 3. Read Raw Active Energy (Addr 512, 2 registers)
            raw_wh = self.instrument.read_registers(512, 2, functioncode=3)
            energy_wh = (raw_wh[0] << 16 | raw_wh[1])
            
            # 4. Read Raw Active Power (Addr 12 [0x000C], 2 registers)
            # Scaling is typically 0.1 W, so divide by 10,000 to get kW
            raw_pw = self.instrument.read_registers(12, 2, functioncode=3)
            # Note: Power can be signed (negative if CT is reversed)
            # We handle the sign here; omron_database.py will use abs() later.
            power_w = (raw_pw[0] << 16 | raw_pw[1])
            
            # Handle 32-bit signed integer for power
            if power_w > 0x7FFFFFFF:
                power_w -= 0x100000000
            
            power_kw = power_w / 1000.0

            return {
                'val_voltage': round(voltage, 2),
                'val_current': round(current, 3),
                'val_energy_kwh': round(energy_wh / 1000.0, 3),
                'val_power_kw': round(power_kw, 4),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
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

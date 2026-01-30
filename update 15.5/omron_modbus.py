# Updated omron_modbus.py (The Pillar)
import minimalmodbus
from datetime import datetime

class OmronReadError(Exception):
    pass

class OmronModbusClient:
    def __init__(self, port='/dev/ttyACM0'):
        try:
            self.instrument = minimalmodbus.Instrument(port, 1)
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
            self.instrument.serial.stopbits = 1
            self.instrument.serial.timeout = 0.5 # Increased slightly for reliability
            self.instrument.close_port_after_each_call = True
        except Exception as e:
            print(f"Failed to initialize Modbus on {port}: {e}")

    def read_data(self, slave_id):
        try:
            self.instrument.address = slave_id 
            
            # 1. Voltage (Addr 0000)
            raw_v = self.instrument.read_registers(0, 2, functioncode=3)
            voltage = (raw_v[0] << 16 | raw_v[1]) / 10.0 

            # 2. Current (Addr 0006)
            raw_a = self.instrument.read_registers(6, 2, functioncode=3)
            current = (raw_a[0] << 16 | raw_a[1]) / 1000.0

            # 3. Active Energy (Addr 512)
            raw_wh = self.instrument.read_registers(512, 2, functioncode=3)
            energy_wh = (raw_wh[0] << 16 | raw_wh[1])
            
            # 4. Active Power (Addr 12)
            raw_pw = self.instrument.read_registers(12, 2, functioncode=3)
            power_w = (raw_pw[0] << 16 | raw_pw[1])
            
            if power_w > 0x7FFFFFFF:
                power_w -= 0x100000000
            
            power_kw = power_w / 1000.0

            # Unit 02 Specific Handling: ABS() for Current if needed
            # (We can do this here or in omron_database.py)
            final_current = abs(current) if slave_id == 2 else current

            return {
                'unit_id': f'unit0{slave_id}',
                'val_voltage': round(voltage, 2),
                'val_current': round(final_current, 3),
                'val_energy_kwh': round(energy_wh / 1000.0, 3),
                'val_power_kw': round(power_kw, 4),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            raise OmronReadError(f"Slave {slave_id} Read Error: {str(e)}")

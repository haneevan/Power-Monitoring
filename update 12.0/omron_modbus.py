import minimalmodbus
from datetime import datetime
import time 

class OmronReadError(Exception):
    """Custom exception for Modbus reading errors."""
    pass

class OmronModbusClient:
    def __init__(self, port='/dev/ttyACM0'):
        try:
            self.instrument = minimalmodbus.Instrument(port, 1)
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
            self.instrument.serial.stopbits = 1
            self.instrument.serial.timeout = 1.0 
            self.instrument.close_port_after_each_call = True
        except Exception as e:
            print(f"Failed to initialize Modbus on {port}: {e}")

    def read_data(self, slave_id):
        try:
            self.instrument.address = slave_id 
            # High-accuracy breather to ensure the KM-N1-FLK logic is ready
            time.sleep(0.25) 
            
            # Addresses updated based on your manual image
            # 1. Voltage 1 (V) - Addr 0000
            raw_v = self.instrument.read_registers(0, 2, functioncode=3)
            voltage = (raw_v[0] << 16 | raw_v[1]) / 10.0 

            # 2. Current 1 (A) - Addr 0006
            raw_a = self.instrument.read_registers(6, 2, functioncode=3)
            current = (raw_a[0] << 16 | raw_a[1]) / 1000.0

            # 3. Active Power (W) - Addr 0010 (Hex) = 16 (Dec)
            # Note: Manual shows 0010 Hex for 有効電力
            raw_p = self.instrument.read_registers(16, 2, functioncode=3)
            active_power = (raw_p[0] << 16 | raw_p[1]) / 10.0 

            # 4. Accumulated Active Energy (Wh) - Addr 0200 (Hex) = 512 (Dec)
            raw_wh = self.instrument.read_registers(512, 2, functioncode=3)
            energy_wh = (raw_wh[0] << 16 | raw_wh[1])

            return {
                'val_voltage': round(voltage, 2),
                'val_current': round(current, 3),
                'val_power_w': round(active_power, 1),
                'val_energy_kwh': round(energy_wh / 1000, 3),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            raise OmronReadError(f"Slave {slave_id} Read Error: {str(e)}")

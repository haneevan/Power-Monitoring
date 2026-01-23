import struct
from pymodbus.client import ModbusSerialClient

class OmronModbusClient:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        # Initializing with settings matching your manual test
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity='E',      # Even parity as per Omron KM-N1
            stopbits=1,
            bytesize=8,
            timeout=1
        )

    def decode_32bit_signed(self, registers):
        """
        Combines two 16-bit registers into a 32-bit signed integer.
        Omron uses Big-Endian (High word first).
        """
        if not registers or len(registers) < 2:
            return 0
        # registers[0] is High Word (0x0001), registers[1] is Low Word (0xC467)
        combined = (registers[0] << 16) | registers[1]
        # Unpack as a signed 32-bit integer ('>i')
        return struct.unpack('>i', struct.pack('>I', combined))[0]

    def read_data(self, unit_id):
        """
        Reads Voltage, Current, and Active Power from a specific unit.
        """
        try:
            if not self.client.connect():
                print(f"Connection Failed to Unit {unit_id}")
                return 0, 0, 0

            # 1. Read Voltage (Address 0000, 2 registers)
            v_res = self.client.read_holding_registers(0x0000, 2, slave=unit_id)
            # 2. Read Current (Address 0006, 2 registers)
            a_res = self.client.read_holding_registers(0x0006, 2, slave=unit_id)
            # 3. Read Active Power (Address 0010, 2 registers)
            p_res = self.client.read_holding_registers(0x0010, 2, slave=unit_id)

            if any(r.isError() for r in [v_res, a_res, p_res]):
                return 0, 0, 0

            # Apply correct Omron scaling factors
            voltage = self.decode_32bit_signed(v_res.registers) / 10.0   # 0.1V unit
            current = self.decode_32bit_signed(a_res.registers) / 1000.0 # 0.001A unit
            power_w = self.decode_32bit_signed(p_res.registers) / 10.0   # 0.1W unit

            return voltage, current, power_w

        except Exception as e:
            print(f"Modbus Error on Unit {unit_id}: {e}")
            return 0, 0, 0
        finally:
            self.client.close()

# For quick standalone testing
if __name__ == "__main__":
    test_client = OmronModbusClient()
    for unit in [1, 2]:
        v, a, p = test_client.read_data(unit)
        print(f"--- Unit {unit:02d} Results ---")
        print(f"Voltage: {v:.2f} V")
        print(f"Current: {a:.3f} A")
        print(f"Power:   {p/1000.0:.2f} kW ({p:.1f} W)")

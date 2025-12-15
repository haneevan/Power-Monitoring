import minimalmodbus
import time
import serial
from datetime import datetime

# Define a custom exception for clean error handling in the main app
class OmronReadError(Exception):
    """Custom exception for errors during Modbus read operation."""
    pass

class OmronModbusClient:
    """
    Client for reading power parameters from an OMRON Power Monitor
    via Modbus RTU (Serial).
    """

    # --- 1. CONFIGURATION SETTINGS ---
    PORT = '/dev/ttyACM0'
    SLAVE_ADDRESS = 1
    BAUDRATE = 9600
    FUNCTION_CODE = 3

    # --- 2. MODBUS REGISTER ADDRESSES (Updated) ---
    # Addresses are zero-based, corresponding to Omron's documentation (4xxxx)
    REGISTER_V = 0x0000     # Voltage 1 (40001)
    REGISTER_A = 0x0006     # Current 1 (40007)
    # REGISTER_KW REMOVED
    REGISTER_KWH = 0x0200   # Accumulated Effective Energy (Wh) (40513)

    # --- 3. SCALING FACTORS (Updated) ---
    SCALE_V = 0.1
    SCALE_A = 0.001
    # SCALE_KW REMOVED
    SCALE_KWH = 0.001
    
    def __init__(self, port=PORT, slave_address=SLAVE_ADDRESS, baudrate=BAUDRATE):
        self.port = port
        self.slave_address = slave_address
        self.baudrate = baudrate
        self.instrument = None
        self._initialize_instrument()

    def _initialize_instrument(self):
        """
        Initializes and sets up the minimalmodbus instrument object.
        """
        try:
            instrument = minimalmodbus.Instrument(
                self.port, self.slave_address, mode=minimalmodbus.MODE_RTU
            )
            instrument.serial.baudrate = self.baudrate
            instrument.serial.timeout = 0.5
            # OMRON standard: 8 data bits, Even parity, 1 stop bit
            instrument.serial.parity = serial.PARITY_EVEN
            instrument.serial.bytesize = 8
            instrument.serial.stopbits = 1
            
            # OMRON 32-bit values are Low-Word-First 
            instrument.long_byteorder = 3 
            
            self.instrument = instrument
            print(f"Modbus communication initialized on {self.port} at {self.baudrate} baud.")
            
        except Exception as e:
            print(f"FATAL: Failed to initialize Modbus instrument. Error: {e}")
            self.instrument = None

    def read_data(self):
        """
        Reads all power parameters (V, A, kWh) from the Modbus instrument.
        
        Returns:
            dict: Dictionary of scaled readings including timestamp.
            
        Raises:
            OmronReadError: If Modbus communication fails or instrument is not ready.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self.instrument:
            raise OmronReadError("Modbus instrument is not initialized.")
            
        try:
            # All are 32-bit (Long) reads, Function Code 3 (Read Holding Registers)
            
            # 1. Voltage (V)
            raw_v = self.instrument.read_long(self.REGISTER_V, self.FUNCTION_CODE, signed=True)
            v_value = round(raw_v * self.SCALE_V, 2)
            
            # 2. Current (A)
            raw_a = self.instrument.read_long(self.REGISTER_A, self.FUNCTION_CODE, signed=True)
            a_value = round(raw_a * self.SCALE_A, 3)
            
            # 3. Accumulated Energy (kWh)
            raw_wh = self.instrument.read_long(self.REGISTER_KWH, self.FUNCTION_CODE, signed=False)
            kwh_value = round(raw_wh * self.SCALE_KWH, 3)
            
            # Return standard keys
            return {
                'timestamp': timestamp,
                'val_voltage': v_value, 
                'val_current': a_value,
                # 'val_power_kw' REMOVED
                'val_energy_kwh': kwh_value,
            }
            
        except minimalmodbus.ModbusException as e:
            raise OmronReadError(f"Modbus communication error: {e}") from e
        except Exception as e:
            raise OmronReadError(f"Unhandled error: {e}") from e

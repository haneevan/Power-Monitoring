import minimalmodbus
import time
import serial 

# --- 1. CONFIGURATION SETTINGS (CONFIRMED) ---
PORT = '/dev/ttyACM0'  
SLAVE_ADDRESS = 1      
BAUDRATE = 9600        
FUNCTION_CODE = 3      

# --- 2. MODBUS REGISTER ADDRESSES (FINALIZED) ---
REGISTER_V = 0x0000     # Voltage 1 (40001)
REGISTER_A = 0x0006     # Current 1 (40007)
REGISTER_KW = 0x0010    # Power (Raw in Watts)
REGISTER_KWH = 0x0220   # Accumulated Effective Energy (Raw in Wh)

# --- 3. SCALING FACTORS (FINAL CONFIRMED) ---
SCALE_V  = 0.1          # Raw * 0.1 = V (Volts)
SCALE_A  = 0.001        # Raw * 0.001 = A (Amperes)
SCALE_KW = 0.001        # Raw W -> kW (Divide by 1000)
SCALE_KWH = 1           # Raw kWh

def initialize_instrument():
    """Initializes and returns the minimalmodbus instrument object."""
    try:
        instrument = minimalmodbus.Instrument(
            PORT, SLAVE_ADDRESS, mode=minimalmodbus.MODE_RTU
        )
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.timeout = 0.5
        instrument.serial.parity = serial.PARITY_EVEN  
        instrument.serial.bytesize = 8                 
        instrument.serial.stopbits = 1                 
        instrument.long_byteorder = 3 # Low-Word-First for 32-bit data
        
        print(f"Modbus instrument initialized on {PORT}.")
        return instrument
    except Exception as e:
        print(f"FATAL: Failed to initialize Modbus instrument. Error: {e}")
        return None

def read_omron_data(instrument):
    """
    Reads all four power parameters and returns them as a dictionary.
    
    Args:
        instrument (minimalmodbus.Instrument): The initialized Modbus object.
        
    Returns:
        dict or None: Dictionary of readings or None if communication fails.
    """
    if not instrument:
        return None
        
    try:
        # 1. Read Voltage (V)
        raw_v = instrument.read_long(REGISTER_V, FUNCTION_CODE, signed=True)
        v_value = raw_v * SCALE_V
        
        # 2. Read Current (A)
        raw_a = instrument.read_long(REGISTER_A, FUNCTION_CODE, signed=True)
        a_value = raw_a * SCALE_A
        
        # 3. Read Power (kW)
        raw_kw = instrument.read_long(REGISTER_KW, FUNCTION_CODE, signed=True) 
        kw_value = raw_kw * SCALE_KW 

        # 4. Read Accumulated Energy (kWh)
        raw_wh = instrument.read_long(REGISTER_KWH, FUNCTION_CODE, signed=False) 
        kwh_value = raw_wh * SCALE_KWH 
        
        return {
            'voltage': v_value,
            'current': a_value,
            'power_kw': kw_value,
            'energy_kwh': kwh_value
        }
    
    except minimalmodbus.ModbusException as e:
        # Don't print an error here, let the caller handle it.
        raise e

import BAC0
import time
from datetime import datetime
import asyncio # <--- CRITICAL IMPORT FOR ASYNCIO

# --- 1. CONFIGURATION SETTINGS (BACnet) ---
# NOTE: Using 38400 bps as a common BACnet speed, but confirm KM-N1 setting.
SERIAL_PORT = 'serial:/dev/ttyACM0:9600:E:8:1' 
DEVICE_ID = 1      # Unit Number (01)

# --- 2. BACnet OID to Query (Likely Placeholders) ---
KWH_OBJECT = 'AnalogInput:1042' 
KW_OBJECT = 'AnalogInput:1020'
A_OBJECT = 'AnalogInput:1017'

READ_LIST = [
    f'{KWH_OBJECT} @ {DEVICE_ID}', 
    f'{KW_OBJECT} @ {DEVICE_ID}', 
    f'{A_OBJECT} @ {DEVICE_ID}'
]
LABELS = ['Total_Energy_kWh', 'Total_Power_kW', 'Total_Current_A']

# --- 3. ASYNCHRONOUS MAIN FUNCTION ---
# This function is now marked 'async'
async def run_bacnet_reader():
    bacnet = None
    try:
        # Initialize the network connection
        # The 'await' is crucial when using asyncio.run
        bacnet = BAC0.lite(
            ip=SERIAL_PORT, 
            segmentation_supported=True,
            poll=1 
        )
        print(f"BACnet connected on {SERIAL_PORT}")

        # --- Main Reading Loop ---
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Perform the multi-read operation
                # NOTE: The BAC0 library handles the internal awaits for 'read'
                results = bacnet.read(READ_LIST, property='presentValue')
                
                print(f"\n--- {timestamp} ---")
                
                if isinstance(results, list) and len(results) == len(READ_LIST):
                    print("✅ SUCCESS! Read Attempted.")
                    for label, value in zip(LABELS, results):
                        print(f"{label}: {value}")
                else:
                    # This will catch communication failures (like No Response)
                    print(f"❌ BACnet Read FAILED. Result: {results}")

            except Exception as e:
                print(f"[{timestamp}] BACnet Communication Error: {e}")

            await asyncio.sleep(10) # Use await asyncio.sleep instead of time.sleep

    except Exception as e:
        print(f"Initialization or Fatal Run-time Error: {e}")
        
    finally:
        if bacnet:
            bacnet.disconnect()
            print("BACnet disconnected.")

if __name__ == "__main__":
    # --- CRITICAL FIX: Run the async function using asyncio.run ---
    try:
        asyncio.run(run_bacnet_reader())
    except KeyboardInterrupt:
        print("\nExiting BACnet Reader.")

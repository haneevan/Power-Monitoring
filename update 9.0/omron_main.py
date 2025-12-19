import time
from datetime import datetime
# Import functions from our libraries
from omron_modbus import initialize_instrument, read_omron_data, minimalmodbus
from omron_database import setup_database, log_reading, cleanup_old_data

# --- Configuration ---
READ_INTERVAL_SECONDS = 5     # How often to poll the device
CLEANUP_INTERVAL_MINUTES = 60 # How often to run the database cleanup (once per hour)

def main_monitoring_loop():
    """
    Main function to initialize systems and run the continuous data collection loop.
    """
    # 1. Setup Database
    setup_database()
    
    # 2. Setup Modbus Instrument
    instrument = initialize_instrument()
    if not instrument:
        print("Application cannot start without a working Modbus connection.")
        return

    # 3. Main Logging Loop
    last_cleanup_time = time.time()
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Read data using the function from omron_modbus.py
                readings = read_omron_data(instrument)
                
                if readings:
                    # Log the successful reading to the database
                    log_reading(
                        readings['voltage'],
                        readings['current'],
                        readings['power_kw'],
                        readings['energy_kwh']
                    )
                    
                    # Print status to console for real-time verification
                    print(f"[{timestamp}] LOGGED | V: {readings['voltage']:.2f} | A: {readings['current']:.3f} | kW: {readings['power_kw']:.3f} | kWh: {readings['energy_kwh']:.4f}")
                
            except minimalmodbus.ModbusException as e:
                print(f"[{timestamp}] MODBUS COMMUNICATION FAILED. Error: {e}")
            except Exception as e:
                print(f"[{timestamp}] Unhandled error during read cycle: {e}")

            # Check for periodic cleanup
            if (time.time() - last_cleanup_time) > (CLEANUP_INTERVAL_MINUTES * 60):
                cleanup_old_data()
                last_cleanup_time = time.time()
                
            time.sleep(READ_INTERVAL_SECONDS) 

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    finally:
        # Clean up serial connection when the program exits
        instrument.serial.close()
        print("Modbus instrument connection closed.")

if __name__ == "__main__":
    main_monitoring_loop()

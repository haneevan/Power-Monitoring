import time
import threading
import json
from datetime import datetime
from flask import Flask, render_template
from collections import namedtuple

# Import Modbus Class and custom exception
from omron_modbus import OmronModbusClient, OmronReadError 

# Import Database functions 
# NOTE: The database functions now expect 3 values: V, A, kWh
from omron_database import setup_database, log_reading, cleanup_old_data, get_latest_readings, get_historical_readings

# --- Configuration ---
READ_INTERVAL_SECONDS = 5      
CLEANUP_INTERVAL_MINUTES = 60 
HISTORY_DAYS = 1              
HISTORY_HOURS = HISTORY_DAYS * 24

# Global flag to control the logging thread
logging_running = True

# --- Flask App Setup ---
app = Flask(__name__)
# Global variable to cache the latest reading for API speed
latest_data_cache = None
cache_lock = threading.Lock() 

# --- Logger Thread Function ---

def monitoring_loop(monitor_client):
    """
    The function executed in a separate thread to handle continuous data logging.
    """
    setup_database()
    
    last_cleanup_time = time.time()
    global logging_running
    global latest_data_cache
    
    try:
        while logging_running:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Read data from the OMRON device (Now returns V, A, kWh)
                readings = monitor_client.read_data()
                
                if readings:
                    # Log the successful reading to the local SQLite database (Updated call)
                    log_reading(
                        readings['val_voltage'], 
                        readings['val_current'],
                        readings['val_energy_kwh']
                    )
                    
                    # Update the global cache 
                    with cache_lock:
                        latest_data_cache = readings
                    
                    # Print status (Updated print statement)
                    print(f"[{timestamp}] LOGGER LOGGED | V: {readings['val_voltage']:.2f}V | A: {readings['val_current']:.3f}A | kWh: {readings['val_energy_kwh']:.3f}kWh")
                        
            except OmronReadError as e: 
                print(f"[{timestamp}] DATA READ ERROR: {e}")
            except Exception as e:
                print(f"[{timestamp}] UNHANDLED ERROR in loop: {e}")

            # Check for periodic cleanup
            if (time.time() - last_cleanup_time) > (CLEANUP_INTERVAL_MINUTES * 60):
                cleanup_old_data()
                last_cleanup_time = time.time()
                
            time.sleep(READ_INTERVAL_SECONDS)

    except Exception as e:
        print(f"Logger thread terminated unexpectedly: {e}")
    finally:
        # Ensure the serial port is closed gracefully
        if monitor_client and monitor_client.instrument and monitor_client.instrument.serial.is_open:
            monitor_client.instrument.serial.close()
            print("Logger thread closing Modbus connection.")


# --- Flask Web Routes ---

@app.route('/')
def dashboard():
    """
    Renders the dashboard. Fetches data for the initial page load.
    """
    history_data_tuples = get_historical_readings(days=HISTORY_DAYS)
    
    # *** CRITICAL FIX: Convert list of namedtuples to list of dictionaries ***
    # This ensures JavaScript receives a standard array of objects it can map easily.
    history_data_dicts = [item._asdict() for item in history_data_tuples]
    
    # RENDER TEMPLATE: Loads dashboard.html from the 'templates' folder
    return render_template(
        'dashboard.html', 
        # Pass the last item of the DICT list for the metric cards' initial load
        latest=history_data_dicts[-1] if history_data_dicts else None, 
        history=history_data_dicts, # Pass the DICT list to the template
        datetime=datetime,
        history_days=HISTORY_DAYS,
        history_hours=HISTORY_HOURS,
        read_interval_ms=READ_INTERVAL_SECONDS * 1000 
    )

@app.route('/api/latest')
def api_latest():
    """
    API endpoint to return the single latest reading as JSON. 
    This route already works because the cache stores a dictionary.
    """
    global latest_data_cache
    
    with cache_lock:
        if latest_data_cache:
            return latest_data_cache, 200
        else:
            # Fallback: if cache is empty, get from DB and convert namedtuple to dict
            latest_data_list = get_latest_readings(limit=1)
            if latest_data_list:
                # Convert the namedtuple to a standard Python dictionary for JSON serialization
                return dict(latest_data_list[0]._asdict()), 200
            else:
                return {'error': 'No data available'}, 404


# --- Main Execution ---

if __name__ == '__main__':
    # ... (execution block remains the same) ...
    
    # 1. Setup Modbus Instrument Client
    monitor_client = OmronModbusClient()
    instrument = monitor_client.instrument
    
    if not instrument:
        print("FATAL: Cannot initialize Modbus instrument. Web monitor starting without logging.")
        pass

    # 2. Start the Monitoring/Logging thread
    if instrument:
        logger_thread = threading.Thread(
            target=monitoring_loop, 
            args=(monitor_client,), 
            daemon=True
        )
        logger_thread.start()
        print("----------------------------------------------------------------------")
        print(f"Logger thread started (interval: {READ_INTERVAL_SECONDS}s).")
        print(f"History configured for: {HISTORY_HOURS} hours.")
        print("----------------------------------------------------------------------")
    else:
        print("----------------------------------------------------------------------")
        print("WARNING: Data logging thread NOT started due to initialization failure.")
        print("----------------------------------------------------------------------")


    # 3. Start the Flask Web Server
    print("Starting Flask Web Server...")
    print("Dashboard available at: http://0.0.0.0:5200/")
    
    try:
        app.run(host='0.0.0.0', port=5200, debug=False)
    except KeyboardInterrupt:
        print("\nWeb server stopped by user.")
    finally:
        print("Stopping logger thread...")
        logging_running = False
        if 'logger_thread' in locals() and logger_thread.is_alive():
             logger_thread.join(timeout=10)
        print("Application shutdown complete.")

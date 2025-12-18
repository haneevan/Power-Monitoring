import time
import threading
from flask import Flask, render_template, request, jsonify
from omron_modbus import OmronModbusClient, OmronReadError
from omron_database import (setup_database, log_reading, cleanup_old_data, 
                            get_historical_readings, get_historical_readings_by_range)

app = Flask(__name__)

# --- Configuration ---
TARGET_INTERVAL = 1.0  # Target update rate in seconds
PORT = 5200

# Global caches to store the most recent data for the UI
latest_caches = {
    'unit01': None,
    'unit02': None
}
cache_lock = threading.Lock()
logging_running = True

def monitoring_loop(client):
    """
    High-speed background thread with dynamic timing to hit 1-second intervals.
    """
    print("--- High-Speed Monitor Started ---")
    setup_database()
    
    cleanup_counter = 0
    
    while logging_running:
        start_time = time.time()  # Mark the start of this reading cycle

        # 1. Read Unit 01 (Slave ID 1)
        try:
            data1 = client.read_data(slave_id=1) 
            if data1:
                log_reading(data1['val_voltage'], data1['val_current'], data1['val_energy_kwh'], "unit01")
                with cache_lock:
                    latest_caches['unit01'] = data1
        except Exception as e:
            print(f"U1 Read Error: {e}")

        # Tiny breather for RS-485 transceiver (essential for /dev/ttyACM0)
        time.sleep(0.05)

        # 2. Read Unit 02 (Slave ID 2)
        try:
            data2 = client.read_data(slave_id=2)
            if data2:
                log_reading(data2['val_voltage'], data2['val_current'], data2['val_energy_kwh'], "unit02")
                with cache_lock:
                    latest_caches['unit02'] = data2
        except Exception as e:
            print(f"U2 Read Error: {e}")

        # --- Dynamic Timing Logic ---
        elapsed = time.time() - start_time
        # Wait only the remaining time needed to reach TARGET_INTERVAL
        sleep_time = max(0, TARGET_INTERVAL - elapsed)
        
        # Optional: Database cleanup logic
        cleanup_counter += 1
        if cleanup_counter >= 3600:  # Roughly every hour at 1s intervals
            cleanup_old_data(30)
            cleanup_counter = 0

        time.sleep(sleep_time)

# --- Web Routes ---

@app.route('/')
def dashboard_unit01():
    history_objs = get_historical_readings(days=1, unit_id="unit01")
    history_list = [item._asdict() for item in history_objs]
    return render_template(
        'dashboard.html', 
        unit_id="unit01", 
        history=history_list,
        latest=history_list[-1] if history_list else None,
        history_hours=24,
        read_interval_ms=TARGET_INTERVAL * 1000
    )

@app.route('/unit02')
def dashboard_unit02():
    history_objs = get_historical_readings(days=1, unit_id="unit02")
    history_list = [item._asdict() for item in history_objs]
    return render_template(
        'dashboard.html', 
        unit_id="unit02", 
        history=history_list,
        latest=history_list[-1] if history_list else None,
        history_hours=24,
        read_interval_ms=TARGET_INTERVAL * 1000
    )

# --- API Endpoints ---

@app.route('/api/<unit_id>/latest')
def api_latest(unit_id):
    with cache_lock:
        data = latest_caches.get(unit_id)
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No data available"}), 404

@app.route('/api/<unit_id>/history')
def api_history(unit_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({"error": "Missing dates"}), 400
    history_objs = get_historical_readings_by_range(start_date, end_date, unit_id)
    history_list = [item._asdict() for item in history_objs]
    return jsonify(history_list)

if __name__ == '__main__':
    # Initializing with your confirmed port
    modbus_client = OmronModbusClient(port='/dev/ttyACM0')
    
    monitor_thread = threading.Thread(target=monitoring_loop, args=(modbus_client,), daemon=True)
    monitor_thread.start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

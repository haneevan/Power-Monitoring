#---Importing necessary items----
import time
import threading
from datetime import datetime # Added for timestamping quiet fails
from flask import Flask, render_template, request, jsonify, redirect, url_for
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
    """Background thread to poll Modbus data every second with Quiet Fail logic."""
    print("--- High-Speed Monitor Started (Gapless Mode) ---")
    setup_database()
    cleanup_counter = 0
    
    while logging_running:
        start_time = time.time()
        # Generate a consistent timestamp for this specific polling "tick"
        current_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Poll both units sequentially
        for unit_id in ['unit01', 'unit02']:
            slave_id = 1 if unit_id == 'unit01' else 2
            
            try:
                # 1. Attempt to read actual data from the Omron unit
                data = client.read_data(slave_id=slave_id) 
                
                if data:
                    # Log actual data including the new val_power_w
                    log_reading(data['val_voltage'], data['val_current'], 
                                data['val_power_w'], data['val_energy_kwh'], unit_id)
                    with cache_lock:
                        latest_caches[unit_id] = data
                
            except OmronReadError:
                # 2. QUIET FAIL: If the unit is OFF, log 0s to maintain the timeline
                # This prevents the jumps you observed in the CSV
                null_data = {
                    'val_voltage': 0.0,
                    'val_current': 0.0,
                    'val_power_w': 0.0,
                    'val_energy_kwh': 0.0,
                    'timestamp': current_ts
                }
                # Pass 0.0 for all metrics to the database
                log_reading(0.0, 0.0, 0.0, 0.0, unit_id)
                with cache_lock:
                    latest_caches[unit_id] = null_data
                print(f"[{current_ts}] {unit_id} unreachable (OFF). Logged 0.0.")
            
            except Exception as e:
                print(f"Unexpected Error on {unit_id}: {e}")

            # 3. Transceiver breather (0.25s for bus stability)
            time.sleep(0.25) 

        # --- Cleanup Logic (Preserved from your reference code) ---
        elapsed = time.time() - start_time
        sleep_time = max(0, TARGET_INTERVAL - elapsed)
        
        cleanup_counter += 1
        if cleanup_counter >= 3600: # Hourly cleanup
            cleanup_old_data(30) # Maintain 30 days of data
            cleanup_counter = 0

        time.sleep(sleep_time)

# --- Web Routes (Preserved exactly as per reference) ---

@app.route('/')
def menu():
    """Main portal page."""
    return render_template('menu.html')

@app.route('/dashboard/<unit_id>')
def dashboard(unit_id):
    """Dynamic route for Unit 01 and Unit 02 dashboards."""
    if unit_id not in ['unit01', 'unit02']:
        return redirect(url_for('menu'))

    history_objs = get_historical_readings(days=1, unit_id=unit_id)
    history_list = [item._asdict() for item in history_objs]
    
    return render_template(
        'dashboard.html', 
        unit_id=unit_id, 
        history=history_list,
        latest=history_list[-1] if history_list else None,
        history_hours=24,
        read_interval_ms=TARGET_INTERVAL * 1000
    )

@app.route('/hikaku')
def hikaku():
    h1_all = get_historical_readings(days=1, unit_id="unit01")
    h2_all = get_historical_readings(days=1, unit_id="unit02")
    
    return render_template(
        'hikaku.html', 
        history_u1=[item._asdict() for item in h1_all[:]], 
        history_u2=[item._asdict() for item in h2_all[:]],
        read_interval_ms=TARGET_INTERVAL * 1000,
        apiUrlU1=url_for('api_latest', unit_id='unit01'),
        apiUrlU2=url_for('api_latest', unit_id='unit02')
    )

# --- API Endpoints ---

@app.route('/api/<unit_id>/latest')
def api_latest(unit_id):
    with cache_lock:
        data = latest_caches.get(unit_id)
        if data:
            return jsonify(data)
        return jsonify({"error": "No data available"}), 404

@app.route('/api/<unit_id>/history')
def api_history(unit_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "Missing parameters"}), 400
    
    from datetime import datetime
    d1 = datetime.strptime(start_date, '%Y-%m-%d')
    d2 = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (d2 - d1).days

    if delta_days >= 7:   skip_rate = 300 
    elif delta_days >= 3:  skip_rate = 60
    elif delta_days >= 1:  skip_rate = 5
    else:                  skip_rate = 1

    history_objs = get_historical_readings_by_range(start_date, end_date, unit_id, skip=skip_rate)
    return jsonify([item._asdict() for item in history_objs])

if __name__ == '__main__':
    modbus_client = OmronModbusClient(port='/dev/ttyACM0')
    monitor_thread = threading.Thread(target=monitoring_loop, args=(modbus_client,), daemon=True)
    monitor_thread.start()
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

import time
import threading
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
    """Background thread to poll Modbus data every second."""
    print("--- High-Speed Monitor Started ---")
    setup_database()
    cleanup_counter = 0
    
    while logging_running:
        start_time = time.time()
        # Read Unit 01 (Slave ID 1)
        try:
            data1 = client.read_data(slave_id=1) 
            if data1:
                log_reading(data1['val_voltage'], data1['val_current'], data1['val_energy_kwh'], "unit01")
                with cache_lock:
                    latest_caches['unit01'] = data1
        except Exception as e:
            print(f"U1 Read Error: {e}")

        time.sleep(0.05) # Transceiver breather

        # Read Unit 02 (Slave ID 2)
        try:
            data2 = client.read_data(slave_id=2)
            if data2:
                log_reading(data2['val_voltage'], data2['val_current'], data2['val_energy_kwh'], "unit02")
                with cache_lock:
                    latest_caches['unit02'] = data2
        except Exception as e:
            print(f"U2 Read Error: {e}")

        elapsed = time.time() - start_time
        sleep_time = max(0, TARGET_INTERVAL - elapsed)
        
        cleanup_counter += 1
        if cleanup_counter >= 3600:
            cleanup_old_data(30)
            cleanup_counter = 0

        time.sleep(sleep_time)

# --- Web Routes ---

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
    """Side-by-side comparison view (Renamed to match BuildError fix)."""
    h1 = get_historical_readings(days=1, unit_id="unit01")[-600:]
    h2 = get_historical_readings(days=1, unit_id="unit02")[-600:]
    
    return render_template(
        'hikaku.html', 
        history_u1=[item._asdict() for item in h1],
        history_u2=[item._asdict() for item in h2],
        read_interval_ms=TARGET_INTERVAL * 1000
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
    limit = request.args.get('limit', type=int)
    if limit:
        history_objs = get_historical_readings(days=1, unit_id=unit_id)
        return jsonify([item._asdict() for item in history_objs][-limit:])
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({"error": "Missing parameters"}), 400
        
    history_objs = get_historical_readings_by_range(start_date, end_date, unit_id)
    return jsonify([item._asdict() for item in history_objs])

if __name__ == '__main__':
    modbus_client = OmronModbusClient(port='/dev/ttyACM0')
    monitor_thread = threading.Thread(target=monitoring_loop, args=(modbus_client,), daemon=True)
    monitor_thread.start()
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

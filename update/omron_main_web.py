import time
import threading
from datetime import datetime
from flask import Flask, render_template_string

# Import Modbus functions
from omron_modbus import initialize_instrument, read_omron_data, minimalmodbus
# Import Database functions (including the new retrieval function)
from omron_database import setup_database, log_reading, cleanup_old_data, get_latest_readings

# --- Configuration ---
READ_INTERVAL_SECONDS = 5     # How often to poll the device
CLEANUP_INTERVAL_MINUTES = 60 # How often to run the database cleanup (once per hour)

# Global flag to control the logging thread
logging_running = True

# --- Flask App Setup ---
app = Flask(__name__)
# The server will run on http://127.0.0.1:5000/

# --- Logger Thread Function ---

def monitoring_loop(instrument):
    """
    The function executed in a separate thread to handle continuous data logging.
    """
    # 1. Setup Database
    setup_database()
    
    # 2. Main Logging Loop
    last_cleanup_time = time.time()
    
    global logging_running
    
    try:
        while logging_running:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Read data from the OMRON device
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
                    print(f"[{timestamp}] LOGGER LOGGED | V: {readings['voltage']:.2f}V | kW: {readings['power_kw']:.3f}kW | kWh: {readings['energy_kwh']:.5f}kWh")
                
            except minimalmodbus.ModbusException as e:
                print(f"[{timestamp}] MODBUS ERROR: {e}")
            except Exception as e:
                print(f"[{timestamp}] UNHANDLED ERROR: {e}")

            # Check for periodic cleanup
            if (time.time() - last_cleanup_time) > (CLEANUP_INTERVAL_MINUTES * 60):
                cleanup_old_data()
                last_cleanup_time = time.time()
                
            time.sleep(READ_INTERVAL_SECONDS) 

    except Exception as e:
        print(f"Logger thread terminated unexpectedly: {e}")
    finally:
        if instrument and instrument.serial.is_open:
            instrument.serial.close()
            print("Logger thread closing Modbus connection.")


# --- Flask Web Routes ---

@app.route('/')
def dashboard():
    """
    Renders the main monitoring dashboard using Bootstrap for styling.
    Fetches the latest 10 readings from the database.
    """
    readings = get_latest_readings(limit=10)
    
    # Simple HTML template for the dashboard
    # Tailwind CSS is not included in this simple setup; using Bootstrap CDN for fast styling.
    html_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Power Monitor</title>
    <!-- Bootstrap CSS for easy styling -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .container { max-width: 900px; margin-top: 40px; }
        .card { box-shadow: 0 4px 8px rgba(0,0,0,.05); border-radius: 10px; }
        .header { background-color: #007bff; color: white; padding: 15px; border-radius: 10px 10px 0 0; }
        .data-row { font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h3 class="mb-0">電力量モニタ</h3>
            </div>
            <div class="card-body">
                <p class="text-muted">Modbusロガーのリアルタイム値。最終更新： {{ datetime.now().strftime("%Y-%m-%d %H:%M:%S") }}</p>

                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>時間</th>
                            <th>電圧 (V)</th>
                            <th>電流 (A)</th>
                            <th>有効電力 (kW)</th>
                            <th>積算有効電力量 (kWh)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for reading in readings %}
                        <tr class="data-row">
                            <td>{{ reading.timestamp }}</td>
                            <td>{{ "%.2f"|format(reading.val_voltage) }}</td>
                            <td>{{ "%.3f"|format(reading.val_current) }}</td>
                            <td>{{ "%.3f"|format(reading.val_power_kw) }}</td>
                            <td>{{ "%.5f"|format(reading.val_energy_kwh) }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" class="text-center text-danger">No data logged yet. Check logger thread status.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
                <p class="mt-4 text-center">データ保存：{{ 30 }} 日間. 記録間隔: {{ 5 }} 秒.</p>
            </div>
        </div>
    </div>
    <!-- Script to auto-refresh the page every 5 seconds -->
    <script>
        setTimeout(function(){
           window.location.reload(1);
        }, 5000);
    </script>
</body>
</html>
    """
    return render_template_string(html_template, readings=readings, datetime=datetime)

# --- Main Execution ---

if __name__ == '__main__':
    
    # 1. Setup Modbus Instrument
    instrument = initialize_instrument()
    if not instrument:
        print("FATAL: Cannot initialize Modbus instrument. Web monitor starting without logging.")
        # If Modbus fails, still start the web server to show the error/empty data
        pass

    # 2. Start the Monitoring/Logging thread
    if instrument:
        logger_thread = threading.Thread(target=monitoring_loop, args=(instrument,), daemon=True)
        logger_thread.start()
        print("----------------------------------------------------------------------")
        print(f"Logger thread started (interval: {READ_INTERVAL_SECONDS}s).")
        print("----------------------------------------------------------------------")

    # 3. Start the Flask Web Server
    print("Starting Flask Web Server...")
    print("Dashboard available at: http://127.0.0.1:5000/")
    
    # Use a try/finally block to ensure the logging thread is stopped gracefully
    try:
        app.run(host='0.0.0.0', port=5200, debug=False)
    except KeyboardInterrupt:
        print("\nWeb server stopped by user.")
    finally:
        print("Stopping logger thread...")
        logging_running = False
        # Give the logger thread a moment to shut down gracefully
        if 'logger_thread' in locals() and logger_thread.is_alive():
             logger_thread.join(timeout=10)
        print("Application shutdown complete.")

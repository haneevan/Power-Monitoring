# omron_main_web.py
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from omron_database import (
    get_historical_readings, 
    get_historical_readings_by_range
)

app = Flask(__name__)

# --- Configuration ---
PORT = 5200
DB_MAIN = 'omron.db'

def get_latest_from_db(unit_id):
    """Fetches the single most recent row for a specific unit from the database."""
    try:
        conn = sqlite3.connect(DB_MAIN)
        conn.row_factory = sqlite3.Row  # Crucial: allows access by column name
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM readings 
            WHERE unit_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        """, (unit_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Latest DB Read Error: {e}")
        return None

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

    # Fetch 24h history
    history_list = get_historical_readings(days=1, unit_id=unit_id)
    
    return render_template(
        'dashboard.html', 
        unit_id=unit_id, 
        history=history_list,
        latest=history_list[-1] if history_list else None,
        history_hours=24,
        read_interval_ms=1000  # Matches your new collector speed
    )

@app.route('/hikaku')
def hikaku():
    """Comparison view for both units."""
    h1_all = get_historical_readings(days=1, unit_id="unit01")
    h2_all = get_historical_readings(days=1, unit_id="unit02")
    
    return render_template(
        'hikaku.html', 
        history_u1=h1_all, 
        history_u2=h2_all,
        read_interval_ms=1000,
        apiUrlU1=url_for('api_latest', unit_id='unit01'),
        apiUrlU2=url_for('api_latest', unit_id='unit02')
    )

# --- API Endpoints ---

@app.route('/api/<unit_id>/latest')
def api_latest(unit_id):
    """Endpoint for real-time card updates via JavaScript."""
    data = get_latest_from_db(unit_id)
    if data:
        return jsonify(data)
    return jsonify({"error": "No data available"}), 404

@app.route('/api/<unit_id>/history')
def api_history(unit_id):
    """Endpoint for date-range filtered history."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "Missing parameters"}), 400
    
    # Calculate skip rate for performance
    d1 = datetime.strptime(start_date, '%Y-%m-%d')
    d2 = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (d2 - d1).days

    if delta_days >= 7:    skip_rate = 300 
    elif delta_days >= 3:  skip_rate = 60
    elif delta_days >= 1:  skip_rate = 5
    else:                  skip_rate = 1

    history_objs = get_historical_readings_by_range(
        start_date, end_date, unit_id, skip=skip_rate
    )
    return jsonify(history_objs)

@app.route('/api/weekly_summary')
def get_weekly_summary():
    """Aggregated average current for the last 7 days."""
    try:
        db = sqlite3.connect(DB_MAIN)
        cursor = db.cursor()
        
        query = """
            SELECT strftime('%m/%d', timestamp) as day, 
                   AVG(val_current) as avg_val
            FROM readings
            WHERE unit_id = ? 
            AND timestamp >= date('now', '-7 days')
            GROUP BY day
            ORDER BY timestamp ASC
        """
        
        cursor.execute(query, ("unit01",))
        u1_dict = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute(query, ("unit02",))
        u2_dict = {row[0]: row[1] for row in cursor.fetchall()}
        db.close()

        all_dates = sorted(list(set(u1_dict.keys()) | set(u2_dict.keys())))

        return jsonify({
            "labels": all_dates,
            "u1": [round(u1_dict.get(day, 0), 3) for day in all_dates],
            "u2": [round(u2_dict.get(day, 0), 3) for day in all_dates]
        })
    except Exception as e:
        print(f"Weekly Summary Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/weekly_energy_summary')
def get_weekly_energy_summary():
    """Calculates daily kWh consumption (Daily Max - Daily Min) for the last 7 days."""
    try:
        db = sqlite3.connect(DB_MAIN)
        cursor = db.cursor()
        
        # This query calculates the delta (Max - Min) for each day
        query = """
            SELECT strftime('%m/%d', timestamp) as day, 
                   (MAX(val_energy_kwh) - MIN(val_energy_kwh)) as daily_usage
            FROM readings
            WHERE unit_id = ? 
            AND timestamp >= date('now', '-7 days')
            GROUP BY day
            ORDER BY timestamp ASC
        """
        
        # Fetch for Unit 01
        cursor.execute(query, ("unit01",))
        u1_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch for Unit 02
        cursor.execute(query, ("unit02",))
        u2_data = {row[0]: row[1] for row in cursor.fetchall()}
        db.close()

        # Combine dates from both units to ensure the X-axis is aligned
        all_dates = sorted(list(set(u1_data.keys()) | set(u2_data.keys())))

        return jsonify({
            "labels": all_dates,
            "u1": [round(u1_data.get(day, 0), 3) for day in all_dates],
            "u2": [round(u2_data.get(day, 0), 3) for day in all_dates]
        })
    except Exception as e:
        print(f"Weekly Energy Summary Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/monthly_energy_summary')
def get_monthly_energy_summary():
    """Calculates daily kWh consumption for the last 30 days for the monthly bar chart."""
    try:
        db = sqlite3.connect(DB_MAIN)
        cursor = db.cursor()
        
        # Query to get daily usage (Max kWh - Min kWh) for each day in the last 30 days
        query = """
            SELECT strftime('%m/%d', timestamp) as day, 
                   (MAX(val_energy_kwh) - MIN(val_energy_kwh)) as daily_usage
            FROM readings
            WHERE unit_id = ? 
            AND timestamp >= date('now', '-30 days')
            GROUP BY day
            ORDER BY timestamp ASC
        """
        
        # Fetch data for Unit 01
        cursor.execute(query, ("unit01",))
        u1_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch data for Unit 02
        cursor.execute(query, ("unit02",))
        u2_data = {row[0]: row[1] for row in cursor.fetchall()}
        db.close()

        # Merge all unique dates from both units to keep the chart X-axis synchronized
        all_dates = sorted(list(set(u1_data.keys()) | set(u2_data.keys())))

        return jsonify({
            "labels": all_dates,
            "u1": [round(u1_data.get(day, 0), 3) for day in all_dates],
            "u2": [round(u2_data.get(day, 0), 3) for day in all_dates]
        })
    except Exception as e:
        print(f"Monthly Energy Summary Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Flask is now just a web gateway. No hardware threads!
    app.run(host='0.0.0.0', port=PORT, debug=False)

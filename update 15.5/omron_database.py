import sqlite3
import time
import os
from datetime import datetime
from omron_modbus import OmronModbusClient, OmronReadError

DB_NAME = 'omron.db'
TARGET_INTERVAL = 1.0  # Target speed: 1 second per cycle
CLEANUP_THRESHOLD = 3600 # Run cleanup roughly every hour (3600 seconds)

def setup_database():
    """Initializes the database with WAL mode for microservice compatibility."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode=WAL;')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            val_voltage REAL NOT NULL,
            val_current REAL NOT NULL,
            val_power_kw REAL NOT NULL,
            val_energy_kwh REAL NOT NULL,
            unit_id TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unit_timestamp ON readings (unit_id, timestamp)')
    conn.commit()
    conn.close()

def cleanup_old_data(days=30):
    """Deletes records older than 30 days to preserve space."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readings WHERE timestamp < datetime('now', ?, 'localtime')", (f"-{days} day",))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted_count > 0:
            print(f"[{datetime.now()}] --- CLEANUP: Deleted {deleted_count} old records ---")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] Database Cleanup Error: {e}")

def get_historical_readings(days=1, unit_id="unit01"):
    """Fetches records for the last X days for the dashboard charts."""
    try:
        conn = sqlite3.connect(DB_NAME)
        # Use Row factory so we can return dictionaries
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = """
            SELECT * FROM readings 
            WHERE unit_id = ? 
            AND timestamp >= datetime('now', ?, 'localtime') 
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (unit_id, f"-{days} day"))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"History Fetch Error: {e}")
        return []

def get_historical_readings_by_range(start_date, end_date, unit_id="unit01", skip=1):
    """Fetches records for specific dates with downsampling for the comparison view."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = """
            SELECT * FROM readings 
            WHERE unit_id = ? 
            AND date(timestamp) BETWEEN ? AND ? 
            AND (id % ? = 0)
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (unit_id, start_date, end_date, skip))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Range Fetch Error: {e}")
        return []

def run_collector():
    """The main loop for the omron-data.service"""
    setup_database()
    client = OmronModbusClient()
    units = [1, 2] 
    cleanup_timer = 0
    
    print(f"[{datetime.now()}] Data Collection Service Started (1s Target Interval)")
    
    while True:
        start_time = time.time()
        
        for slave_id in units:
            unit_label = f"unit0{slave_id}"
            try:
                data = client.read_data(slave_id)
                
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                fixed_kw = abs(data['val_power_kw'])
                
                cursor.execute('''
                    INSERT INTO readings (
                        timestamp, val_voltage, val_current, 
                        val_power_kw, val_energy_kwh, unit_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (data['timestamp'], data['val_voltage'], data['val_current'], 
                      fixed_kw, data['val_energy_kwh'], unit_label))
                
                conn.commit()
                conn.close()

                print(f"[{data['timestamp']}] {unit_label.upper()} | "
                      f"{data['val_voltage']}V | {data['val_current']}A | "
                      f"{fixed_kw}kW | {data['val_energy_kwh']}kWh")

            except OmronReadError as e:
                print(f"[{datetime.now()}] ERROR: {e}")
            except Exception as e:
                print(f"[{datetime.now()}] SYSTEM CRITICAL: {e}")

        # --- AUTO-DELETE LOGIC ---
        # Checks every hour to see if old data needs purging
        cleanup_timer += (time.time() - start_time)
        if cleanup_timer >= CLEANUP_THRESHOLD:
            cleanup_old_data(30)
            cleanup_timer = 0

        # --- SMART TIMING ---
        # Calculates exactly how long to sleep to maintain a 1-second pace
        elapsed = time.time() - start_time
        time.sleep(max(0, TARGET_INTERVAL - elapsed))

if __name__ == "__main__":
    run_collector()

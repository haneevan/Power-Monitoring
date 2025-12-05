from datetime import datetime, timedelta
import sqlite3

# --- Configuration ---
datafile = 'omron_data.db'
# We will keep data for 30 days
RETENTION_DAYS = 30 

def setup_database():
    """
    Sets up the SQLite database and creates the required tables.
    """
    # Using 'with' for connection ensures it is properly closed, even if errors occur.
    conn = sqlite3.connect(datafile, timeout=5.0)
    cursor = conn.cursor()
    # Write-Ahead Logging (WAL) mode improves concurrency (read/write access)
    cursor.execute('PRAGMA journal_mode=WAL;')
    
    # Table structure updated to use more descriptive names
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            val_voltage REAL NOT NULL,
            val_current REAL NOT NULL,
            val_power_kw REAL NOT NULL,
            val_energy_kwh REAL NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database setup complete. Table 'readings' ready in {datafile}.")
    
def log_reading(v, a, kw, kwh):
    """
    Logs a single set of readings into the database.
    
    Args:
        v (float): Voltage reading (V)
        a (float): Current reading (A)
        kw (float): Power reading (kW)
        kwh (float): Accumulated Energy reading (kWh)
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = sqlite3.connect(datafile, timeout=5.0)
        cursor = conn.cursor()
        
        # Use parameterized query (the '?' placeholders) to safely insert data
        cursor.execute('''
            INSERT INTO readings (timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp_str, v, a, kw, kwh))
        
        conn.commit()
        # print(f"Logged: {timestamp_str} | {kw:.3f} kW") # Optional: uncomment for verbose logging
        
    except sqlite3.Error as e:
        print(f"Database Error during logging: {e}")
    finally:
        if conn:
            conn.close()

def cleanup_old_data():
    """
    Removes data older than RETENTION_DAYS (30 days) from the database.
    """
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = sqlite3.connect(datafile, timeout=5.0)
        cursor = conn.cursor()
        
        # Delete rows where the timestamp is older than the cutoff date
        cursor.execute('''
            DELETE FROM readings
            WHERE timestamp < ?
        ''', (cutoff_date_str,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Database cleanup: Removed {deleted_count} old records (older than {cutoff_date_str}).")
        
    except sqlite3.Error as e:
        print(f"Database Error during cleanup: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Example usage:
    setup_database()
    
    # Simulate a reading
    sim_v, sim_a, sim_kw, sim_kwh = 205.1, 1.503, 0.308, 1500.254
    log_reading(sim_v, sim_a, sim_kw, sim_kwh)
    print(f"Simulated data logged.")

    # Execute cleanup (won't delete anything yet, as data is new)
    cleanup_old_data()

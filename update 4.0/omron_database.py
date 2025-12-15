# omron_database.py

import sqlite3
from datetime import datetime, timedelta
import collections

# --- Configuration (Updated) ---
datafile = 'omron_data.db' 
RETENTION_DAYS = 30 
READING_FIELDS = ['timestamp', 'val_voltage', 'val_current', 'val_energy_kwh'] 

# Define the namedtuple here
Reading = collections.namedtuple('Reading', READING_FIELDS)


def setup_database():
    """
    Sets up the SQLite database, creates the 'readings' table, and ensures a 
    WAL journal mode and an index on the timestamp column for performance.
    """
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('PRAGMA journal_mode=WAL;')
            
            # Create the readings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    val_voltage REAL NOT NULL,
                    val_current REAL NOT NULL,
                    val_energy_kwh REAL NOT NULL 
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON readings (timestamp);
            ''')
            
            conn.commit()
        print(f"Database setup complete. Table 'readings' ready in {datafile}.")
    except sqlite3.Error as e:
        print(f"FATAL: Database setup failed: {e}")
    
def log_reading(v, a, kwh):
    """
    Logs a single set of readings into the database.
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO readings (timestamp, val_voltage, val_current, val_energy_kwh)
                VALUES (?, ?, ?, ?)
            ''', (timestamp_str, v, a, kwh))
            
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database Error during logging: {e}")

def cleanup_old_data():
    """
    Removes data older than RETENTION_DAYS (30 days) from the database.
    """
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM readings
                WHERE timestamp < ?
            ''', (cutoff_date_str,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"Database cleanup: Removed {deleted_count} old records.")
            
    except sqlite3.Error as e:
        print(f"Database Error during cleanup: {e}")

def get_latest_readings(limit=1):
    """
    Retrieves the most recent readings from the database, ordered by timestamp descending.
    """
    readings = []
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, val_voltage, val_current, val_energy_kwh
                FROM readings
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            for row in cursor.fetchall():
                readings.append(Reading(
                    timestamp=row['timestamp'], 
                    val_voltage=row['val_voltage'], 
                    val_current=row['val_current'], 
                    val_energy_kwh=row['val_energy_kwh']
                ))
                
    except sqlite3.Error as e:
        print(f"Database Error during retrieval: {e}")
        
    return readings

def get_historical_readings(days=1):
    """
    Retrieves historical readings for charting purposes (default home view).
    """
    readings = []
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, val_voltage, val_current, val_energy_kwh
                FROM readings
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (cutoff_date_str,))
            
            for row in cursor.fetchall():
                 readings.append(Reading(
                    timestamp=row['timestamp'], 
                    val_voltage=row['val_voltage'], 
                    val_current=row['val_current'], 
                    val_energy_kwh=row['val_energy_kwh']
                ))
                
    except sqlite3.Error as e:
        print(f"Database Error during historical retrieval: {e}")
        
    return readings
    
def get_historical_readings_by_range(start_date_str, end_date_str):
    """
    Retrieves historical readings with intelligent granularity based on range length.
    """
    readings = []
    
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Calculate the total span in days (inclusive)
        time_diff = end_dt - start_dt
        total_days = time_diff.days + 1
        
        start_dt_inclusive_str = f"{start_date_str} 00:00:00"
        end_dt_inclusive_str = f"{end_date_str} 23:59:59"

        # --- Granularity Selection Logic ---
        if total_days <= 1:
            # 1 Day: 5-minute averaging for high detail
            INTERVAL_MINUTES = 5 
        elif total_days <= 7:
            # 2 to 7 Days: 30-minute averaging
            INTERVAL_MINUTES = 30
        else:
            # More than 7 Days: 60-minute (1 hour) averaging
            INTERVAL_MINUTES = 60
            
        print(f"Querying data for {total_days} days. Using {INTERVAL_MINUTES}-minute interval.")
        
        # SQLite Grouping Key (Truncates time to the start of the interval)
        GROUPING_QUERY = f"""
        strftime('%Y-%m-%d %H:', timestamp) || 
        (CAST(strftime('%M', timestamp) AS INT) / {INTERVAL_MINUTES}) * {INTERVAL_MINUTES} ||
        ':00'
        """

        with sqlite3.connect(datafile, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Aggregate query: AVG for V/A, MAX for cumulative kWh
            query = f"""
            SELECT 
                {GROUPING_QUERY} AS group_timestamp,
                AVG(val_voltage) AS avg_voltage,
                AVG(val_current) AS avg_current,
                MAX(val_energy_kwh) AS max_energy_kwh
            FROM readings
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY group_timestamp
            ORDER BY group_timestamp ASC
            """
            
            cursor.execute(query, (start_dt_inclusive_str, end_dt_inclusive_str))
            
            for row in cursor.fetchall():
                 readings.append(Reading(
                    timestamp=row['group_timestamp'], 
                    val_voltage=row['avg_voltage'], 
                    val_current=row['avg_current'], 
                    val_energy_kwh=row['max_energy_kwh'] 
                ))
                
    except sqlite3.Error as e:
        print(f"Database Error during intelligent ranged retrieval: {e}")
    except ValueError as e:
        print(f"Date conversion error: {e}")
        
    return readings

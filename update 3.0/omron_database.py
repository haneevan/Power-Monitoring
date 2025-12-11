import sqlite3
from datetime import datetime, timedelta
import collections

# --- Configuration (Updated) ---
datafile = 'omron_data.db' 
RETENTION_DAYS = 30 
READING_FIELDS = ['timestamp', 'val_voltage', 'val_current', 'val_energy_kwh'] # val_power_kw removed

def setup_database():
    """
    Sets up the SQLite database, creates the 'readings' table, and ensures a 
    WAL journal mode and an index on the timestamp column for performance.
    """
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('PRAGMA journal_mode=WAL;')
            
            # 2. Create the readings table (Updated)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    val_voltage REAL NOT NULL,
                    val_current REAL NOT NULL,
                    val_energy_kwh REAL NOT NULL 
                    -- val_power_kw REMOVED
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
    
def log_reading(v, a, kwh): # kw parameter removed
    """
    Logs a single set of readings into the database.
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            
            # val_power_kw removed from column list and VALUES tuple
            cursor.execute('''
                INSERT INTO readings (timestamp, val_voltage, val_current, val_energy_kwh)
                VALUES (?, ?, ?, ?)
            ''', (timestamp_str, v, a, kwh))
            
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database Error during logging: {e}")

def cleanup_old_data():
    """
    Removes data older than RETENTION_DAYS (30 days) from the database. (No change needed)
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
    
    Reading = collections.namedtuple('Reading', READING_FIELDS)
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # val_power_kw removed from SELECT statement
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
    Retrieves historical readings for charting purposes.
    """
    readings = []
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    Reading = collections.namedtuple('Reading', READING_FIELDS)
    
    try:
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # val_power_kw removed from SELECT statement
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

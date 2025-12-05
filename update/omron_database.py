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
    try:
        # Using 'with' for connection ensures it is properly closed, even if errors occur.
        with sqlite3.connect(datafile, timeout=5.0) as conn:
            cursor = conn.cursor()
            # Write-Ahead Logging (WAL) mode improves concurrency (read/write access)
            # This is important for concurrent read/write access (Logger writes, Web reads)
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
        print(f"Database setup complete. Table 'readings' ready in {datafile}.")
    except sqlite3.Error as e:
        print(f"FATAL: Database setup failed: {e}")
    
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
    
    conn = None # Initialize conn outside the try block
    try:
        conn = sqlite3.connect(datafile, timeout=5.0)
        cursor = conn.cursor()
        
        # Use parameterized query (the '?' placeholders) to safely insert data
        cursor.execute('''
            INSERT INTO readings (timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp_str, v, a, kw, kwh))
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database Error during logging: {e}")
    finally:
        if conn:
            conn.close()

def get_latest_readings(limit=10):
    """
    Retrieves the most recent N readings from the database.
    
    Args:
        limit (int): The number of latest records to return.
        
    Returns:
        list of dicts: A list of the latest reading dictionaries, or an empty list on failure.
    """
    conn = None
    try:
        conn = sqlite3.connect(datafile, timeout=5.0)
        # Set row_factory to sqlite3.Row to allow accessing columns by name (dict-like)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # Query to select the latest records by ordering by timestamp descending
        cursor.execute(f'''
            SELECT timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh 
            FROM readings
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        # Convert sqlite3.Row objects to standard dictionaries
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
        
    except sqlite3.Error as e:
        print(f"Database Error during retrieval: {e}")
        return []
    finally:
        if conn:
            conn.close()

def cleanup_old_data():
    """
    Removes data older than RETENTION_DAYS (30 days) from the database.
    """
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = None
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

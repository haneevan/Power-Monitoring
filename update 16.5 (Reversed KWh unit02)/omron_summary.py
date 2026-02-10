import sqlite3
import os
from datetime import datetime
from collections import namedtuple

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_MAIN = os.path.join(BASE_DIR, 'omron.db')
DB_SUB = os.path.join(BASE_DIR, 'summary.db')

# Structure: id | date | unit_id | avg_a | daily_kwh | total_kwh
DailySummary = namedtuple('DailySummary', ['date', 'unit_id', 'avg_a', 'daily_kwh', 'total_kwh'])

def init_sub_db():
    """Ensures the summary database and table exist with the new flexible schema."""
    with sqlite3.connect(DB_SUB) as conn:
        # We use an auto-increment ID to allow multiple entries per day
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                unit_id TEXT,
                avg_a REAL,
                daily_kwh REAL,
                total_kwh REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def process_and_save_daily_data(unit_id, target_date):
    """
    Queries main DB, detects abnormalities/resets, 
    and saves sessions to the summary database.
    """
    with sqlite3.connect(DB_MAIN) as conn:
        cursor = conn.cursor()
        # Fetch all readings for the day to detect reset jumps
        cursor.execute("""
            SELECT val_current, val_energy_kwh 
            FROM readings 
            WHERE unit_id = ? AND timestamp LIKE ? 
            ORDER BY timestamp ASC
        """, (unit_id, f"{target_date}%"))
        
        rows = cursor.fetchall()
        
    if not rows:
        return

    conn_sub = sqlite3.connect(DB_SUB)
    
    session_start_kwh = rows[0][1]
    session_currents = []
    
    # Iterate through readings to find the 'break points' (resets)
    for i in range(len(rows)):
        curr_a, curr_kwh = rows[i]
        session_currents.append(abs(curr_a))
        
        # Check if a reset occurs: the next reading is significantly lower than the current
        is_reset = False
        if i + 1 < len(rows):
            next_kwh = rows[i+1][1]
            if next_kwh < curr_kwh:
                is_reset = True
        
        # If we hit a reset or the end of the data, close the current session
        if is_reset or i == len(rows) - 1:
            avg_a = round(sum(session_currents) / len(session_currents), 2)
            
            # Daily kWh for this session is Current - Start
            # We use max(0, ...) to prevent tiny negative noise from showing up
            delta_kwh = max(0, round(curr_kwh - session_start_kwh, 3))
            
            conn_sub.execute("""
                INSERT INTO daily_summaries (date, unit_id, avg_a, daily_kwh, total_kwh)
                VALUES (?, ?, ?, ?, ?)
            """, (target_date, unit_id, avg_a, delta_kwh, curr_kwh))
            
            # If there was a reset, prepare to start the next session immediately
            if is_reset:
                session_start_kwh = rows[i+1][1]
                session_currents = []
                
    conn_sub.commit()
    conn_sub.close()

def run_nightly_job():
    """Main function to be triggered by crontab."""
    init_sub_db()
    today = datetime.now().strftime('%Y-%m-%d')
    units = ['unit01', 'unit02']

    for uid in units:
        try:
            process_and_save_daily_data(uid, today)
            print(f"[{datetime.now()}] Success: Processed sessions for {uid} on {today}")
        except Exception as e:
            print(f"[{datetime.now()}] Error processing {uid}: {e}")

if __name__ == "__main__":
    run_nightly_job()

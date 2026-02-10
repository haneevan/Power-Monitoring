import sqlite3
import os
from datetime import datetime

DB_MAIN = 'omron.db'
DB_SUB = 'summary.db'

def setup_db():
    if os.path.exists(DB_SUB):
        os.remove(DB_SUB)
    conn = sqlite3.connect(DB_SUB)
    conn.execute("""
        CREATE TABLE daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            unit_id TEXT,
            avg_a REAL,
            daily_kwh REAL,
            total_kwh REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def run_migration():
    setup_db()
    conn_main = sqlite3.connect(DB_MAIN)
    cursor_main = conn_main.cursor()
    
    # Get unique days and units
    cursor_main.execute("SELECT DISTINCT date(timestamp), unit_id FROM readings ORDER BY timestamp ASC")
    work_list = cursor_main.fetchall()
    
    conn_sub = sqlite3.connect(DB_SUB)
    
    for day, unit in work_list:
        print(f"Processing {day} | {unit}...")
        cursor_main.execute("""
            SELECT val_current, val_energy_kwh 
            FROM readings 
            WHERE unit_id = ? AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (unit, day))
        rows = cursor_main.fetchall()
        
        if not rows: continue

        # Logic to split rows on reset
        session_start_kwh = rows[0][1]
        session_currents = []
        
        for i in range(len(rows)):
            curr_a, curr_kwh = rows[i]
            session_currents.append(abs(curr_a))
            
            # Detect Reset: If next value exists and is lower than current
            is_reset = False
            if i + 1 < len(rows):
                next_kwh = rows[i+1][1]
                if next_kwh < curr_kwh:
                    is_reset = True
            
            # If it's a reset OR the end of the day, save the session
            if is_reset or i == len(rows) - 1:
                daily_delta = round(curr_kwh - session_start_kwh, 3)
                # Handle edge case where delta might be negative due to noise
                daily_delta = max(0, daily_delta) 
                
                avg_a = round(sum(session_currents) / len(session_currents), 2)
                
                conn_sub.execute("""
                    INSERT INTO daily_summaries (date, unit_id, avg_a, daily_kwh, total_kwh)
                    VALUES (?, ?, ?, ?, ?)
                """, (day, unit, avg_a, daily_delta, curr_kwh))
                
                # Start new session logic
                if is_reset:
                    session_start_kwh = rows[i+1][1]
                    session_currents = []

    conn_sub.commit()
    conn_main.close()
    conn_sub.close()
    print("Migration Complete with Reset-Detection logic.")

if __name__ == "__main__":
    run_migration()

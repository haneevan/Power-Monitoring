import sqlite3
import os
from datetime import datetime
from collections import namedtuple

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_MAIN = os.path.join(BASE_DIR, 'omron.db')
DB_SUB = os.path.join(BASE_DIR, 'summary.db')

# Represents the aggregated data for the sub-database
# kwh = daily delta (usage), kwh_total = absolute meter reading
DailySummary = namedtuple('DailySummary', ['date', 'u1_avg_a', 'u1_kwh', 'u1_kwh_total', 'u2_avg_a', 'u2_kwh', 'u2_kwh_total'])

def init_sub_db():
    """Ensures the summary database and table exist with total accumulation columns."""
    with sqlite3.connect(DB_SUB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                date TEXT PRIMARY KEY,
                u1_a_avg REAL,
                u1_kwh REAL,
                u1_kwh_total REAL,
                u2_a_avg REAL,
                u2_kwh REAL,
                u2_kwh_total REAL
            )
        """)

def get_daily_stats(unit_id, target_date):
    """Queries main DB and returns aggregated stats for a specific unit."""
    with sqlite3.connect(DB_MAIN) as conn:
        cursor = conn.cursor()
        # Query 1: Average and Delta Usage
        # Query 2: Max Reading (Accumulated total)
        query = """
            SELECT AVG(ABS(val_current)), 
                   MAX(val_energy_kwh) - MIN(val_energy_kwh),
                   MAX(val_energy_kwh)
            FROM readings 
            WHERE unit_id = ? AND timestamp LIKE ?
        """
        cursor.execute(query, (unit_id, f"{target_date}%"))
        row = cursor.fetchone()
        
        return {
            'avg_a': round(row[0] or 0, 2),
            'kwh_delta': round(row[1] or 0, 3),
            'kwh_total': round(row[2] or 0, 3)
        }

def save_summary(summary):
    """Saves the DailySummary namedtuple into the sub-database."""
    with sqlite3.connect(DB_SUB) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_summaries 
            (date, u1_a_avg, u1_kwh, u1_kwh_total, u2_a_avg, u2_kwh, u2_kwh_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (summary.date, summary.u1_avg_a, summary.u1_kwh, summary.u1_kwh_total, 
              summary.u2_avg_a, summary.u2_kwh, summary.u2_kwh_total))

def run_nightly_job():
    init_sub_db()
    today = datetime.now().strftime('%Y-%m-%d')
    
    u1_stats = get_daily_stats('unit01', today)
    u2_stats = get_daily_stats('unit02', today)
    
    report = DailySummary(
        date=today,
        u1_avg_a=u1_stats['avg_a'],
        u1_kwh=u1_stats['kwh_delta'],
        u1_kwh_total=u1_stats['kwh_total'],
        u2_avg_a=u2_stats['avg_a'],
        u2_kwh=u2_stats['kwh_delta'],
        u2_kwh_total=u2_stats['kwh_total']
    )
    
    save_summary(report)
    print(f"[{datetime.now()}] Success: {today} | U1: {report.u1_kwh}kWh (Total: {report.u1_kwh_total})")

if __name__ == "__main__":
    run_nightly_job()

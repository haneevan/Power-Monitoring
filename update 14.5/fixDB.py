import sqlite3

def fix_reversed_data():
    db = sqlite3.connect('omron.db')
    cursor = db.cursor()
    
    # 1. Flip any negative power or current to positive
    cursor.execute("""
        UPDATE readings 
        SET val_current = ABS(val_current),
            val_power_kw = ABS(val_power_kw)
        WHERE val_current < 0 OR val_power_kw < 0
    """)
    
    # 2. Fix the Energy Trend
    # If Unit 02 energy has been decreasing, we find the max value 
    # and subtract the current value from it to simulate an 'increase'
    cursor.execute("SELECT MAX(val_energy_kwh) FROM readings WHERE unit_id = 'unit02'")
    max_val = cursor.fetchone()[0] or 0
    
    if max_val > 0:
        # This logic is a 'best effort' to make the energy look like it's increasing
        cursor.execute("""
            UPDATE readings 
            SET val_energy_kwh = ? + (? - val_energy_kwh)
            WHERE unit_id = 'unit02'
        """, (max_val, max_val))
        
    db.commit()
    db.close()
    print("Database cleanup complete.")

if __name__ == "__main__":
    fix_reversed_data()

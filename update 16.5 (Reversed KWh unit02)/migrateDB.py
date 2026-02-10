import sqlite3
import os

DB_NAME = 'omron.db'

def migrate():
    if not os.path.exists(DB_NAME):
        print("Database not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        print("Starting migration to remove Power Factor column...")

        # 1. Create a temporary table with the NEW 7-field structure (including ID)
        cursor.execute('''
            CREATE TABLE readings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                val_voltage REAL NOT NULL,
                val_current REAL NOT NULL,
                val_power_kw REAL NOT NULL,
                val_energy_kwh REAL NOT NULL,
                unit_id TEXT NOT NULL
            )
        ''')

        # 2. Check existing columns to see what we can save
        cursor.execute("PRAGMA table_info(readings)")
        columns = [info[1] for info in cursor.fetchall()]

        # 3. Move data (Mapping old columns to new columns)
        # We ignore val_power_factor during this move
        if 'val_power_kw' in columns:
            print("Preserving existing kW data...")
            cursor.execute('''
                INSERT INTO readings_new (id, timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh, unit_id)
                SELECT id, timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh, unit_id FROM readings
            ''')
        else:
            print("kW column didn't exist yet, initializing with 0.0...")
            cursor.execute('''
                INSERT INTO readings_new (id, timestamp, val_voltage, val_current, val_power_kw, val_energy_kwh, unit_id)
                SELECT id, timestamp, val_voltage, val_current, 0.0, val_energy_kwh, unit_id FROM readings
            ''')

        # 4. Drop old table and rename new one
        cursor.execute("DROP TABLE readings")
        cursor.execute("ALTER TABLE readings_new RENAME TO readings")

        # 5. Re-create the index for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_unit_timestamp ON readings (unit_id, timestamp)')

        conn.commit()
        print("Migration successful! Power Factor column removed.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

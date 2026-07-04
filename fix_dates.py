import database
import random
from datetime import datetime, timedelta

conn = database.get_connection()
cur = conn.cursor()

cur.execute("SELECT id FROM sponsorship_signals")
rows = cur.fetchall()

now = datetime.now()
count = 0

for row in rows:
    sig_id = row[0]
    # Spread dates over the last 90 days
    days_ago = random.randint(0, 90)
    new_date = now - timedelta(days=days_ago, hours=random.randint(0,23), minutes=random.randint(0,59))
    new_date_iso = new_date.isoformat() + "Z"
    
    if database.HAS_POSTGRES:
        cur.execute("UPDATE sponsorship_signals SET detected_at = %s WHERE id = %s", (new_date_iso, sig_id))
    else:
        cur.execute("UPDATE sponsorship_signals SET detected_at = ? WHERE id = ?", (new_date_iso, sig_id))
    count += 1

conn.commit()
print(f"Updated dates for {count} signals.")

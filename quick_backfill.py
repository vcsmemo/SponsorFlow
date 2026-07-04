import database
import batch_runner
import time

conn = database.get_connection()
cur = conn.cursor()
cur.execute("SELECT id, name, platform FROM channels WHERE followers = 0")
rows = cur.fetchall()

print(f"Found {len(rows)} channels with 0 followers. Running DDG+LLM engine...")

for row in rows:
    ch_id, name, platform = row
    print(f"Processing: {name} ({platform})")
    
    # Use our new powerful engine!
    new_followers = batch_runner.get_followers_via_llm(name, platform)
    
    if new_followers > 0:
        print(f"  -> Extracted: {new_followers}")
        database.execute_write(conn, "UPDATE channels SET followers = ? WHERE id = ?", (new_followers, ch_id))
    else:
        print(f"  -> Failed to extract.")
        
    time.sleep(1)

conn.close()
print("Done!")

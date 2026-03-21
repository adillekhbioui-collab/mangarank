import os, json, sys
import httpx
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def main():
    print("Checking manga_raw summaries...", flush=True)
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    
    url = f"{SUPABASE_URL}/rest/v1/manga_raw?select=id,title,summary,source_site&limit=5"
    print(f"GET {url}")
    r = httpx.get(url, headers=headers, timeout=10)
    print("Status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print("Text:", r.text)
        
    print("\nAttempting to reload schema cache...", flush=True)
    url_rpc = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    r2 = httpx.post(url_rpc, headers=headers, json={"query": "NOTIFY pgrst, reload schema;"}, timeout=10)
    print("Reload status:", r2.status_code)

if __name__ == "__main__":
    main()

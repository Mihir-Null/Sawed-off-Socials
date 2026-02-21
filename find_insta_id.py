import os
import requests
from dotenv import load_dotenv

load_dotenv()

def find_instagram_ids():
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        print("❌ Error: INSTAGRAM_ACCESS_TOKEN not found in .env file.")
        print("Please add your token to the .env file first.")
        return

    print("🔍 Fetching associated Facebook Pages...")
    pages_url = f"https://graph.facebook.com/v22.0/me/accounts?fields=name,id,instagram_business_account&access_token={token}"
    
    try:
        response = requests.get(pages_url)
        data = response.json()
        
        if "error" in data:
            print(f"❌ API Error: {data['error'].get('message')}")
            return

        pages = data.get("data", [])
        
        if not pages:
            print("⚠️ No Facebook Pages found for this token.")
            print("Checklist:")
            print("1. Did you grant 'pages_show_list' and 'instagram_basic' permissions?")
            print("2. Did you select at least one Page when generating the token?")
            print("3. Is your Instagram account a Business account and linked to a Facebook Page?")
            return

        print(f"\n✅ Found {len(pages)} Page(s):\n")
        
        found_any = False
        for page in pages:
            page_name = page.get("name")
            page_id = page.get("id")
            insta_acc = page.get("instagram_business_account")
            
            print(f"Page: {page_name} (ID: {page_id})")
            
            if insta_acc:
                insta_id = insta_acc.get("id")
                print(f"  └─ ✨ Linked Instagram Business Account ID: {insta_id}")
                print(f"     👉 Use this for INSTAGRAM_USER_ID in your .env file.")
                found_any = True
            else:
                print("  └─ ❌ No linked Instagram Business Account found for this Page.")
        
        if not found_any:
            print("\n⚠️ No linked Instagram Business Accounts were found across any of your Pages.")
            print("Ensure your Instagram account is set to 'Business' and is linked to the correct Facebook Page.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    find_instagram_ids()

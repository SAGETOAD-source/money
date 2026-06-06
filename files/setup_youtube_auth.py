"""
setup_youtube_auth.py
Run ONCE before starting the bot.
Opens your browser to authorise YouTube upload access.
After that the bot handles token refresh automatically.

Usage:  python setup_youtube_auth.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import config

from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    if not os.path.exists(config.YOUTUBE_CLIENT_SECRET_FILE):
        print(f"""
ERROR: {config.YOUTUBE_CLIENT_SECRET_FILE} not found.

Steps to get it:
  1. Go to https://console.cloud.google.com/
  2. Create a project → Enable 'YouTube Data API v3'
  3. Create OAuth2 credentials (Desktop app)
  4. Download JSON → rename it '{config.YOUTUBE_CLIENT_SECRET_FILE}'
  5. Put it in this folder, then re-run this script
""")
        sys.exit(1)

    flow  = InstalledAppFlow.from_client_secrets_file(
                config.YOUTUBE_CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(config.YOUTUBE_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"""
✅ YouTube authorisation complete!
   Token saved to: {config.YOUTUBE_TOKEN_FILE}
   You can now run:  python main.py
""")

if __name__ == "__main__":
    main()

"""Test sp_dc cookie approach for editorial playlists.

Run this after setting POKODLER_SPOTIFY_SP_DC in .env to verify it works.
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SP_DC = os.getenv("POKODLER_SPOTIFY_SP_DC", "")
PLAYLIST_ID = "37i9dQZF1DZ06evO3PVKpO"
API_BASE = "https://api.spotify.com/v1"

if not SP_DC:
    print("ERROR: POKODLER_SPOTIFY_SP_DC not set in .env")
    print("\nHow to get your sp_dc cookie:")
    print("  1. Open https://open.spotify.com in your browser (must be logged in)")
    print("  2. Open DevTools → Application (Chrome) or Storage (Firefox)")
    print("  3. Cookies → https://open.spotify.com")
    print("  4. Find 'sp_dc' and copy its value")
    print("  5. Add to .env: POKODLER_SPOTIFY_SP_DC=<value>")
    sys.exit(1)

print(f"sp_dc: {SP_DC[:20]}...")

# Fetch web player token
print("\n[1] Fetching web player token via sp_dc...")
r = requests.get(
    "https://open.spotify.com/get_access_token",
    params={"reason": "transport", "productType": "web_player"},
    headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"sp_dc={SP_DC}",
        "Referer": "https://open.spotify.com/",
    },
    timeout=10,
)
print(f"    Status: {r.status_code}")
if r.status_code != 200:
    print(f"    Body: {r.text[:300]}")
    print("\nsp_dc cookie may be expired. Get a fresh one from the browser.")
    sys.exit(1)

data = r.json()
token = data.get("accessToken")
is_anon = data.get("isAnonymous", True)
print(f"    isAnonymous: {is_anon}")
print(f"    Token: {token[:30]}..." if token else "    No token!")

if is_anon:
    print("\nWARNING: Token is anonymous — sp_dc may be invalid or not logged in")

if not token:
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

# Test editorial playlist
print(f"\n[2] Editorial playlist ({PLAYLIST_ID}):")
r = requests.get(f"{API_BASE}/playlists/{PLAYLIST_ID}", headers=headers, timeout=10)
print(f"    Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Name: {d.get('name')}")
    print(f"    Owner: {d.get('owner', {}).get('display_name')}")
    print(f"    Total tracks: {d.get('tracks', {}).get('total')}")
    print("\nsp_dc approach works! Add POKODLER_SPOTIFY_SP_DC to .env and restart the server.")
else:
    print(f"    Body: {r.text[:300]}")

# Test Today's Top Hits
print("\n[3] Today's Top Hits (37i9dQZF1DXcBWIGoYBM5M):")
r = requests.get(f"{API_BASE}/playlists/37i9dQZF1DXcBWIGoYBM5M", headers=headers, timeout=10)
print(f"    Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Name: {d.get('name')}, tracks: {d.get('tracks', {}).get('total')}")
else:
    print(f"    Body: {r.text[:200]}")

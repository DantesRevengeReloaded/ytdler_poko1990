import requests, re, json
def _get_tracks_from_embed(url: str):
    m_url = re.search(r'playlist/([A-Za-z0-9]+)', url)
    resource_id = m_url.group(1)
    embed_url = f"https://open.spotify.com/embed/playlist/{resource_id}"
    r = requests.get(embed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text)
    if not m:
        return None, None
    data = json.loads(m.group(1))
    entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
    title = entity.get("name") or entity.get("title") or "Spotify Playlist"
    track_list = entity.get("trackList", [])
    tracks = []
    for t in track_list:
        tracks.append({
            "title": t.get("title", "Unknown"),
            "artist": t.get("subtitle", "Unknown"),
            "album": None,
            "spotify_url": None
        })
    return tracks, title
print(_get_tracks_from_embed("https://open.spotify.com/playlist/37i9dQZF1DXe9VRwc7kLEx")[1])

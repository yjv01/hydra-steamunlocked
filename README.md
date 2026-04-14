# Hydra Launcher — SteamUnlocked Source

Auto-updating Hydra Launcher download source for [steamunlocked.net](https://steamunlocked.net).

The `steamunlocked.json` file is automatically refreshed every **12 hours** via GitHub Actions.

## Add to Hydra Launcher

1. Open **Hydra Launcher**
2. Go to **Settings → Download Sources → Add Source**
3. Paste this URL:

```
https://raw.githubusercontent.com/yjv01/hydra-steamunlocked/main/steamunlocked.json
```

## JSON Format

The file follows the official Hydra Launcher source schema:

```json
{
  "name": "SteamUnlocked",
  "downloads": [
    {
      "title": "Game Title",
      "uris": ["https://..."],
      "fileSize": "4.2 GB",
      "uploadDate": "2024-06-01T00:00:00.000Z"
    }
  ]
}
```

## How It Works

A Python script (`scrape.py`) runs on GitHub Actions every 12 hours:
1. Fetches the full game list from `steamunlocked.net/all-games/`
2. Visits each game page to extract title, file size, upload date, and download URI
3. Outputs `steamunlocked.json` in Hydra Launcher format
4. Commits and pushes the updated file to this repository

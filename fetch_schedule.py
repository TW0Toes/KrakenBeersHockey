import json
import datetime
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

CLIENT_ID = "2296"
LEAGUE_ID = "5717"

# Winter 2026-2027 season months
SEASON_MONTHS = [
    (9, 2026),
    (10, 2026),
    (11, 2026),
    (12, 2026),
    (1, 2027),
    (2, 2027),
    (3, 2027),
    (4, 2027),
]

def clean_team_name(name):
    if not name:
        return ""
    # Remove division tags like KRA F, REA F, VIP F, etc.
    cleaned = re.sub(r'\s+[A-Z]{2,4}\s+F\b', '', name.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'\b[A-Z]{2,5}\s+[A-Z0-9]\b$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', cleaned).strip()

def extract_hna_date(text):
    patterns = [
        r'\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\s+[A-Za-z]{3,4}\.?\s+\d{1,2}(?:,?\s*\d{4})?\b',
        r'\b[A-Za-z]{3,4}\.?\s+\d{1,2},?\s+\d{4}\b'
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""

def scrape_schedule():
    print("Fetching 2026-2027 season schedule...")
    schedule_data = {"last_game": None, "upcoming_games": []}
    seen_games = set()

    for month, year in SEASON_MONTHS:
        url = f"https://www.hna.com/leagues/schedules.cfm?clientID={CLIENT_ID}&leagueID={LEAGUE_ID}&schedType=main&printPage=0&monthID={month}&yearID={year}"

        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.find_all('tr')
            current_date = ""

            for row in rows:
                cols = [re.sub(r'\s+', ' ', td.text).strip() for td in row.find_all(['td', 'th'])]
                if not cols:
                    continue

                raw_row_text = ' '.join(cols).strip()
                row_upper = raw_row_text.upper()

                # Capture date header blocks
                found_date = extract_hna_date(raw_row_text)
                if found_date:
                    current_date = found_date
                    continue

                # Ignore completed games with scores or final tags
                if any(kw in row_upper for kw in ['FINAL', 'RESULT', 'GAME #', 'RECORD:']):
                    continue

                if re.search(r'\b\d+\s*-\s*\d+\b', raw_row_text):
                    continue

                # Filter strictly for Kraken Beers games
                if "KRAKEN" in row_upper:
                    time_match = re.search(r'\b\d{1,2}:\d{2}\s*(?:AM|PM)\b', row_upper)
                    if not time_match:
                        continue

                    time_str = time_match.group(0)

                    # Extract location (usually contains 'Rink', 'WSA', 'Playland', etc.)
                    location = "Local Rink"
                    for col in reversed(cols):
                        if any(loc_kw in col.upper() for loc_kw in ['RINK', 'WSA', 'PLAYLAND', 'ICE', 'MAP']):
                            location = col.replace('MAP', '').strip()
                            break

                    # Identify matchup components
                    teams = [c for c in cols if "KRAKEN" in c.upper() or " F" in c]
                    visitor_raw, home_raw = "Kraken Beers", "Opponent"

                    if len(cols) >= 4:
                        visitor_raw = cols[2]
                        home_raw = cols[3]

                    home_clean = clean_team_name(home_raw)
                    away_clean = clean_team_name(visitor_raw)

                    # Ensure team names don't collapse to empty strings
                    if "KRAKEN" in visitor_raw.upper():
                        away_clean = "Kraken Beers"
                    if "KRAKEN" in home_raw.upper():
                        home_clean = "Kraken Beers"

                    game_obj = {
                        "date": current_date or f"{month}/2026",
                        "time": time_str,
                        "home_team": home_clean,
                        "away_team": away_clean,
                        "location": location or "Local Rink"
                    }

                    game_signature = f"{game_obj['date']}_{game_obj['time']}_{game_obj['home_team']}_{game_obj['away_team']}"
                    if game_signature not in seen_games:
                        seen_games.add(game_signature)
                        schedule_data["upcoming_games"].append(game_obj)

        except Exception as e:
            print(f"Skipping {month}/{year}: {e}")

    with open('schedule.json', 'w') as f:
        json.dump(schedule_data, f, indent=2)

    print(f"Schedule complete! Saved {len(schedule_data['upcoming_games'])} upcoming games.")

if __name__ == '__main__':
    scrape_schedule()

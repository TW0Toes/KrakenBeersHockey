import json
import re
from bs4 import BeautifulSoup
import requests

SCHEDULE_URL = 'https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=25148&teamID=679527&printPage=0'
STANDINGS_URL = 'https://www.hna.com/leagues/standings.cfm?leagueID=5717&clientID=2296'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}

def clean_team_name(name):
    """Generically strips team code suffixes (e.g. 'Kraken Beers KRA F' -> 'Kraken Beers')."""
    if not name:
        return ""
    cleaned = re.sub(r'\b[A-Z]{2,5}\s+[A-Z0-9]\b$', '', name.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'\b[A-Z]{3,5}\b$', '', cleaned.strip(), flags=re.IGNORECASE)
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
    print("Fetching schedule from HNA...")
    res = requests.get(SCHEDULE_URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    upcoming_games = []
    rows = soup.find_all('tr')
    current_date = ""

    for row in rows:
        cols = [re.sub(r'\s+', ' ', td.text).strip() for td in row.find_all(['td', 'th'])]
        if not cols:
            continue

        raw_row_text = ' '.join(cols).strip()
        row_upper = raw_row_text.upper()

        found_date = extract_hna_date(raw_row_text)
        if found_date:
            current_date = found_date

        if any(kw in row_upper for kw in ['RESULT', 'GAME #', 'VISITOR', 'FINAL', 'RECORD:', 'LAST:']):
            continue

        time_str = ""
        for cell in cols:
            if ('PM' in cell.upper() or 'AM' in cell.upper()) and len(cell) < 15:
                time_str = cell
                break

        if time_str:
            raw_team_1 = cols[2] if len(cols) > 2 else ""
            raw_team_2 = cols[4] if len(cols) > 4 else (cols[3] if len(cols) > 3 else "")

            team_1_clean = clean_team_name(raw_team_1)
            team_2_clean = clean_team_name(raw_team_2)

            location = "Playland"
            for c in cols:
                if any(rink in c.lower() for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']):
                    location = c
                    break

            upcoming_games.append({
                "date": current_date,
                "time": time_str,
                "home_team": team_2_clean,
                "away_team": team_1_clean,
                "location": location
            })

    with open('schedule.json', 'w') as f:
        json.dump({"upcoming_games": upcoming_games}, f, indent=2)

def scrape_standings():
    print("Fetching standings from HNA...")
    res = requests.get(STANDINGS_URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    standings_data = []
    in_f_division = False

    rows = soup.find_all('tr')
    for row in rows:
        text = row.text.strip().upper()
        
        # Identify Division Headers
        if "DIVISION" in text:
            if "F DIVISION" in text or "DIVISION F" in text:
                in_f_division = True
            else:
                in_f_division = False
            continue

        if not in_f_division:
            continue

        cols = [re.sub(r'\s+', ' ', td.text).strip() for td in row.find_all(['td', 'th'])]
        
        # Skip header rows
        if not cols or 'TEAM' in cols[0].upper() or 'GP' in cols:
            continue

        # Expect standard standings columns: Team, GP, W, L, T, PTS, etc.
        if len(cols) >= 6:
            raw_team = cols[0]
            team_clean = clean_team_name(raw_team)

            # Defensive numerical checks
            try:
                gp = int(cols[1])
                w = int(cols[2])
                l = int(cols[3])
                t = int(cols[4])
                pts = int(cols[5])

                standings_data.append({
                    "team": team_clean,
                    "gp": gp,
                    "w": w,
                    "l": l,
                    "t": t,
                    "pts": pts
                })
            except ValueError:
                continue

    # Sort descending by Points
    standings_data.sort(key=lambda x: x['pts'], reverse=True)

    with open('standings.json', 'w') as f:
        json.dump({"standings": standings_data}, f, indent=2)

if __name__ == '__main__':
    scrape_schedule()
    scrape_standings()
    print("Scraping complete!")

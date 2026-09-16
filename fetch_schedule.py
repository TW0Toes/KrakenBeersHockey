import json
import re
from bs4 import BeautifulSoup
import requests

URL = 'https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=25148&teamID=679527&printPage=0'

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

def run_scraper():
    print("Fetching schedule from HNA...")
    res = requests.get(URL, headers=headers)
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

        # Skip main table header rows
        if any(kw in row_upper for kw in ['RESULT', 'GAME #', 'VISITOR', 'FINAL']):
            continue

        # Look for explicit date strings across any cell in this row
        for cell in cols:
            # Matches 'Sun Sep 13', 'Sun, Sep 13', '09/13/2026', or '9/13/26'
            date_match = re.search(
                r'\b((?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\s+[A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b', 
                cell, 
                re.IGNORECASE
            )
            if date_match and not any(time_kw in cell.upper() for time_kw in ['PM', 'AM']):
                current_date = date_match.group(0).strip()
                break

        # Identify time cell (AM/PM)
        time_str = ""
        for cell in cols:
            if 'PM' in cell.upper() or 'AM' in cell.upper():
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

    output = {
        "upcoming_games": upcoming_games
    }

    with open('schedule.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Done! Saved {len(upcoming_games)} game(s).")

if __name__ == '__main__':
    run_scraper()

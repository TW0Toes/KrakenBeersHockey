
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.hna.com/leagues/schedules.cfm"

PARAMS = {
    "clientID": "2296",
    "leagueID": "5717",
    "schedType": "main",
    "printPage": "0",
    "selectedTeamID": "683136",  # Kraken Beers
    "monthID": "9,2026",          # September 2026
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.hna.com/",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
}


TEAM_NAME = "Kraken Beers"
TEAM_ID = "683136"


# ============================================================
# HTTP
# ============================================================

def fetch_page():
    """Download the HNA schedule page."""

    response = requests.get(
        BASE_URL,
        params=PARAMS,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# HELPERS
# ============================================================

def clean_text(element):
    """Return normalized text from a BeautifulSoup element."""

    if element is None:
        return ""

    return " ".join(element.stripped_strings)


def normalize_team_name(text):
    """
    Remove the division abbreviation that appears in the table.

    Example:
        'Kraken Beers KRA F' -> 'Kraken Beers'
        'Reapers REA F'      -> 'Reapers'
    """

    text = clean_text(text)

    # The desktop version has the team name, abbreviation and division.
    # Example: Kraken Beers KRA F
    #
    # We primarily use the <a> text below, so this is a fallback.
    parts = text.split()

    if len(parts) >= 3:
        # Last item is normally division (F, E1, E2, etc.)
        # Second-to-last is normally abbreviation.
        if re.fullmatch(r"[A-Z0-9]{1,5}", parts[-1]):
            parts = parts[:-1]

        if len(parts) >= 2 and re.fullmatch(r"[A-Z0-9]{2,5}", parts[-1]):
            parts = parts[:-1]

    return " ".join(parts)


def get_team_name(cell):
    """
    Extract the full team name from a game table cell.

    HNA provides the full name in:
        <span class="d-sm-inline d-none">
            <a>Kraken Beers</a>
        </span>
    """

    if cell is None:
        return ""

    # First choice: the desktop/full team name.
    desktop = cell.select_one("span.d-sm-inline.d-none a")

    if desktop:
        return clean_text(desktop)

    # Second choice: tooltip title.
    tooltip = cell.select_one("[title]")

    if tooltip:
        title = tooltip.get("title")

        if title:
            return " ".join(title.split())

    # Last resort.
    return normalize_team_name(cell)


def get_team_id(cell):
    """Extract the team ID from the team's stats link."""

    if cell is None:
        return None

    link = cell.select_one('a[href*="stats_1team.cfm"]')

    if not link:
        return None

    href = link.get("href", "")

    match = re.search(r"[?&]teamID=(\d+)", href)

    if match:
        return match.group(1)

    return None


def parse_date_heading(text):
    """
    Convert HNA date headings such as:

        Tue Sep 22, 2026

    into:

        09/22/2026
    """

    text = " ".join(text.split())

    match = re.search(
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2}),\s+(\d{4})",
        text,
    )

    if not match:
        return None

    date_text = match.group(0)

    try:
        date_obj = datetime.strptime(date_text, "%a %b %d, %Y")
        return date_obj.strftime("%m/%d/%Y")
    except ValueError:
        return None


def find_date_for_table(table):
    """
    Find the date heading associated with a schedule table.

    The HNA page places a date heading in an element before
    the table rather than putting the date inside each <tr>.
    """

    # Walk backward through preceding elements.

    for element in table.find_all_previous(["h1", "h2", "h3", "h4", "h5", "div"], limit=30):
        text = clean_text(element)

        if not text:
            continue

        parsed = parse_date_heading(text)

        if parsed:
            return parsed

    return None


def get_game_rows(table):
    """Return actual game rows, ignoring the table header."""

    rows = []

    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)

        if len(cells) < 7:
            continue

        rows.append(row)

    return rows


# ============================================================
# GAME PARSING
# ============================================================

def parse_game(row, date):
    """Convert one HNA <tr> into a game dictionary."""

    cells = row.find_all("td", recursive=False)

    if len(cells) < 7:
        return None

    # HNA schedule columns:
    #
    # Upcoming:
    #   0 = Time
    #   1 = Game #
    #   2 = Away
    #   3 = Away score
    #   4 = Home
    #   5 = Home score
    #   6 = Location
    #
    # Completed:
    #   0 = Result
    #   1 = Game #
    #   2 = Away
    #   3 = Away score
    #   4 = Home
    #   5 = Home score
    #   6 = Location

    first_cell = clean_text(cells[0])
    game_number = clean_text(cells[1])

    away_cell = cells[2]
    away = get_team_name(away_cell)

    home_cell = cells[4]
    home = get_team_name(home_cell)

    location = clean_text(cells[6])

    away_score = clean_text(cells[3])
    home_score = clean_text(cells[5])

    # Determine whether this is an upcoming game or completed game.
    if re.fullmatch(r"\d{1,2}:\d{2}\s+[AP]M", first_cell, re.IGNORECASE):
        time = first_cell
        status = "scheduled"
    else:
        time = None
        status = first_cell.lower() if first_cell else "scheduled"

    # Determine home/away relative to Kraken Beers.
    if get_team_id(away_cell) == TEAM_ID:
        opponent = home
        home_away = "away"

    elif get_team_id(home_cell) == TEAM_ID:
        opponent = away
        home_away = "home"

    else:
        return None

    game = {
        "date": date,
        "time": time,
        "away": away,
        "home": home,
        "opponent": opponent,
        "home_away": home_away,
        "location": location,
        "game_number": game_number,
        "status": status,
    }

    # Add scores only when they actually exist.
    if away_score or home_score:
        game["away_score"] = away_score
        game["home_score"] = home_score

    return game


# ============================================================
# SCHEDULE
# ============================================================

def scrape_schedule(html):
    """Extract all Kraken Beers games from the page."""

    soup = BeautifulSoup(html, "html.parser")

    games = []

    # The schedule consists of multiple tables, one table per date.
    for table in soup.select("table.table.table-hover"):
        date = find_date_for_table(table)

        if not date:
            continue

        for row in get_game_rows(table):
            game = parse_game(row, date)

            if game:
                games.append(game)

    return games


# ============================================================
# NEXT GAME
# ============================================================

def find_next_game(games):
    """
    Find the first scheduled game.

    Completed games have status such as 'final'.
    Upcoming games have a time and status 'scheduled'.
    """

    scheduled = [
        game
        for game in games
        if game.get("status") == "scheduled"
    ]

    if not scheduled:
        return None

    def sort_key(game):
        date = datetime.strptime(game["date"], "%m/%d/%Y")

        time = datetime.strptime(
            game["time"],
            "%I:%M %p",
        )

        return datetime.combine(date.date(), time.time())

    scheduled.sort(key=sort_key)

    return scheduled[0]


# ============================================================
# OUTPUT
# ============================================================

def print_schedule(games):
    """Print a human-readable schedule."""

    print()
    print("=" * 70)
    print("KRAKEN BEERS SCHEDULE")
    print("=" * 70)

    if not games:
        print("No Kraken Beers games found.")
        return

    for game in games:
        print()

        print(
            f"{game['date']} | "
            f"{game['time'] or 'Final'}"
        )

        print(
            f"  {game['away']} "
            f"{game.get('away_score', '')}"
            f"  @  "
            f"{game['home']} "
            f"{game.get('home_score', '')}"
        )

        print(f"  Location: {game['location']}")
        print(f"  Game #:   {game['game_number']}")
        print(f"  Status:   {game['status']}")
        print(f"  Opponent: {game['opponent']}")
        print(f"  Home/Away: {game['home_away']}")


def print_next_game(games):
    """Print the next scheduled Kraken Beers game."""

    next_game = find_next_game(games)

    print()
    print("=" * 70)
    print("NEXT KRAKEN BEERS GAME")
    print("=" * 70)

    if not next_game:
        print("No upcoming Kraken Beers games found.")
        return

    print(
        f"{next_game['date']} at {next_game['time']}"
    )

    print(
        f"Kraken Beers {'@' if next_game['home_away'] == 'away' else 'vs'} "
        f"{next_game['opponent']}"
    )

    print(f"Location: {next_game['location']}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("KRAKEN BEERS HOCKEY SCHEDULE SCRAPER")
    print("=" * 70)

    try:
        html = fetch_page()

    except requests.RequestException as exc:
        print()
        print("ERROR: Could not download the HNA schedule.")
        print(exc)
        return

    print()
    print(f"Downloaded {len(html):,} bytes.")

    games = scrape_schedule(html)

    print()
    print(f"Found {len(games)} Kraken Beers game(s).")

    print_schedule(games)
    print_next_game(games)


if __name__ == "__main__":
    main()

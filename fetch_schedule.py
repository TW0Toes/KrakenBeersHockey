import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime


# ---------------------------------------------------------
# HNA CONFIGURATION
# ---------------------------------------------------------

BASE_URL = "https://www.hna.com/leagues/schedules.cfm"

CLIENT_ID = "2296"
LEAGUE_ID = "5717"
TEAM_ID = "683136"       # Kraken Beers

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    ),
    "Referer": "https://www.hna.com/",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
}


# ---------------------------------------------------------
# SESSION
# ---------------------------------------------------------

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------
# GET A PAGE FROM HNA
# ---------------------------------------------------------

def get_page(params):
    response = session.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ---------------------------------------------------------
# FIND MONTH OPTIONS
#
# HNA uses values such as:
#
#   9,2026
#   10,2026
#
# These are NOT the actual game dates.
# They are month selectors.
# ---------------------------------------------------------

def get_month_options(html):
    soup = BeautifulSoup(html, "html.parser")

    months = []

    for option in soup.find_all("option"):
        value = option.get("value", "").strip()

        if re.fullmatch(r"\d{1,2},\d{4}", value):
            if value not in months:
                months.append(value)

    return months


# ---------------------------------------------------------
# CLEAN TEAM NAME
# ---------------------------------------------------------

def clean_team_name(anchor):
    if not anchor:
        return ""

    # Get all visible text from the team link.
    text = anchor.get_text(" ", strip=True)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------------------------------------
# EXTRACT DATE FROM HNA HEADING
#
# Examples:
#
#   Tue Sep 22, 2026
#   Thu Sep 24, 2026
#   Fri Sep 25, 2026
# ---------------------------------------------------------

def parse_date_heading(text):
    if not text:
        return None

    text = re.sub(r"\s+", " ", text).strip()

    match = re.search(
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2}),\s*(\d{4})",
        text,
    )

    if not match:
        return None

    date_text = match.group(0)

    try:
        dt = datetime.strptime(date_text, "%a %b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


# ---------------------------------------------------------
# FIND THE DATE FOR A GAME TABLE
#
# HNA puts the date in an <h5> BEFORE the table.
#
# The game <tr> itself does not contain the date.
# ---------------------------------------------------------

def find_date_for_table(table):
    heading = table.find_previous("h5")

    if not heading:
        return None

    return parse_date_heading(
        heading.get_text(" ", strip=True)
    )


# ---------------------------------------------------------
# DETERMINE WHETHER A ROW IS A GAME
# ---------------------------------------------------------

def get_team_links(row):
    """
    Return team links from a schedule row.

    We specifically look for links containing teamID=
    so that things like navigation/team selectors are ignored.
    """

    links = []

    for anchor in row.find_all("a", href=True):
        href = anchor.get("href", "")

        if re.search(r"teamID=\d+", href, re.IGNORECASE):
            links.append(anchor)

    return links


# ---------------------------------------------------------
# PARSE ONE MONTH
# ---------------------------------------------------------

def parse_month(html):
    soup = BeautifulSoup(html, "html.parser")

    games = []

    for table in soup.find_all("table"):

        game_date = find_date_for_table(table)

        if not game_date:
            continue

        for row in table.find_all("tr"):

            team_links = get_team_links(row)

            # A real game row should have at least two teams.
            if len(team_links) < 2:
                continue

            away_anchor = team_links[0]
            home_anchor = team_links[1]

            away_team = clean_team_name(away_anchor)
            home_team = clean_team_name(home_anchor)

            if not away_team or not home_team:
                continue

            # Make sure this is actually a Kraken Beers game.
            hrefs = [
                a.get("href", "")
                for a in team_links
            ]

            kraken_found = any(
                re.search(
                    rf"teamID={TEAM_ID}\b",
                    href,
                    re.IGNORECASE,
                )
                for href in hrefs
            )

            if not kraken_found:
                continue

            cells = row.find_all("td")

            if len(cells) < 7:
                continue

            cell_text = [
                re.sub(
                    r"\s+",
                    " ",
                    cell.get_text(" ", strip=True)
                ).strip()
                for cell in cells
            ]

            # Typical HNA layout:
            #
            # 0 = time/result
            # 1 = game number
            # 2 = away team
            # 3 = away score
            # 4 = home team
            # 5 = home score
            # 6 = location
            #
            time_or_result = cell_text[0]
            location = cell_text[6]

            game = {
                "date": game_date,
                "time": "",
                "away_team": away_team,
                "home_team": home_team,
                "location": location,
            }

            # -------------------------------------------------
            # UPCOMING GAME
            #
            # HNA gives these rows a time such as:
            # "10:20 PM"
            # -------------------------------------------------

            if re.search(
                r"\d{1,2}:\d{2}\s*(AM|PM)",
                time_or_result,
                re.IGNORECASE,
            ):
                game["time"] = time_or_result

            # -------------------------------------------------
            # COMPLETED GAME
            #
            # Examples:
            #
            # Final
            # Final /OT
            # Final /SO
            # -------------------------------------------------

            else:
                game["time"] = ""

            games.append(game)

    return games


# ---------------------------------------------------------
# REMOVE DUPLICATES
# ---------------------------------------------------------

def deduplicate_games(games):
    seen = set()
    unique = []

    for game in games:
        key = (
            game["date"],
            game["time"],
            game["away_team"],
            game["home_team"],
            game["location"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(game)

    return unique


# ---------------------------------------------------------
# DETERMINE IF GAME IS COMPLETED
#
# HNA uses "Final" in the first cell for completed games.
#
# Because our simplified game object doesn't retain the
# original status, we determine this while reparsing the
# source row below.
# ---------------------------------------------------------

def parse_month_with_status(html):
    soup = BeautifulSoup(html, "html.parser")

    games = []

    for table in soup.find_all("table"):

        game_date = find_date_for_table(table)

        if not game_date:
            continue

        for row in table.find_all("tr"):

            team_links = get_team_links(row)

            if len(team_links) < 2:
                continue

            away_anchor = team_links[0]
            home_anchor = team_links[1]

            away_team = clean_team_name(away_anchor)
            home_team = clean_team_name(home_anchor)

            if not away_team or not home_team:
                continue

            hrefs = [
                a.get("href", "")
                for a in team_links
            ]

            kraken_found = any(
                re.search(
                    rf"teamID={TEAM_ID}\b",
                    href,
                    re.IGNORECASE,
                )
                for href in hrefs
            )

            if not kraken_found:
                continue

            cells = row.find_all("td")

            if len(cells) < 7:
                continue

            cell_text = [
                re.sub(
                    r"\s+",
                    " ",
                    cell.get_text(" ", strip=True)
                ).strip()
                for cell in cells
            ]

            status_or_time = cell_text[0]
            location = cell_text[6]

            # Determine whether HNA considers it final.
            is_final = bool(
                re.search(
                    r"\bFinal\b",
                    status_or_time,
                    re.IGNORECASE,
                )
            )

            # Upcoming games normally contain a time.
            time_match = re.search(
                r"\d{1,2}:\d{2}\s*(AM|PM)",
                status_or_time,
                re.IGNORECASE,
            )

            game_time = (
                time_match.group(0)
                if time_match
                else ""
            )

            game = {
                "date": game_date,
                "time": game_time,
                "away_team": away_team,
                "home_team": home_team,
                "location": location,
                "_completed": is_final,
            }

            games.append(game)

    return games


# ---------------------------------------------------------
# MAIN SCRAPER
# ---------------------------------------------------------

def fetch_schedule():

    # -----------------------------------------------------
    # First request.
    #
    # IMPORTANT:
    # This is your original HNA URL.
    #
    # We use it to discover the available month options.
    # -----------------------------------------------------

    base_params = {
        "clientID": CLIENT_ID,
        "leagueID": LEAGUE_ID,
        "schedType": "main",
        "printPage": "0",
    }

    initial_html = get_page(base_params)

    month_options = get_month_options(initial_html)

    if not month_options:
        raise RuntimeError(
            "Could not find HNA month options."
        )

    print("HNA month options found:")
    for month in month_options:
        print("  ", month)

    # -----------------------------------------------------
    # Fetch every available month for Kraken Beers.
    # -----------------------------------------------------

    all_games = []

    for month_id in month_options:

        print(f"Fetching HNA month: {month_id}")

        params = {
            "clientID": CLIENT_ID,
            "leagueID": LEAGUE_ID,
            "schedType": "main",
            "printPage": "0",
            "selectedTeamID": TEAM_ID,
            "monthID": month_id,
        }

        html = get_page(params)

        games = parse_month_with_status(html)

        print(
            f"  Found {len(games)} Kraken Beers games"
        )

        all_games.extend(games)

    # -----------------------------------------------------
    # Remove duplicates.
    # -----------------------------------------------------

    unique_games = deduplicate_games(all_games)

    # -----------------------------------------------------
    # Sort chronologically.
    # -----------------------------------------------------

    def sort_key(game):
        date_part = game["date"]

        time_part = game["time"]

        try:
            if time_part:
                dt = datetime.strptime(
                    f"{date_part} {time_part}",
                    "%Y-%m-%d %I:%M %p",
                )
                return dt
        except ValueError:
            pass

        try:
            return datetime.strptime(
                date_part,
                "%Y-%m-%d",
            )
        except ValueError:
            return datetime.max

    unique_games.sort(key=sort_key)

    # -----------------------------------------------------
    # Use today's date.
    #
    # For games on today's date, use time when available.
    # -----------------------------------------------------

    now = datetime.now()

    completed_games = []
    upcoming_games = []

    for game in unique_games:

        try:
            game_date = datetime.strptime(
                game["date"],
                "%Y-%m-%d",
            ).date()
        except ValueError:
            continue

        if game.get("_completed"):
            completed_games.append(game)
            continue

        # If HNA hasn't marked it Final, determine whether
        # its scheduled date/time is still in the future.
        if game_date > now.date():
            upcoming_games.append(game)
            continue

        if game_date < now.date():
            # A past game that HNA hasn't marked Final.
            # Keep it out of upcoming_games.
            continue

        # Game is today.
        if game["time"]:
            try:
                game_dt = datetime.strptime(
                    f"{game['date']} {game['time']}",
                    "%Y-%m-%d %I:%M %p",
                )

                if game_dt >= now:
                    upcoming_games.append(game)

            except ValueError:
                # If the time cannot be parsed, keep it as
                # upcoming rather than silently losing it.
                upcoming_games.append(game)

    # -----------------------------------------------------
    # Last completed game
    # -----------------------------------------------------

    last_game = None

    if completed_games:
        completed_games.sort(key=sort_key)
        last_game = completed_games[-1].copy()

    # -----------------------------------------------------
    # Clean internal "_completed" field.
    # -----------------------------------------------------

    for game in upcoming_games:
        game.pop("_completed", None)

    if last_game:
        last_game.pop("_completed", None)

    # -----------------------------------------------------
    # Final JSON structure.
    # -----------------------------------------------------

    return {
        "last_game": last_game,
        "upcoming_games": upcoming_games,
    }


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":

    try:
        result = fetch_schedule()

        print()
        print(json.dumps(
            result,
            indent=2,
        ))

    except Exception as e:
        print(
            json.dumps(
                {
                    "error": str(e)
                },
                indent=2,
            )
        )

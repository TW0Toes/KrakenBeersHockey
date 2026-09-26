
import requests
from bs4 import BeautifulSoup
import re


BASE_URL = "https://www.hna.com/leagues/schedules.cfm"

PARAMS = {
    "clientID": "2296",
    "leagueID": "5717",
    "schedType": "main",
    "printPage": "0",
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


def clean_text(text):
    """Collapse whitespace."""
    return " ".join(text.split())


def print_limited(text, limit=12000):
    """Print text without flooding GitHub Actions."""
    text = str(text)

    if len(text) > limit:
        print(text[:limit])
        print(f"\n... [truncated at {limit:,} characters]")
    else:
        print(text)


def main():

    print("=" * 70)
    print("KRAKEN BEERS HOCKEY SCHEDULE DEBUG")
    print("=" * 70)

    # ------------------------------------------------------------
    # 1. Fetch normal schedule page
    # ------------------------------------------------------------

    print("\nFetching HNA schedule...")

    response = requests.get(
        BASE_URL,
        params=PARAMS,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    print("Status:", response.status_code)
    print("URL:", response.url)
    print("Response length:", f"{len(response.text):,}")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")


    # ------------------------------------------------------------
    # 2. Basic page information
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("PAGE INFO")
    print("=" * 70)

    if soup.title:
        print("Title:", soup.title.get_text(" ", strip=True))

    # Selected season
    season_select = soup.find(
        "select",
        {"name": "sel_ChildSeason"}
    )

    if season_select:
        selected = season_select.find("option", selected=True)

        if selected:
            print(
                "Season:",
                selected.get_text(" ", strip=True)
            )

    # Selected month
    month_select = soup.find(
        "select",
        {"name": "monthID"}
    )

    if month_select:
        selected = month_select.find("option", selected=True)

        if selected:
            print(
                "Month:",
                selected.get_text(" ", strip=True),
                "| value:",
                selected.get("value")
            )


    # ------------------------------------------------------------
    # 3. Verify Kraken Beers exists in team selector
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("KRAKEN TEAM ID")
    print("=" * 70)

    team_option = soup.find(
        "option",
        string=lambda s: s and TEAM_NAME.lower() in s.lower()
    )

    if team_option:
        print("Team:", team_option.get_text(" ", strip=True))
        print("Team ID:", team_option.get("value"))
    else:
        print("Could not find Kraken Beers in team selector.")


    # ------------------------------------------------------------
    # 4. Find the ACTUAL schedule row containing Kraken Beers
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("KRAKEN BEERS GAME ROWS")
    print("=" * 70)

    kraken_rows = []

    for row_number, row in enumerate(soup.find_all("tr")):

        row_text = clean_text(
            row.get_text(" ", strip=True)
        )

        if TEAM_NAME.lower() in row_text.lower():
            kraken_rows.append((row_number, row))

    print(
        f"Found {len(kraken_rows)} table row(s) containing "
        f"'{TEAM_NAME}'."
    )


    if not kraken_rows:
        print("\nERROR: No Kraken Beers game rows found.")

        print("\nSearching raw page text for Kraken Beers...")

        if TEAM_NAME.lower() in response.text.lower():
            print(
                "Kraken Beers DOES exist in the HTML, "
                "but not inside a <tr>."
            )
        else:
            print("Kraken Beers was not found in the HTML at all.")

        return


    # ------------------------------------------------------------
    # 5. Print each actual Kraken game row
    # ------------------------------------------------------------

    for index, (row_number, row) in enumerate(kraken_rows, start=1):

        print("\n" + "-" * 70)
        print(f"KRAKEN GAME #{index}")
        print("TABLE ROW NUMBER:", row_number)
        print("-" * 70)

        cells = [
            clean_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(["td", "th"])
        ]

        print("CELLS:")
        print(cells)

        print("\nRAW ROW HTML:")
        print_limited(row.prettify(), 8000)


        # --------------------------------------------------------
        # 6. Inspect neighboring rows
        # --------------------------------------------------------

        print("\nNEIGHBORING ROWS:")

        previous_rows = []
        current = row

        for _ in range(3):
            current = current.find_previous("tr")

            if current:
                previous_rows.append(current)
            else:
                break

        previous_rows.reverse()

        for prev in previous_rows:
            text = clean_text(
                prev.get_text(" ", strip=True)
            )

            print("PREVIOUS:", repr(text))


        next_rows = []

        current = row

        for _ in range(3):
            current = current.find_next("tr")

            if current:
                next_rows.append(current)
            else:
                break

        for nxt in next_rows:
            text = clean_text(
                nxt.get_text(" ", strip=True)
            )

            print("NEXT:", repr(text))


        # --------------------------------------------------------
        # 7. Inspect the parent table
        # --------------------------------------------------------

        table = row.find_parent("table")

        if table:

            print("\nPARENT TABLE SUMMARY:")

            table_text = clean_text(
                table.get_text(" ", strip=True)
            )

            print_limited(table_text, 5000)

            print("\nPARENT TABLE HTML:")

            print_limited(
                table.prettify(),
                20000
            )


        # --------------------------------------------------------
        # 8. Inspect elements immediately preceding the table
        # --------------------------------------------------------

        if table:

            print("\nELEMENTS BEFORE TABLE:")

            element = table

            for level in range(1, 6):

                element = element.find_previous()

                if not element:
                    break

                text = clean_text(
                    element.get_text(" ", strip=True)
                )

                if text and len(text) < 300:

                    print(
                        f"LEVEL {level}: "
                        f"<{element.name}> "
                        f"{repr(text)}"
                    )


    # ------------------------------------------------------------
    # 9. Search page for date-like strings
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("DATE-LIKE TEXT FOUND IN PAGE")
    print("=" * 70)

    page_text = soup.get_text(" ", strip=True)

    date_patterns = [
        # 9/26/2026
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",

        # 09-26-2026
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",

        # September 26, 2026
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+"
        r"\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",

        # Sat September 26
        r"\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)"
        r"\w*,?\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2}\b",
    ]

    dates_found = set()

    for pattern in date_patterns:

        matches = re.findall(
            pattern,
            page_text,
            flags=re.IGNORECASE
        )

        for match in matches:
            dates_found.add(match)

    if dates_found:

        for date in sorted(dates_found):
            print(date)

    else:
        print(
            "No conventional date strings found "
            "in visible page text."
        )


    # ------------------------------------------------------------
    # 10. Look for likely date headings
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("POSSIBLE DATE HEADINGS")
    print("=" * 70)

    heading_tags = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    found_heading = False

    for heading in heading_tags:

        text = clean_text(
            heading.get_text(" ", strip=True)
        )

        if text:
            print(
                f"<{heading.name}> {text}"
            )

            found_heading = True

    if not found_heading:
        print("No heading tags with text found.")


    # ------------------------------------------------------------
    # 11. Try HNA's Kraken team filter
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("KRAKEN TEAM-FILTER TEST")
    print("=" * 70)

    filtered_params = {
        "clientID": "2296",
        "leagueID": "5717",
        "schedType": "main",
        "printPage": "0",
        "selectedTeamID": TEAM_ID,
        "monthID": "9,2026",
    }

    filtered_response = requests.get(
        BASE_URL,
        params=filtered_params,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    print(
        "Filtered status:",
        filtered_response.status_code
    )

    print(
        "Filtered URL:",
        filtered_response.url
    )

    print(
        "Filtered response length:",
        f"{len(filtered_response.text):,}"
    )

    filtered_response.raise_for_status()

    filtered_soup = BeautifulSoup(
        filtered_response.text,
        "html.parser"
    )

    filtered_rows = []

    for row_number, row in enumerate(
        filtered_soup.find_all("tr")
    ):

        text = clean_text(
            row.get_text(" ", strip=True)
        )

        if TEAM_NAME.lower() in text.lower():
            filtered_rows.append(
                (row_number, text)
            )

    print(
        f"Kraken rows returned by team filter: "
        f"{len(filtered_rows)}"
    )

    for row_number, text in filtered_rows:
        print(
            f"ROW {row_number}: {text}"
        )


    # ------------------------------------------------------------
    # DONE
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()


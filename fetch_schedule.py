import requests
from bs4 import BeautifulSoup


URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    "?clientID=2296"
    "&leagueID=5717"
    "&schedType=main"
    "&printPage=0"
)


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


def main():
    print("Downloading schedule...")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )

    print("STATUS:", response.status_code)
    print("URL:", response.url)
    print("LENGTH:", len(response.text))

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")


    # ============================================================
    # 1. BASIC PAGE INFORMATION
    # ============================================================

    print("\n" + "=" * 80)
    print("PAGE TITLE")
    print("=" * 80)

    if soup.title:
        print(soup.title.get_text(" ", strip=True))
    else:
        print("No <title> found.")


    # ============================================================
    # 2. LOOK FOR DATE-RELATED ELEMENTS
    # ============================================================

    print("\n" + "=" * 80)
    print("POSSIBLE DATE ELEMENTS")
    print("=" * 80)

    found_date_elements = False

    for element in soup.find_all(True):

        element_id = str(element.get("id", "")).lower()

        classes = element.get("class", [])
        class_text = " ".join(classes).lower()

        name = str(element.get("name", "")).lower()

        combined = f"{element_id} {class_text} {name}"

        if "date" in combined:
            found_date_elements = True

            print("\nTAG:", element.name)
            print("ID:", element.get("id"))
            print("CLASS:", element.get("class"))
            print("TEXT:", element.get_text(" ", strip=True))
            print("HTML:")
            print(element.prettify()[:5000])

    if not found_date_elements:
        print("No elements with 'date' in id/class/name were found.")


    # ============================================================
    # 3. LOOK FOR DATE-RELATED ATTRIBUTES
    # ============================================================

    print("\n" + "=" * 80)
    print("POSSIBLE DATE ATTRIBUTES")
    print("=" * 80)

    found_date_attributes = False

    for element in soup.find_all(True):

        for attribute, value in element.attrs.items():

            attribute_lower = attribute.lower()

            if (
                "date" in attribute_lower
                or "date" in str(value).lower()
            ):
                found_date_attributes = True

                print("\nTAG:", element.name)
                print("ATTRIBUTE:", attribute)
                print("VALUE:", value)
                print("TEXT:", element.get_text(" ", strip=True)[:500])

    if not found_date_attributes:
        print("No obvious date attributes found.")


    # ============================================================
    # 4. FIND THE CHIEFS GAME
    # ============================================================

    print("\n" + "=" * 80)
    print("HTML AROUND CHIEFS GAME")
    print("=" * 80)

    chiefs_found = False

    for text_node in soup.find_all(
        string=lambda s: s and "Chiefs" in s
    ):
        chiefs_found = True

        print("\nFOUND TEXT:")
        print(repr(text_node.strip()))

        element = text_node.parent

        print("\nPARENT ELEMENT:")
        print(element.prettify())

        # Print a few parent levels upward
        parent = element

        for level in range(1, 5):
            parent = parent.parent

            if parent is None:
                break

            print(
                f"\n--- PARENT LEVEL {level} ---"
            )

            print(parent.prettify()[:10000])

    if not chiefs_found:
        print("Could not find 'Chiefs' in the page.")


    # ============================================================
    # 5. TABLE DEBUG
    # ============================================================

    print("\n" + "=" * 80)
    print("ROW DEBUG")
    print("=" * 80)

    rows = soup.find_all("tr")

    for i, row in enumerate(rows):

        cols = [
            td.get_text(" ", strip=True)
            for td in row.find_all(["td", "th"])
        ]

        if cols:
            print(f"ROW {i}: {cols}")


    # ============================================================
    # 6. PRINT COMPLETE TABLE HTML FOR SCHEDULE TABLES
    # ============================================================

    print("\n" + "=" * 80)
    print("SCHEDULE TABLE HTML")
    print("=" * 80)

    tables_found = 0

    for table_index, table in enumerate(soup.find_all("table")):

        table_text = table.get_text(" ", strip=True)

        # Only show tables that appear to contain schedule information
        schedule_words = [
            "Chiefs",
            "Hurricanes",
            "HNA",
            "Away",
            "Home",
            "Location",
        ]

        if any(word in table_text for word in schedule_words):

            tables_found += 1

            print(
                f"\n--- TABLE {table_index} ---"
            )

            print(table.prettify()[:30000])

    if tables_found == 0:
        print("No obvious schedule table found.")


    # ============================================================
    # 7. HEADINGS / DIVS / SPANS THAT MAY CONTAIN DATES
    # ============================================================

    print("\n" + "=" * 80)
    print("HEADINGS / DIVS / SPANS")
    print("=" * 80)

    interesting_tags = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "div", "span"]
    )

    for element in interesting_tags:

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        # Print relatively short elements that look potentially useful.
        if (
            len(text) < 150
            and any(
                word in text.lower()
                for word in [
                    "2024",
                    "2025",
                    "2026",
                    "2027",
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                    "sunday",
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                ]
            )
        ):
            print(
                f"\nTAG: {element.name}"
            )
            print(
                f"ID: {element.get('id')}"
            )
            print(
                f"CLASS: {element.get('class')}"
            )
            print(
                f"TEXT: {text}"
            )


    # ============================================================
    # 8. SEARCH RAW HTML FOR COMMON DATE FORMATS
    # ============================================================

    print("\n" + "=" * 80)
    print("RAW HTML DATE SEARCH")
    print("=" * 80)

    raw_html = response.text

    date_keywords = [
        "2024",
        "2025",
        "2026",
        "2027",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    for keyword in date_keywords:

        position = raw_html.lower().find(keyword.lower())

        if position != -1:

            print(
                f"\nFOUND '{keyword}' at character {position}"
            )

            start = max(0, position - 500)
            end = min(
                len(raw_html),
                position + 1000
            )

            print(
                raw_html[start:end]
            )


    # ============================================================
    # 9. PAGE TEXT
    # ============================================================

    print("\n" + "=" * 80)
    print("PAGE TEXT")
    print("=" * 80)

    print(
        soup.get_text("\n", strip=True)
    )

    print("\n" + "=" * 80)
    print("END DEBUG")
    print("=" * 80)


if __name__ == "__main__":
    main()

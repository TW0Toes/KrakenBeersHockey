```python
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
    print("Fetching HNA schedule...")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    print(f"Status: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Response length: {len(response.text):,} characters")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")


    # ------------------------------------------------------------
    # 1. Basic page information
    # ------------------------------------------------------------

    print("\n=== PAGE INFO ===")

    if soup.title:
        print("Title:", soup.title.get_text(" ", strip=True))
    else:
        print("Title: <none>")


    # ------------------------------------------------------------
    # 2. Look for obvious date elements
    # ------------------------------------------------------------

    print("\n=== DATE-RELATED ELEMENTS ===")

    date_elements = []

    for element in soup.find_all(True):
        element_id = str(element.get("id", "")).lower()

        classes = element.get("class", [])
        class_text = " ".join(classes).lower()

        name = str(element.get("name", "")).lower()

        if (
            "date" in element_id
            or "date" in class_text
            or "date" in name
        ):
            text = element.get_text(" ", strip=True)

            # Ignore huge containers.
            if text and len(text) < 500:
                date_elements.append(element)

    if date_elements:
        for element in date_elements[:20]:
            print(
                f"TAG={element.name} "
                f"ID={element.get('id')} "
                f"CLASS={element.get('class')}"
            )
            print("TEXT:", element.get_text(" ", strip=True))
    else:
        print("No obvious date elements found.")


    # ------------------------------------------------------------
    # 3. Look for date-related attributes
    # ------------------------------------------------------------

    print("\n=== DATE-RELATED ATTRIBUTES ===")

    attribute_count = 0

    for element in soup.find_all(True):

        for attribute, value in element.attrs.items():

            if "date" not in attribute.lower():
                continue

            print(
                f"TAG={element.name} "
                f"ATTRIBUTE={attribute} "
                f"VALUE={value}"
            )

            attribute_count += 1

            if attribute_count >= 20:
                break

        if attribute_count >= 20:
            break

    if attribute_count == 0:
        print("No date-related attributes found.")


    # ------------------------------------------------------------
    # 4. Find the Chiefs game and show its HTML hierarchy
    # ------------------------------------------------------------

    print("\n=== CHIEFS GAME HTML ===")

    chiefs_node = None

    for text_node in soup.find_all(
        string=lambda s: s and "Chiefs" in s
    ):
        chiefs_node = text_node.parent
        break

    if chiefs_node is None:
        print("Could not find 'Chiefs' on the page.")

    else:
        print("Found:", chiefs_node.get_text(" ", strip=True))

        current = chiefs_node

        for level in range(1, 4):

            current = current.parent

            if current is None:
                break

            print(f"\n--- PARENT LEVEL {level} ---")

            # Limit output so GitHub Actions doesn't explode.
            html = current.prettify()

            if len(html) > 8000:
                html = html[:8000] + "\n... [truncated]"

            print(html)


    # ------------------------------------------------------------
    # 5. Show the schedule rows in a compact format
    # ------------------------------------------------------------

    print("\n=== SCHEDULE ROWS ===")

    rows = soup.find_all("tr")

    schedule_row_count = 0

    for i, row in enumerate(rows):

        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["td", "th"])
        ]

        if not cells:
            continue

        # Only show rows that look like schedule data.
        schedule_words = [
            "Chiefs",
            "Hurricanes",
            "Kraken",
            "Rye",
            "Wolves",
            "Mavericks",
            "Invaders",
            "Growlers",
        ]

        if any(
            word.lower() in " ".join(cells).lower()
            for word in schedule_words
        ):
            print(f"ROW {i}: {cells}")
            schedule_row_count += 1

    print(f"\nSchedule rows found: {schedule_row_count}")


    # ------------------------------------------------------------
    # 6. Search raw HTML for years/months
    # ------------------------------------------------------------

    print("\n=== DATE SEARCH IN RAW HTML ===")

    raw_html = response.text

    date_terms = [
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

    found_terms = set()

    for term in date_terms:

        position = raw_html.lower().find(term.lower())

        if position == -1:
            continue

        # Avoid printing the same area repeatedly.
        context_start = max(0, position - 250)
        context_end = min(
            len(raw_html),
            position + 500
        )

        context = raw_html[context_start:context_end]

        # Strip excessive whitespace.
        context = " ".join(context.split())

        print(f"\nFound '{term}':")
        print(context[:750])

        found_terms.add(term)

        # We only need a few examples.
        if len(found_terms) >= 8:
            break


    # ------------------------------------------------------------
    # 7. Important: check for JavaScript date data
    # ------------------------------------------------------------

    print("\n=== POSSIBLE JAVASCRIPT DATE DATA ===")

    script_text = "\n".join(
        script.get_text(" ", strip=True)
        for script in soup.find_all("script")
    )

    javascript_terms = [
        "schedule",
        "gameDate",
        "game_date",
        "date",
        "startDate",
        "start_date",
    ]

    found_js = False

    for term in javascript_terms:

        position = script_text.lower().find(term.lower())

        if position == -1:
            continue

        start = max(0, position - 300)
        end = min(
            len(script_text),
            position + 700
        )

        print(f"\nFound JavaScript term '{term}':")
        print(script_text[start:end])

        found_js = True

    if not found_js:
        print("No obvious JavaScript date data found.")


    # ------------------------------------------------------------
    # DONE
    # ------------------------------------------------------------

    print("\n=== DEBUG COMPLETE ===")
    print("The next step is to identify how HNA stores the schedule date.")


if __name__ == "__main__":
    main()
```

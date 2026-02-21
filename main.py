import asyncio
from playwright.async_api import async_playwright, Page
import os


async def fetch_page(browser):
    TARGET_URL = "https://www.ana.co.jp/en/us/"

    page = await browser.new_page()
    await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)

    return page


async def click_flight_awards_tab(page):
    """Clicks the 'Flight Awards' tab."""
    await page.get_by_role("tab", name="Flight Awards").click()
    await _write_page_to_file(page, "0_flight_awards.html")


async def click_award_reservation(page):
    """Clicks the 'Award Reservation' link.
    Note: It navigates the current tab, it doesn't open a new one."""
    # Instead of clicking and hoping a new tab opens (which times out),
    # we directly extract the href and navigate to it in the current tab.
    link_loc = page.locator(
        "a[data-scclick-element='reserve-award_txt_flightAwardReservations']"
    )
    href = await link_loc.get_attribute("href")

    print(f"Directly navigating to: {href}")
    # Wait until commit to bypass potential hangs on domcontentloaded for this ANA page
    await page.goto(href, wait_until="commit", timeout=60000)

    # Explicitly wait for the login form to be rendered
    await page.wait_for_selector("#accountNumber", state="visible", timeout=60000)

    new_page = page
    await _write_page_to_file(new_page, "1_award_reservation.html")
    return new_page


async def login(page: Page) -> Page:
    """Fills in fake credentials and clicks the login button on the new tab."""
    # Take a screenshot before filling so we can add it to the walkthrough
    await page.screenshot(path=os.path.join(os.getcwd(), "out", "login_page.png"))

    await page.locator("#accountNumber").fill("1234567890")
    await page.locator("#password").fill("FakePassword123!")

    await page.locator("#amcMemberLogin").click()

    # Try to wait for the page load after login, but catch timeout since fake credentials will just show an error message
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"Wait after login exception or timeout: {e}")

    await _write_page_to_file(page, "2_login_attempt.html")
    return page


async def main():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)

        page = await fetch_page(browser)

        print("Navigating to Flight Awards tab...")
        await click_flight_awards_tab(page)

        print("Selecting Award Reservation...")
        page = await click_award_reservation(page)

        if page:
            print("Logging in...")
            page = await login(page)

            print("\nScraping job completed successfully!")
            await _write_page_to_file(page, "99_final.html")

        await browser.close()


async def _write_page_to_file(page, filename):
    with open(os.path.join(os.getcwd(), "out", filename), "w", encoding="utf-8") as f:
        f.write(await page.content())


if __name__ == "__main__":
    asyncio.run(main())

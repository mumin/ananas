import asyncio
import os

import dotenv
from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Page

dotenv.load_dotenv()


async def fetch_page(browser):
    TARGET_URL = "https://www.ana.co.jp/en/us/"

    page = await browser.new_page()
    await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)

    return page


async def accept_cookies(page: Page):
    """Attempts to accept the generic Ensighten cookie banner if it exists."""
    print("Checking for cookie banner...")
    try:
        # The banner takes a moment to slide in. Wait up to 5 seconds.
        accept_btn = page.locator("#ensSave")
        await accept_btn.wait_for(state="visible", timeout=5000)
        # Using force=True because ANA's modal wrapper intercepts standard pointer events
        await accept_btn.click(force=True)
        print("Cookie banner accepted.")
    except Exception:
        print("No cookie banner found or already accepted.")


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
    print("Clicking Award Reservation link naturally...")
    async with page.context.expect_page() as new_page_info:
        await link_loc.click()

    new_page = await new_page_info.value
    await new_page.wait_for_load_state("domcontentloaded", timeout=60000)

    print(f"Old page URL: {page.url}")
    print(f"New page URL: {new_page.url}")

    # Explicitly wait for the login form to be rendered
    await new_page.wait_for_selector("#accountNumber", state="visible", timeout=60000)

    await _write_page_to_file(new_page, "1_award_reservation.html")
    return new_page


async def login(page: Page) -> Page:
    """Fills in fake credentials and clicks the login button on the new tab."""
    # Take a screenshot before filling so we can add it to the walkthrough
    await page.screenshot(path=os.path.join(os.getcwd(), "out", "login_page.png"))

    await page.locator("#accountNumber").press_sequentially(
        os.getenv("ANANAS_USERNAME"), delay=100
    )
    await page.locator("#password").press_sequentially(
        os.getenv("ANANAS_PASSWORD"), delay=100
    )

    await page.locator("#amcMemberLogin").click()

    # Try to wait for the page load after login, but catch timeout since fake credentials will just show an error message
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"Wait after login exception or timeout: {e}")

    await _write_page_to_file(page, "2_login_attempt.html")
    return page


async def main():
    print("Launching browser...")
    async with AsyncCamoufox(headless=False) as browser:
        page = await fetch_page(browser)

        await accept_cookies(page)

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
    with open(
        os.path.join(os.getcwd(), os.getenv("HTML_OUTPUT_DIR"), filename),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(await page.content())


if __name__ == "__main__":
    asyncio.run(main())

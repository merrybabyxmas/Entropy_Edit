from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:5173")

        # Wait for hydration
        time.sleep(3)

        # Check title
        assert "Entropy Edit" in page.title()

        # Check for key components
        # AssetBrowser text
        assert page.is_visible("text=Drop Video or Click")

        # Properties Panel
        assert page.is_visible("text=Sigma")
        assert page.is_visible("text=Height")

        # Timeline
        assert page.is_visible("text=0s")

        # Take screenshot
        page.screenshot(path="integration_full.png")
        print("Integration verification passed. Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    run()

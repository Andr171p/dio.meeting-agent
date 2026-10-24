import asyncio
import os

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()


async def main() -> None:
    port = os.getenv("BROWSER_PORT", "3000")
    path = os.environ["BROWSER_WS_PATH"]

    endpoint = f"ws://localhost:{port}{path}"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect(endpoint)

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )

        page = await context.new_page()

        await page.goto("https://playwright.dev/")

        await page.evaluate(
            """
            () => {
                window.audioContext = new AudioContext();

                window.oscillator =
                    window.audioContext.createOscillator();

                window.oscillator.frequency.value = 440;

                window.oscillator.connect(
                    window.audioContext.destination
                );

                window.oscillator.start();
            }
            """
        )

        await asyncio.sleep(10)

        await page.evaluate(
            """
            async () => {
                window.oscillator.stop();
                await window.audioContext.close();
            }
            """
        )

        print("Page title:", await page.title())

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

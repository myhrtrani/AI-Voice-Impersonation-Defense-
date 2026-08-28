import asyncio
from playwright.async_api import async_playwright
import os

GEN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "samples", "genuine_validation"))

async def run_session(page, filename, context_name, expected_end_alerts):
    print(f"\n--- Starting Session: {filename} (Context: {context_name}) ---")
    
    # Wait for setup screen
    await page.wait_for_selector("text=Step 1: Select Transaction Risk Context", timeout=5000)

    # 1. Click Context
    await page.get_by_text(context_name).click()

    # 2. Click 'Mode A: Upload Replay'
    await page.get_by_text("Mode A: Upload Replay").click()

    # 3. Upload file
    audio_file = os.path.join(GEN_DIR, filename)
    async with page.expect_file_chooser() as fc_info:
        await page.get_by_text("Upload Call Audio File").click()
    file_chooser = await fc_info.value
    await file_chooser.set_files(audio_file)

    print(f"File {filename} uploaded. Waiting for streaming to start...")
    
    # 4. Wait for dashboard to appear
    await page.wait_for_selector("text=Mode A Stream Replay", timeout=5000)
    
    # 5. Extract values continuously during the stream
    print("Streaming in progress, collecting telemetry from UI...")
    for _ in range(6): # poll for a few seconds
        try:
            raw_risk = await page.locator("text=/Raw Risk:/").inner_text(timeout=1000)
            print(f"UI Trace -> {raw_risk.strip()}")
        except Exception as e:
            pass
        await page.wait_for_timeout(1000)

    # 6. Wait for Post-Call summary
    print("Waiting for Post-Call Forensic Audit summary screen...")
    await page.wait_for_selector("text=Post-Call Forensic Audit", timeout=10000)
    
    peak_risk = await page.locator("text=/Peak Risk Index/").locator("xpath=..").locator("div.text-2xl").inner_text()
    avg_risk = await page.locator("text=/Average Risk Score/").locator("xpath=..").locator("div.text-2xl").inner_text()
    alert_count = await page.locator("text=/Security Alerts/").locator("xpath=..").locator("div.text-2xl").inner_text()
    chunks = await page.locator("text=/Analyzed Chunks/").inner_text()

    print(f"Summary UI - Peak Risk: {peak_risk}, Average Risk: {avg_risk}, Alerts: {alert_count}, Duration: {chunks}")
    
    assert str(expected_end_alerts) in alert_count, f"Expected {expected_end_alerts} alerts, got {alert_count}"

    # Click 'Start New Session'
    await page.get_by_text("Start New Session").click()
    print("Session reset.")


async def test_frontend():
    async with async_playwright() as p:
        print("Launching Chromium...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to http://localhost:5173/")
        await page.goto("http://localhost:5173/")
        await page.wait_for_load_state("networkidle")

        # Test A: Authentic Human
        await run_session(page, "librispeech_male_clean.wav", "General Call", expected_end_alerts=1)  # male clean triggers 1 warn in general? let's see
        
        # Test B: Voice Clone
        await run_session(page, "xtts_voice_clone_en.wav", "Fund Transfer", expected_end_alerts=1)
        
        # Test C: Authentic Human Female (should reset properly and have 0 alerts)
        await run_session(page, "librispeech_female_clean.wav", "General Call", expected_end_alerts=0)

        print("\nAll End-to-End browser UI tests passed! Closing browser.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_frontend())

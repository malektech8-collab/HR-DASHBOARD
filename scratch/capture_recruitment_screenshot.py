import asyncio
from playwright.async_api import async_playwright
import os
import shutil

async def main():
    os.makedirs("docs/qa/screenshots", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # High height viewport to capture the full page with charts and exception logs
        page = await browser.new_page(viewport={"width": 1280, "height": 4500})
        
        # Log page errors
        page.on("pageerror", lambda err: print(f"FRONTEND RUNTIME ERROR: {err}"))
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        
        try:
            # Navigate to home
            print("Navigating to dashboard...")
            await page.goto("http://localhost:5173/")
            await page.wait_for_selector("text=Executive Summary")
            await page.wait_for_timeout(1000)
            
            # Navigate to Recruitment Page
            print("Navigating to Recruitment Dashboard...")
            await page.locator("button:has-text('Recruitment & Hiring')").click(force=True)
            
            # Wait for page heading to load
            await page.wait_for_selector("text=Recruitment & Workforce Planning Dashboard", timeout=5000)
            print("Waiting for ECharts animations...")
            await page.wait_for_timeout(4000)
            
            # Capture Recruitment page
            rec_path = "docs/qa/screenshots/milestone_2f_recruitment_dashboard.png"
            await page.screenshot(path=rec_path)
            print(f"Captured Recruitment Dashboard at {rec_path}")
            
            # Let's copy it to the artifacts directory as well to use it in our walkthrough/QA reports
            artifact_dir = "C:/Users/hr/.gemini/antigravity/brain/722901c0-dbf0-4da7-b9dc-3271811691fa"
            if os.path.exists(artifact_dir):
                shutil.copy(rec_path, os.path.join(artifact_dir, "milestone_2f_recruitment_dashboard.png"))
                print("Copied screenshot to artifacts folder.")
            
        except Exception as e:
            print(f"Screenshot failed: {e}")
            try:
                body_text = await page.locator("body").inner_text()
                print("================ BODY TEXT ================")
                print(body_text)
                print("===========================================")
            except Exception as inner_e:
                print("Could not get body text:", inner_e)
            err_path = "docs/qa/screenshots/recruitment_error.png"
            await page.screenshot(path=err_path)
            print(f"Saved diagnostic screenshot to {err_path}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

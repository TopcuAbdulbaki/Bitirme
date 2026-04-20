from playwright.sync_api import sync_playwright
import time
import sys

print("Playwright başlatılıyor...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()
        page.goto("https://google.com")
        print("Masaüstünde Google Chrome açık olmalı. Lütfen 5 saniye bekle...")
        time.sleep(5)
        browser.close()
except Exception as e:
    print("Hata:", e)
    sys.exit(1)

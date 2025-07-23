from playwright.sync_api import sync_playwright
import pandas as pd
import time

def scrape_tiktok(query: str, num_videos: int = 3):
    comments_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="user_data",
            headless=False,
            viewport={"width": 1200, "height": 800}
        )

        page = browser.new_page()

        url = f"https://www.tiktok.com/tag/{query}" if not query.startswith("@") else f"https://www.tiktok.com/{query}"
        page.goto(url, timeout=60000)
        time.sleep(3)

        page.wait_for_selector('div[data-e2e="challenge-item-list"]', timeout=20000)
        videos = page.locator('div[id="column-item-video-container"]')
        total = min(videos.count(), num_videos)

        for idx in range(total):
            try:
                videos.nth(idx).click()
                time.sleep(4)

                try:
                    title = page.locator('span[data-e2e="new-desc-span"]').nth(0).inner_text()
                except:
                    title = "Sin título"

                page.wait_for_selector('div[data-e2e="search-comment-container"]', timeout=10000)
                for _ in range(5):
                    page.mouse.wheel(0, 1200)
                    time.sleep(1.2)

                comments = page.locator('div[data-e2e="search-comment-container"] p[data-e2e="comment-level-1"] span[dir]')
                for i in range(comments.count()):
                    text = comments.nth(i).inner_text()
                    comments_list.append({
                        "query": query,
                        "title": title,
                        "text": text
                    })

            except Exception as e:
                print(f"Error en video {idx+1}: {e}")
                continue

            if idx < total - 1:
                page.go_back()
                time.sleep(2)
                page.wait_for_selector('div[data-e2e="challenge-item-list"]', timeout=10000)
                videos = page.locator('div[id="column-item-video-container"]')

        browser.close()

    return comments_list
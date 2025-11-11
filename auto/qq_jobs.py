# scrape_qq_jobs.py
# 抓取 join.qq.com 职位列表 + 详情页（新 TAB 打开 自动关闭）
# 完全适配你提供的 DOM 结构

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


START_URL = lambda p: f"https://join.qq.com/post.html?query=p_{p}"
WAIT = 1.0
MAX_PAGES = 1


def clean_text(x: str):
    return x.strip().replace("\n", " ").replace("\t", " ").replace("  ", " ")


def extract_detail_section(page):
    """解析详情页的结构"""

    detail = {}

    boxes = page.locator("ul.post_detail > li.detail_box")
    count = boxes.count()

    for i in range(count):
        box = boxes.nth(i)

        title_el = box.locator(".subtitle")
        title = clean_text(title_el.text_content()) if title_el.count() else ""

        # 两种结构：
        # 1. <div class="text_box"><p class="detail_text">…</p></div>
        # 2. <li><div class="detail_text">…</div></li>
        text1 = box.locator(".text_box .detail_text")
        text2 = box.locator("> .detail_text")

        if text1.count():
            content = clean_text(text1.text_content())
        elif text2.count():
            content = clean_text(text2.text_content())
        else:
            content = ""

        if title:
            detail[title] = content

    return detail


def scrape_all():
    all_jobs = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()

        # 列表页
        page = context.new_page()

        for p in range(1, MAX_PAGES + 1):
            url = START_URL(p)
            print(f"\n➡️ 抓取列表页: {url}")

            page.goto(url, wait_until="networkidle")
            time.sleep(WAIT)

            rows = page.locator("ul.post_list > li.post_box")
            row_count = rows.count()

            if row_count == 0:
                print("⚠️ 无更多职位，停止。")
                break

            print(f"✅ 找到 {row_count} 条职位")

            for i in range(row_count):
                row = rows.nth(i)

                # 职位名称
                title = clean_text(row.locator(".post_title").text_content())

                # 标签
                tag_nodes = row.locator(".post_tag_box .post_tag")
                tags = [
                    clean_text(tag_nodes.nth(j).text_content())
                    for j in range(tag_nodes.count())
                ]

                # 工作地点
                location = clean_text(row.locator(".site_box .site").text_content())

                job = {
                    "title": title,
                    "tags": tags,
                    "location": location,
                    "list_page": url,
                }

                print(f"   🔍 抓取详情页（新 TAB）: {title}")

                # 等待新 tab 打开
                with context.expect_page() as new_tab_info:
                    row.click()  # 点击列表行 → 打开新TAB

                detail_page = new_tab_info.value

                # 等待加载
                detail_page.wait_for_load_state("networkidle")
                time.sleep(WAIT)

                # 提取详情
                detail_data = extract_detail_section(detail_page)
                job["detail"] = detail_data

                # 关闭详情页 tab
                detail_page.close()

                all_jobs.append(job)

            if row_count < 10:
                print("📌 最后一页，任务结束。")
                break

        browser.close()

    return all_jobs


if __name__ == "__main__":
    data = scrape_all()
    out = Path("qq_jobs.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 共抓取 {len(data)} 条职位（含详情）")
    print(f"📄 已写入文件：{out.absolute()}")

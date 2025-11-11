from playwright.sync_api import sync_playwright
import json
import time

LIST_URL = "https://talent.taotian.com/campus/position-list?batchId=100000040001&campusType=freshman&lang=zh"


# -----------------------------------------------------------
# 抓取职位详情页（完全不依赖类名）
# -----------------------------------------------------------
def scrape_details_from_page(page):
    page.wait_for_selector("div.deep-campus-position-detail")

    def get_basic(label):
        try:
            return page.locator(f"text={label}").locator(".. >> p.value").inner_text().strip()
        except:
            return ""

    basic_info = {
        "graduation_time": get_basic("毕业起止时间要求："),
        "recruitment_type": get_basic("招聘类型："),
        "recruitment_batch": get_basic("招聘批次："),
    }

    def get_block(text):
        try:
            return page.locator(f"div.card-header:has-text('{text}')").locator(".. >> div.main").inner_text().strip()
        except:
            return ""

    return {
        "basic_info": basic_info,
        "description": get_block("职位描述"),
        "requirements": get_block("职位要求"),
        "location": get_block("工作地点"),
    }


# -----------------------------------------------------------
# 抓取列表页（纯结构定位，无类名）
# -----------------------------------------------------------
def scrape_list_page(page, browser):
    positionList = page.locator("#positionList")
    html = positionList.inner_html()
    print(html)
    container = positionList.locator(":scope > div:nth-child(1) > div:nth-child(2)")
    print("container 子节点数 =", container.count())
    html = container.inner_html()
    print(html)
    items = container.locator(":scope > div").all()
    results = []
    print(f"  本页职位数：{len(items)}")

    for idx, item in enumerate(items):
        try:
            item_outer_html = item.evaluate("node => node.outerHTML")
            print(item_outer_html)
            # ========== 列表页字段：纯结构定位，完全无类名依赖 ==========
            # div[1] → 职位名称
            title = item.locator(":scope > div:nth-child(1)").inner_text().strip()

            # # div[2] → 信息块
            row = item.locator(":scope > div:nth-child(2) > div > div")
            update_time = row.locator(":scope > div:nth-child(1)").inner_text().strip()
            category    = row.locator(":scope > div:nth-child(2) div").inner_text().strip()
            location    = row.locator(":scope > div:nth-child(3) div").inner_text().strip()
            print(f"[{idx+1}/{len(items)}] 抓取详情：{title} , {update_time},{category},{location}")

            with page.expect_popup() as popup_info:
                item.click()

            detail_page = popup_info.value
            detail_page.wait_for_load_state()

            # 3. 抓取详情页
            detail_link = detail_page.url
            details = scrape_details_from_page(detail_page)

            # 4. 关闭详情页 Tab
            detail_page.close()

            # 5. 保存结果
            results.append({
                "title": title,
                "update_time": update_time,
                "category": category,
                "location": location,
                "link": detail_link,
                **details
            })

            time.sleep(0.3)

        except Exception as e:
            print("    [错误] 抓取失败：", e)

    return results


# -----------------------------------------------------------
# 分页抓取全部列表 & 全部详情
# -----------------------------------------------------------
def scrape_all_pages():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(LIST_URL, timeout=60000)
        page.wait_for_timeout(5000)
        page.wait_for_selector("span.next-tag-body", timeout=30000)

        # 获取总页数：格式类似 “1/6”
        page_text = page.locator("span.next-pagination-display").inner_text().strip()
        current, total = page_text.split("/")
        total_pages = int(total)

        print(f"✅ 总页数：{total_pages}")

        all_results = []

        total_pages = 1

        # 依次抓取 1~6 页
        for page_num in range(1, total_pages + 1):
            print(f"\n===== 抓取第 {page_num} 页 =====")

            page_results = scrape_list_page(page, browser)
            all_results.extend(page_results)

            # 最后一页不需要“下一页”
            if page_num == total_pages:
                break

            next_btn = page.locator("button.next-next")
            next_btn.click()
            page.wait_for_timeout(5000)

            page.wait_for_selector("span.next-pagination-display", timeout=30000)

        browser.close()
        return all_results


# -----------------------------------------------------------
# 主程序
# -----------------------------------------------------------
if __name__ == "__main__":
    results = scrape_all_pages()

    with open("taotian_jobs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 全部完成，共抓取 {len(results)} 条职位")
    print("✅ 已保存为 taotian_jobs.json")

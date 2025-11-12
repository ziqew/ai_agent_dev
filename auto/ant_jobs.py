#!/usr/bin/env python3
"""
蚂蚁集团校园招聘爬虫（最终整合版）
支持分页 + 新Tab详情页抓取职位描述/职位要求
"""

import asyncio
from playwright.async_api import async_playwright, Page
import json
import csv
from datetime import datetime
import time
from typing import List, Dict


# ===============================================================
# CSS 选择器配置
# ===============================================================
SELECTORS = {
    'job_list': 'ul.ant-list-items',
    'job_item': 'li.ant-list-item',
    'job_name': '[class*="item-name"]',
    'job_category': '[class*="item-description"] .ant-typography',
    'job_location': '[class*="item-actions-content"]',
    'job_tag': '[class*="item-tag"]',
}


# ===============================================================
# 抓取职位详情页（职位描述 + 职位要求）
# ===============================================================
async def get_job_details(page: Page) -> dict:
    """
    从职位详情页中提取【职位描述】和【职位要求】
    第一个 [class^="positionDetailConditions"] 为职位描述
    第二个 [class^="positionDetailConditions"] 为职位要求
    """
    await page.wait_for_selector('[class^="positionDetailConditions"]', timeout=15000)
    await asyncio.sleep(1.2)

    try:
        sections = await page.query_selector_all('[class^="positionDetailConditions"]')
        job_desc, job_req = "", ""

        if len(sections) >= 1:
            desc_el = await sections[0].query_selector('section')
            if desc_el:
                job_desc = (await desc_el.inner_text()).strip()

        if len(sections) >= 2:
            req_el = await sections[1].query_selector('section')
            if req_el:
                job_req = (await req_el.inner_text()).strip()

        return {"职位描述": job_desc, "职位要求": job_req}

    except Exception as e:
        print(f"⚠️ 抓取职位详情失败: {e}")
        return {"职位描述": "", "职位要求": ""}


# ===============================================================
# 解析当前页职位（并进入详情页）
# ===============================================================
async def parse_current_page(page: Page, current_page: int) -> List[Dict]:
    await page.wait_for_selector(SELECTORS['job_list'], timeout=10000)
    await asyncio.sleep(1)

    job_items = await page.query_selector_all(SELECTORS['job_item'])
    print(f"📋 第 {current_page} 页检测到 {len(job_items)} 个职位")

    jobs = []

    for index, item in enumerate(job_items):
        try:
            # 基础信息
            name_el = await item.query_selector(SELECTORS['job_name'])
            job_name = (await name_el.inner_text()).strip() if name_el else ""
            if not job_name:
                continue

            category_el = await item.query_selector(SELECTORS['job_category'])
            job_category = (await category_el.inner_text()).strip() if category_el else ""

            location_el = await item.query_selector(SELECTORS['job_location'])
            job_location = (await location_el.inner_text()).strip() if location_el else ""

            tag_els = await item.query_selector_all(SELECTORS['job_tag'])
            tags = list({(await t.inner_text()).strip() for t in tag_els if (await t.inner_text()).strip()})

            # 打开详情页
            print(f"  → 打开详情页: {job_name}")
            async with page.context.expect_page() as new_page_info:
                await item.click()
            detail_page = await new_page_info.value

            await detail_page.wait_for_load_state("networkidle")
            await asyncio.sleep(1.2)
            detail_link = detail_page.url
            details = await get_job_details(detail_page)
            await detail_page.close()

            jobs.append({
                "职位": job_name,
                "公司": "蚂蚁集团",
                "类别": job_category,
                "工作地点": job_location,
                "标签": ", ".join(tags),
                "链接": detail_link,
                **details,
            })

            await asyncio.sleep(0.8)

        except Exception as e:
            print(f"❌ 第 {index+1} 个职位抓取失败: {e}")
            continue

    print(f"✅ 第 {current_page} 页抓取完成，共 {len(jobs)} 个职位")
    return jobs


# ===============================================================
# 分页逻辑：获取总页数 + 跳转
# ===============================================================
async def get_total_pages(page: Page) -> int:
    """根据分页结构提取总页数"""
    try:
        await page.wait_for_selector('div.ant-list-pagination ul.ant-pagination', timeout=8000)
        page_items = await page.query_selector_all('ul.ant-pagination li.ant-pagination-item')
        last_page = 1
        for item in page_items:
            title = await item.get_attribute("title")
            if title and title.isdigit():
                last_page = max(last_page, int(title))
        print(f"📄 检测到总页数: {last_page}")
        return last_page
    except Exception as e:
        print(f"⚠️ 获取总页数失败: {e}")
        return 1


async def go_to_page(page: Page, target_page: int) -> bool:
    """跳转到指定页"""
    try:
        await page.wait_for_selector('ul.ant-pagination', timeout=8000)

        # 当前页
        active = await page.query_selector('li.ant-pagination-item-active')
        current_title = await active.get_attribute("title") if active else None
        if current_title == str(target_page):
            print(f"✅ 已在第 {target_page} 页")
            return True

        # 点击目标页
        target_item = await page.query_selector(f'li.ant-pagination-item[title="{target_page}"]')
        if target_item:
            print(f"➡️ 点击第 {target_page} 页")
            await target_item.click()
        else:
            next_btn = await page.query_selector('li.ant-pagination-next:not([aria-disabled="true"])')
            if next_btn:
                print("➡️ 点击下一页")
                await next_btn.click()
            else:
                print("⚠️ 未找到目标页或下一页按钮")
                return False

        await asyncio.sleep(2)
        await page.wait_for_selector(SELECTORS['job_list'], timeout=10000)
        print(f"✅ 成功跳转到第 {target_page} 页")
        return True

    except Exception as e:
        print(f"⚠️ 跳转到第 {target_page} 页失败: {e}")
        return False


# ===============================================================
# 主逻辑
# ===============================================================
async def scrape_all_pages(url: str, max_pages: int = None, headless: bool = False):
    all_jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        total_pages = await get_total_pages(page)
        pages_to_scrape = min(total_pages, max_pages) if max_pages else total_pages
        print(f"\n🌐 总页数: {total_pages}，计划抓取: {pages_to_scrape} 页\n")

        for page_num in range(1, pages_to_scrape + 1):
            print(f"\n================ 第 {page_num} 页 ================")
            jobs = await parse_current_page(page, page_num)
            all_jobs.extend(jobs)

            if page_num < pages_to_scrape:
                success = await go_to_page(page, page_num + 1)
                if not success:
                    break

        await browser.close()

    return all_jobs


# ===============================================================
# 保存结果
# ===============================================================
def save_to_csv(jobs: List[Dict], filename: str):
    if not jobs:
        return
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)


def save_to_json(jobs: List[Dict], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


# ===============================================================
# 入口
# ===============================================================
async def main():
    URL = "https://talent.antgroup.com/campus-full-list?type=campus_graduates"
    HEADLESS = False     # 设为 True 可后台运行
    MAX_PAGES = None        # 改为 None 抓取全部页

    print("=" * 70)
    print("🚀 蚂蚁集团校园招聘爬虫启动")
    print(f"URL: {URL}")
    print(f"最大页数: {MAX_PAGES}")
    print(f"无头模式: {HEADLESS}")
    print("=" * 70)

    start = time.time()
    jobs = await scrape_all_pages(URL, MAX_PAGES, HEADLESS)
    end = time.time()

    print(f"\n✅ 抓取完成，共 {len(jobs)} 条，用时 {end - start:.2f} 秒")

    if jobs:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_name = f"ant_jobs.csv"
        json_name = f"ant_jobs.json"
        save_to_csv(jobs, csv_name)
        save_to_json(jobs, json_name)
        print(f"\n📁 数据已保存：\n  CSV: {csv_name}\n  JSON: {json_name}")

    print("\n🎉 任务完成！")


if __name__ == "__main__":
    asyncio.run(main())

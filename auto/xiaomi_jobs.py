import asyncio
import json
import traceback
import pandas as pd
from playwright.async_api import async_playwright

TARGET_API = "https://xiaomi.jobs.f.mioffice.cn/api/v1/search/job/posts"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        results = []
        seen_pages = set()  # 避免重复

        page.on("response", lambda resp: asyncio.create_task(handle_response(resp, results)))

        entry_url = (
            "https://xiaomi.jobs.f.mioffice.cn/campus/?keywords=&category=&location="
            "&project=7522024429904805997&type=&job_hot_flag=&current=1&limit=10"
            "&functionCategory=&tag=&spread=J7NS6YR"
        )

        print("🚀 正在打开页面…")
        await page.goto(entry_url, wait_until="networkidle")

        # 抓第一页
        await asyncio.sleep(4)

        total_pages = await get_total_pages(page)
        print(f"📄 检测到总页数: {total_pages}")

        for current_page in range(1, total_pages + 1):
            if current_page in seen_pages:
                continue
            print(f"\n📑 抓取第 {current_page}/{total_pages} 页 ...")
            seen_pages.add(current_page)

            await asyncio.sleep(3)

            # 翻页逻辑
            if current_page < total_pages:
                success = await go_to_next_page(page, current_page + 1)
                if not success:
                    print("⚠️ 翻页失败，提前结束")
                    break

            await asyncio.sleep(5)  # 等接口请求完成

        # 保存结果
        if results:

            df = pd.DataFrame(results)

            # ===== 保存 CSV =====
            csv_path = f"xiaomi_jobs.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"📄 已保存 CSV：{csv_path}")

            # ===== 保存 JSON =====
            json_path = f"xiaomi_jobs.json"
            df.to_json(json_path, orient="records", force_ascii=False, indent=2)
            print(f"💾 已保存 JSON：{json_path}")

            print(f"✅ 共保存 {len(df)} 条岗位数据")
        else:
            print("⚠️ 未抓取到任何岗位数据")

        await browser.close()


# ---------------- 处理响应 ----------------
async def handle_response(resp, results):
    url = resp.url
    if TARGET_API in url and resp.request.method == "POST":
        try:
            if "application/json" not in resp.headers.get("content-type", ""):
                return
            data = await resp.json()
            posts = data.get("data", {}).get("job_post_list", [])
            for item in posts:
                results.append({
                    "职位": item.get("title", ""),
                    "公司": "小米",
                    "类别": item.get("job_function", {}).get("name", ""),
                    "工作地点": item.get("city_info", {}).get("name", ""),
                    "链接": f"https://xiaomi.jobs.f.mioffice.cn/campus/position/{item.get('id', '')}/detail",
                    "职位描述": item.get("description", ""),
                    "职位要求": item.get("requirement", "")
                })
            print(f"📦 抓到 {len(posts)} 条岗位数据")
        except Exception as e:
            print("⚠️ 解析响应失败:", e)
            traceback.print_exc()


# ---------------- 分页函数 ----------------
async def get_total_pages(page):
    """从分页 HTML 结构中提取总页数"""
    try:
        await page.wait_for_selector("ul.atsx-pagination", timeout=8000)
        items = await page.query_selector_all("ul.atsx-pagination li.atsx-pagination-item")
        pages = []
        for it in items:
            title = await it.get_attribute("title")
            if title and title.isdigit():
                pages.append(int(title))
        total = max(pages) if pages else 1
        return total
    except Exception as e:
        print("⚠️ 获取页数失败:", e)
        return 1


async def go_to_next_page(page, target_page):
    """点击页码或下一页"""
    try:
        selector = f'li.atsx-pagination-item[title="{target_page}"]'
        target = await page.query_selector(selector)
        if target:
            await target.click()
            print(f"➡️ 点击第 {target_page} 页")
        else:
            next_btn = await page.query_selector("li.atsx-pagination-next:not(.atsx-pagination-disabled)")
            if next_btn:
                await next_btn.click()
                print("➡️ 点击下一页按钮")
            else:
                print("⚠️ 没有找到下一页按钮")
                return False

        await asyncio.sleep(3)
        await page.wait_for_selector("ul.atsx-pagination", timeout=8000)
        return True

    except Exception as e:
        print("⚠️ 翻页失败:", e)
        return False


if __name__ == "__main__":
    asyncio.run(main())

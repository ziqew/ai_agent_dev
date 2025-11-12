import asyncio
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError
import random

BASE_URL = "https://join.qq.com/post.html?query=p_1,w_1,w_2,w_5,w_3,w_8,w_6,w_37,w_14,w_31,w_17,w_7,w_30,w_11,w_9&c_t=1"

async def extract_detail(context, detail_page):
    """解析职位详情页内容"""
    try:
        await detail_page.wait_for_selector(".post_detail", timeout=10000)
    except TimeoutError:
        return {"desc": "", "req": "", "plus": ""}

    # 提取所有 detail_box
    boxes = await detail_page.query_selector_all(".post_detail .detail_box")
    detail_data = {"desc": "", "req": "", "plus": ""}

    for box in boxes:
        subtitle = (await (await box.query_selector(".subtitle")).inner_text()).strip()
        text_box = await box.query_selector(".text_box .detail_text") or await box.query_selector(".detail_text")
        text = (await text_box.inner_text()).strip() if text_box else ""

        if "描述" in subtitle:
            detail_data["desc"] = text
        elif "要求" in subtitle:
            detail_data["req"] = text
        elif "加分" in subtitle or "注意" in subtitle:
            detail_data["plus"] = text

    return detail_data


async def extract_jobs(page, context):
    """提取当前页职位列表，并打开详情页抓取内容"""
    await page.wait_for_selector("ul.post_list li.post_box", timeout=10000)
    jobs = []
    cards = await page.query_selector_all("ul.post_list li.post_box")

    for idx, c in enumerate(cards):
        title = (await (await c.query_selector(".post_title")).inner_text()).strip()
        category = (await (await c.query_selector(".post_tag_box .post_tag")).inner_text()).strip()
        site = (await (await c.query_selector(".site_box .site")).inner_text()).strip()

        tags_el = await c.query_selector_all(".post_tag_box .post_tag")
        tags = [ (await e.inner_text()).strip().replace("｜", "").strip() for e in tags_el[1:] ]
        tags_text = " | ".join(tags)

        # 打开新标签页
        async with context.expect_page() as new_page_info:
            await c.click()
        detail_page = await new_page_info.value

        # 提取详情内容
        detail_link = detail_page.url
        detail_data = await extract_detail(context, detail_page)

        await detail_page.close()
        await asyncio.sleep(random.uniform(0.8, 1.6))

        jobs.append({
            "title": title,
            "company": "腾讯",
            "category": category,
            "tags": tags_text,
            "site": " ".join(site.split()),
            "link":detail_link,
            "desc": detail_data["desc"],
            "requirement": detail_data["req"],
            "plus": detail_data["plus"],
        })
        print(f"  ✅ [{idx+1}/{len(cards)}] {title}")

    return jobs


async def crawl_all(output="tencent_jobs.csv"):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded")

        all_jobs = []
        page_index = 1

        while True:
            print(f"\n🟢 抓取第 {page_index} 页")
            jobs = await extract_jobs(page, context)
            print(f"  ⮕ 第 {page_index} 页共 {len(jobs)} 条职位")
            all_jobs.extend(jobs)

            # 翻页逻辑
            next_btn = await page.query_selector(".el-pagination .btn-next")
            if not next_btn:
                print("⚠️ 未找到下一页按钮，停止。")
                break

            disabled = await next_btn.get_attribute("disabled")
            if disabled is not None:
                print("✅ 已到最后一页，结束抓取。")
                break

            await next_btn.click()
            page_index += 1

            # 等待分页刷新
            await page.wait_for_timeout(2000)
            await page.wait_for_selector(f".el-pager li.number.active:text-is('{page_index}')", timeout=10000)

        df = pd.DataFrame(all_jobs)
        df.to_csv(output, index=False, encoding="utf-8-sig")
        print(f"\n✅ 共抓取 {len(all_jobs)} 条职位，保存到 {output}")

        await browser.close()

def convert_csv_text():
    # 1. 输入 / 输出文件名
    input_csv = "tencent_jobs.csv"     # 你的源文件
    output_txt = "tencent_jobs.txt"    # 生成的txt文件

    # 2. 读取 CSV
    df = pd.read_csv(input_csv)

    # 3. 生成文本内容
    records = []
    for _, row in df.iterrows():
        job_text = (
            f"【职位】{row['职位']}\n"
            f"【公司】{row['公司']}\n"
            f"【类别】{row['类别']}\n"
            f"【标签】{row['标签']}\n"
            f"【工作地点】{row['工作地点']}\n"
            f"【岗位描述】\n{row['岗位描述']}\n\n"
            f"【岗位要求】\n{row['岗位要求']}\n\n"
            f"【加分项】\n{row['加分项']}\n"
        )
        records.append(job_text.strip())

    # 4. 用 "---" 分隔职位
    final_text = "\n---\n".join(records)

    # 5. 写入文件
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"✅ 已生成 {output_txt} ，共 {len(records)} 条职位信息。")


if __name__ == "__main__":
    convert_csv_text()
    #asyncio.run(crawl_all())

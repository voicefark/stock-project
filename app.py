
from flask import Flask, render_template, request
from stock_monthly_catching import get_stock_monthly

import pandas as pd
import requests
import xml.etree.ElementTree as ET

from email.utils import parsedate_to_datetime
from datetime import datetime
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

app = Flask(__name__)


# ==============================
# 股票名稱
# ==============================

STOCK_NAMES = {
    "2330": "台積電",
    "2454": "聯發科",
    "2317": "鴻海",
    "2308": "台達電",
    "2881": "富邦金",
    "2882": "國泰金",
    "0050": "元大台灣50",
    "0056": "元大高股息",
    "00878": "國泰永續高股息",
    "00919": "群益台灣精選高息"
}



# ==============================
# 新聞圖片解析器
# ==============================

class ImageParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.og_image = None
        self.twitter_image = None

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "meta":
            return

        attrs = dict(attrs)

        # 優先取得 Open Graph 圖片
        if (
            attrs.get("property", "").lower() == "og:image"
            and not self.og_image
        ):
            self.og_image = attrs.get("content")

        # 備用：Twitter 圖片
        if (
            attrs.get("name", "").lower() == "twitter:image"
            and not self.twitter_image
        ):
            self.twitter_image = attrs.get("content")


# ==============================
# 取得新聞圖片
# ==============================

def get_news_image(url):

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=8
        )

        response.raise_for_status()

        parser = ImageParser()
        parser.feed(response.text)

        # 優先使用 og:image
        image = parser.og_image or parser.twitter_image

        if image:

            image_url = urljoin(
                response.url,
                image.strip()
            )

            if image_url.startswith(("http://", "https://")):
                return image_url

    except Exception as e:

        print("新聞圖片取得失敗：", e)

    return None


# ==============================
# 取得近期經濟頭條
# ==============================

def get_recent_news():

    url = "https://news.google.com/rss/search"

    params = {
        "q": "經濟 OR 全球經濟 OR 台灣經濟 OR 通膨 OR 利率",
        "hl": "zh-TW",
        "gl": "TW",
        "ceid": "TW:zh-Hant"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        news_items = []

        # 取得台灣時區
        taiwan_timezone = timezone(
            timedelta(hours=8)
        )

        # 逐筆讀取新聞
        for item in root.findall("./channel/item"):

            title = item.findtext(
                "title",
                default=""
            ).strip()

            link = item.findtext(
                "link",
                default=""
            ).strip()

            pub_date = item.findtext(
                "pubDate",
                default=""
            ).strip()

            source_element = item.find("source")

            if source_element is not None:
                source = (
                    source_element.text or "未知來源"
                )
            else:
                source = "未知來源"

            if not title or not link:
                continue

            # 解析發布時間
            try:

                date_object = parsedate_to_datetime(
                    pub_date
                )

                date_object = date_object.astimezone(
                    taiwan_timezone
                )

                published = date_object.strftime(
                    "%Y-%m-%d %H:%M"
                )

                timestamp = date_object.timestamp()

            except Exception:

                published = pub_date
                timestamp = 0

            news_items.append({

                "title": title,
                "link": link,
                "source": source,
                "published": published,
                "timestamp": timestamp,
                "image": None

            })

        # 按照發布時間排序
        news_items.sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )

        # 只取得最新一則新聞
        if not news_items:
            return None, "目前沒有找到經濟頭條。"

        headline = news_items[0]

        # 擷取頭條圖片
        headline["image"] = get_news_image(
            headline["link"]
        )

        # 終端機除錯資訊
        print("========== 經濟頭條 ==========")
        print("標題：", headline["title"])
        print("來源：", headline["source"])
        print("時間：", headline["published"])
        print("圖片：", headline["image"])
        print("==============================")

        return headline, None

    except Exception as e:

        print("取得經濟新聞失敗：", e)

        return None, "目前無法取得經濟新聞，請稍後再試。"


# ==============================
# 日期轉換
# ==============================

def convert_date(value):

    text = str(value).strip()

    # 民國日期，例如 115/09/24
    match = re.match(r"^(\d{3})/(\d{1,2})/(\d{1,2})$", text)

    if match:
        year = int(match.group(1)) + 1911
        month = int(match.group(2))
        day = int(match.group(3))

        return pd.Timestamp(year, month, day)

    # 民國日期，例如 1150924
    match = re.match(r"^(\d{3})(\d{2})(\d{2})$", text)

    if match:
        year = int(match.group(1)) + 1911
        month = int(match.group(2))
        day = int(match.group(3))

        return pd.Timestamp(year, month, day)

    return pd.to_datetime(value, errors="coerce")


# ==============================
# 取得單支股票資料
# ==============================

def get_stock_result(stock_no, year, month):

    all_data = []

    # 為了計算 MA20，往前取得三個月資料
    for offset in range(3, -1, -1):

        fetch_year = year
        fetch_month = month - offset

        while fetch_month <= 0:
            fetch_month += 12
            fetch_year -= 1

        try:
            df = get_stock_monthly(
                stock_no,
                str(fetch_year),
                str(fetch_month)
            )

            if df is not None and not df.empty:
                all_data.append(df)

        except Exception as e:
            print(
                f"{stock_no} "
                f"{fetch_year}/{fetch_month} "
                f"資料取得失敗：{e}"
            )

    if not all_data:
        return None

    df_all = pd.concat(
        all_data,
        ignore_index=True
    )

    # 整理資料
    required_columns = [
        "date",
        "closing"
    ]

    for column in required_columns:
        if column not in df_all.columns:
            return None

    df_all["date"] = df_all["date"].apply(convert_date)

    df_all["closing"] = pd.to_numeric(
        df_all["closing"],
        errors="coerce"
    )

    df_all = df_all.dropna(
        subset=["date", "closing"]
    )

    df_all = df_all.sort_values("date")

    df_all = df_all.drop_duplicates(
        subset=["date"],
        keep="last"
    )

    # 計算均線
    df_all["ma5"] = df_all["closing"].rolling(
        window=5
    ).mean()

    df_all["ma20"] = df_all["closing"].rolling(
        window=20
    ).mean()

    # 只顯示使用者查詢的月份
    target_data = df_all[
        (df_all["date"].dt.year == year) &
        (df_all["date"].dt.month == month)
    ].copy()

    if target_data.empty:
        return None

    # 整理成網頁需要的格式
    records = []

    for _, row in target_data.iterrows():

        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "closing": round(float(row["closing"]), 2),
            "ma5": (
                round(float(row["ma5"]), 2)
                if pd.notna(row["ma5"])
                else None
            ),
            "ma20": (
                round(float(row["ma20"]), 2)
                if pd.notna(row["ma20"])
                else None
            )
        })

    return {
        "stock_no": stock_no,
        "stock_name": STOCK_NAMES.get(
            stock_no,
            "未知股票"
        ),
        "records": records,
        "chart_labels": [
            row["date"] for row in records
        ],
        "chart_closing": [
            row["closing"] for row in records
        ],
        "chart_ma5": [
            row["ma5"] for row in records
        ],
        "chart_ma20": [
            row["ma20"] for row in records
        ]
    }


# ==============================
# 首頁
# ==============================

@app.route("/")
def index():

    headline, news_error = get_recent_news()

    return render_template(
        "index.html",
        headline=headline,
        news_error=news_error,
        stock_results=[],
        stocks_input="",
        year=datetime.now().year,
        month=datetime.now().month,
        error=None
    )


# ==============================
# 股票查詢
# ==============================

@app.route("/stock")
def stock():

    # 支援多支股票
    stocks = request.args.getlist("stocks")

    # 也支援逗號分隔的股票代號
    if not stocks:
        stocks_text = request.args.get("stock", "")
        stocks = stocks_text.split(",")

    stocks = [
        s.strip()
        for s in stocks
        if s.strip()
    ]

    # 移除重複股票
    stocks = list(dict.fromkeys(stocks))

    stocks_input = ",".join(stocks)

    try:
        year = int(request.args.get("year", datetime.now().year))
        month = int(request.args.get("month", datetime.now().month))

    except ValueError:
        return render_error("年份或月份格式錯誤。")

    if not stocks:
        return render_error("請輸入至少一支股票。")

    if len(stocks) > 10:
        return render_error("最多只能同時查詢 10 支股票。")

    if not 2000 <= year <= 2100:
        return render_error("年份必須介於 2000 至 2100。")

    if not 1 <= month <= 12:
        return render_error("月份必須介於 1 至 12。")

    for stock_no in stocks:

        if not stock_no.isdigit():
            return render_error("股票代號只能輸入數字。")

        if stock_no == "114514":
            return render_error("這麼臭的股票有存在的必要嗎？")

    stock_results = []
    errors = []

    for stock_no in stocks:

        try:
            result = get_stock_result(
                stock_no,
                year,
                month
            )

            if result is None:
                errors.append(
                    f"{stock_no}：查無資料"
                )
            else:
                stock_results.append(result)

        except Exception as e:

            print(f"{stock_no} 查詢失敗：{e}")

            errors.append(
                f"{stock_no}：資料處理失敗"
            )

    error = None

    if errors:
        error = "；".join(errors)

    if not stock_results and not error:
        error = "查無股票資料。"

    return render_template(
        "index.html",
        headline=None,
        news_error=None,
        stock_results=stock_results,
        stocks_input=stocks_input,
        year=year,
        month=month,
        error=error
    )


# ==============================
# 錯誤頁面
# ==============================

def render_error(message):

    return render_template(
        "index.html",
        headline=None,
        news_error=None,
        stock_results=[],
        stocks_input="",
        year=datetime.now().year,
        month=datetime.now().month,
        error=message
    )


# ==============================
# 啟動 Flask
# ==============================

if __name__ == "__main__":
    app.run(debug=True)

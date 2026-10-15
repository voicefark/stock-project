from flask import Flask,render_template,request#request是Flask 要從瀏覽器取得使用者送過來的資料。
from stock_monthly_catching import get_stock_monthly #2026/10/8更新：呼叫其他程式的函式
import pandas as pd
app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")
@app.route("/hello")
def hello():
    return "hello student"

@app.route("/stock")
def stock():
    # 取得使用者輸入的查詢條件
    stock_no = request.args.get("stock")
    year = request.args.get("year")
    month = request.args.get("month")

    # 檢查輸入是否完整
    if not stock_no or not year or not month:
        return render_template(
            "index.html",
            error="請輸入股票代號、年份和月份。"
        )

    try:
        year_num = int(year)
        month_num = int(month)

        if not 1 <= month_num <= 12:
            raise ValueError

    except ValueError:
        return render_template(
            "index.html",
            error="年份或月份格式錯誤。"
        )

    # 取得查詢月份前 3 個月，以及查詢月份本身
    df_parts = []

    for offset in range(3, -1, -1):
        # 將年月轉成連續的月份編號
        total_month = year_num * 12 + (month_num - 1) - offset

        fetch_year = total_month // 12
        fetch_month = total_month % 12 + 1

        # 取得這個月份的股價
        df = get_stock_monthly(
            stock_no,
            str(fetch_year),
            str(fetch_month)
        )

        if df is not None and not df.empty:
            df_parts.append(df)

    # 如果所有月份都沒有資料
    if not df_parts:
        return render_template(
            "index.html",
            error="查無資料，請確認股票代號、年份和月份。"
        )

    # 合併歷史資料
    df_all = pd.concat(df_parts, ignore_index=True)

    # 確保日期與收盤價格式正確
    df_all["date"] = pd.to_datetime(df_all["date"])
    df_all["closing"] = pd.to_numeric(
        df_all["closing"], errors="coerce"
    )

    # 依日期排序，避免移動平均計算錯誤
    df_all = (
        df_all
        .sort_values("date")
        .drop_duplicates(subset=["date"])
        .reset_index(drop=True)
    )

    # 使用所有已取得的歷史資料計算移動平均
    df_all["ma5"] = df_all["closing"].rolling(
        window=5, min_periods=5
    ).mean()

    df_all["ma20"] = df_all["closing"].rolling(
        window=20, min_periods=20
    ).mean()

    # 只留下使用者選擇的月份
    df_month = df_all[
        (df_all["date"].dt.year == year_num) &
        (df_all["date"].dt.month == month_num)
    ].copy()

    if df_month.empty:
        return render_template(
            "index.html",
            error="查詢月份沒有股價資料，請確認輸入內容。"
        )

    # 圖表使用的日期與收盤價
    chart_labels = df_month["date"].dt.strftime(
        "%Y-%m-%d"
    ).tolist()

    chart_closing = df_month["closing"].tolist()

    # 將沒有足夠資料的移動平均轉成 None
    chart_ma5 = [
        None if pd.isna(value) else round(float(value), 2)
        for value in df_month["ma5"]
    ]

    chart_ma20 = [
        None if pd.isna(value) else round(float(value), 2)
        for value in df_month["ma20"]
    ]

    # 整理表格資料
    df_month["date"] = df_month["date"].dt.strftime(
        "%Y-%m-%d"
    )

    df_month = df_month.round({
        "closing": 2,
        "ma5": 2,
        "ma20": 2
    })

    records = (
        df_month.astype(object)
        .where(pd.notna(df_month), None)
        .to_dict(orient="records")
    )

    # 將表格與圖表資料傳給 HTML
    return render_template(
        "index.html",
        records=records,
        stock_no=stock_no,
        year=year,
        month=month,
        chart_labels=chart_labels,
        chart_closing=chart_closing,
        chart_ma5=chart_ma5,
        chart_ma20=chart_ma20
    )
if __name__ == "__main__":
    app.run(debug=True)
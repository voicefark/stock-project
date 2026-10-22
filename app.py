from flask import Flask,render_template,request#request是Flask 要從瀏覽器取得使用者送過來的資料。
from stock_monthly_catching import get_stock_monthly #2026/10/8更新：呼叫其他程式的函式
import pandas as pd
app = Flask(__name__)

STOCK_NAMES = {
    "2330": "台積電",
    "0050": "元大台灣50",
    "00878": "國泰永續高股息"
}
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/hello")
def hello():
    return "hello student"


@app.route("/stock")
def stock():
    # 取得使用者選擇的股票、年份與月份
    selected_stocks = request.args.getlist("stocks")
    year = request.args.get("year")
    month = request.args.get("month")

    # 檢查輸入是否完整
    if not selected_stocks or not year or not month:
        return render_template(
            "index.html",
            error="請至少選擇一檔股票，並輸入年份和月份。",
            selected_stocks=selected_stocks,
            year=year,
            month=month
        )

    # 檢查股票代號是否在目前支援的清單內
    invalid_stocks = [
        stock for stock in selected_stocks
        if stock not in STOCK_NAMES
    ]

    if invalid_stocks:
        return render_template(
            "index.html",
            error="包含不支援的股票代號：" + ", ".join(invalid_stocks),
            selected_stocks=selected_stocks,
            year=year,
            month=month
        )

    # 檢查年份與月份格式
    try:
        year_num = int(year)
        month_num = int(month)

        if year_num < 1900 or not 1 <= month_num <= 12:
            raise ValueError

    except ValueError:
        return render_template(
            "index.html",
            error="年份或月份格式錯誤。",
            selected_stocks=selected_stocks,
            year=year,
            month=month
        )

    # 每檔股票各自整理查詢結果
    stock_results = []
    errors = []

    for stock_no in selected_stocks:
        stock_name = STOCK_NAMES[stock_no]
        df_parts = []

        # 取得查詢月份之前 3 個月及查詢月份
        for offset in range(3, -1, -1):
            total_month = (
                year_num * 12 + (month_num - 1) - offset
            )

            fetch_year = total_month // 12
            fetch_month = total_month % 12 + 1

            try:
                df = get_stock_monthly(
                    stock_no,
                    str(fetch_year),
                    str(fetch_month)
                )
            except Exception:
                df = None

            if df is not None and not df.empty:
                df_parts.append(df)

        # 這檔股票完全沒有取得資料
        if not df_parts:
            errors.append(
                f"{stock_name}（{stock_no}）查無資料"
            )
            continue

        # 合併這檔股票的歷史資料
        df_all = pd.concat(df_parts, ignore_index=True)

        df_all["date"] = pd.to_datetime(
            df_all["date"], errors="coerce"
        )
        df_all["closing"] = pd.to_numeric(
            df_all["closing"], errors="coerce"
        )

        df_all = (
            df_all
            .dropna(subset=["date", "closing"])
            .sort_values("date")
            .drop_duplicates(subset=["date"])
            .reset_index(drop=True)
        )

        # 計算移動平均
        df_all["ma5"] = df_all["closing"].rolling(
            window=5, min_periods=5
        ).mean()

        df_all["ma20"] = df_all["closing"].rolling(
            window=20, min_periods=20
        ).mean()

        # 只保留查詢月份
        df_month = df_all[
            (df_all["date"].dt.year == year_num) &
            (df_all["date"].dt.month == month_num)
        ].copy()

        if df_month.empty:
            errors.append(
                f"{stock_name}（{stock_no}）在指定月份沒有資料"
            )
            continue

        # 整理圖表資料
        chart_labels = df_month["date"].dt.strftime(
            "%Y-%m-%d"
        ).tolist()

        chart_closing = df_month["closing"].tolist()

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
            "opening": 2,
            "highest": 2,
            "lowest": 2,
            "closing": 2,
            "ma5": 2,
            "ma20": 2
        })

        records = (
            df_month.astype(object)
            .where(pd.notna(df_month), None)
            .to_dict(orient="records")
        )

        # 將這檔股票的結果存起來
        stock_results.append({
            "stock_no": stock_no,
            "stock_name": stock_name,
            "records": records,
            "chart_labels": chart_labels,
            "chart_closing": chart_closing,
            "chart_ma5": chart_ma5,
            "chart_ma20": chart_ma20
        })

    # 所有股票都查不到資料
    if not stock_results:
        return render_template(
            "index.html",
            error="；".join(errors) or "查無資料。",
            selected_stocks=selected_stocks,
            year=year,
            month=month
        )

    return render_template(
        "index.html",
        stock_results=stock_results,
        selected_stocks=selected_stocks,
        year=year,
        month=month,
        error="；".join(errors) if errors else None
    )

if __name__ == "__main__":
    app.run(debug=True)
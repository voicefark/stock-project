from flask import Flask, render_template, request
from stock_monthly_catching import get_stock_monthly
import pandas as pd


app = Flask(__name__)


# 常見股票名稱
# 未收錄的股票仍然可以查詢，只是暫時顯示股票代號
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


# 計算指定月份往前推幾個月
def get_previous_month(year, month, offset):
    total_month = year * 12 + month - 1 - offset

    new_year = total_month // 12
    new_month = total_month % 12 + 1

    return new_year, new_month


# 取得股票名稱
def get_stock_name(stock_no):
    return STOCK_NAMES.get(
        stock_no,
        f"股票代號 {stock_no}"
    )


# 建立錯誤回應
def render_error(message, stocks_input="", year="", month=""):
    return render_template(
        "index.html",
        error=message,
        stocks_input=stocks_input,
        year=year,
        month=month,
        stock_results=[]
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        stocks_input="",
        year="",
        month="",
        stock_results=[]
    )


@app.route("/stock", methods=["GET"])
def stock():

    # =========================
    # 1. 取得使用者輸入
    # =========================

    stocks_input = request.args.get("stocks", "").strip()
    year_input = request.args.get("year", "").strip()
    month_input = request.args.get("month", "").strip()

    # 使用逗號分割股票代號
    selected_stocks = [
        item.strip()
        for item in stocks_input.split(",")
        if item.strip()
    ]

    # =========================
    # 2. 檢查輸入是否完整
    # =========================

    if not selected_stocks or not year_input or not month_input:
        return render_error(
            "請輸入股票代號、年份和月份。",
            stocks_input,
            year_input,
            month_input
        )

    # =========================
    # 3. 檢查股票代號格式
    # =========================

    if any(not item.isdigit() for item in selected_stocks):
        return render_error(
            "股票代號只能輸入數字，請使用逗號分隔。",
            stocks_input,
            year_input,
            month_input
        )

    # 移除重複股票代號，保留原本順序
    selected_stocks = list(dict.fromkeys(selected_stocks))

    # 限制一次最多查詢 10 檔
    if len(selected_stocks) > 10:
        return render_error(
            "一次最多只能查詢 10 檔股票。",
            stocks_input,
            year_input,
            month_input
        )

    # =========================
    # 4. 檢查年份與月份
    # =========================

    try:
        year = int(year_input)
        month = int(month_input)

        if year < 2000 or year > 2100:
            raise ValueError

        if month < 1 or month > 12:
            raise ValueError

    except ValueError:
        return render_error(
            "年份或月份格式錯誤。",
            stocks_input,
            year_input,
            month_input
        )

    # =========================
    # 5. 查詢每一檔股票
    # =========================

    stock_results = []
    errors = []

    for stock_no in selected_stocks:

        stock_name = get_stock_name(stock_no)

        try:
            # 儲存最近四個月的資料
            # 用來計算 MA5、MA20
            all_data = []

            # 由較早的月份開始查詢
            for offset in range(3, -1, -1):

                query_year, query_month = get_previous_month(
                    year,
                    month,
                    offset
                )

                df = get_stock_monthly(
                    stock_no,
                    str(query_year),
                    str(query_month)
                )

                if df is not None and not df.empty:
                    all_data.append(df)

            # 沒有取得任何資料
            if not all_data:
                if(stock_no=="114514"):
                    errors.append(f"{stock_no}：這麼臭的股票有存在的必要嗎?")
                    continue
                errors.append(
                    f"股票代號{stock_no}：查無資料"
                )
                continue

            # 合併四個月資料
            df = pd.concat(
                all_data,
                ignore_index=True
            )

            # 確保必要欄位存在
            required_columns = [
                "date",
                "opening",
                "highest",
                "lowest",
                "closing",
                "volume"
            ]

            if not all(
                column in df.columns
                for column in required_columns
            ):
                errors.append(
                    f"{stock_no}：股價資料欄位不完整"
                )
                continue

            # 將價格轉換為數值
            df["closing"] = pd.to_numeric(
                df["closing"],
                errors="coerce"
            )

            # 移除無效收盤價
            df = df.dropna(subset=["closing"])

            # 移除重複日期
            df = df.drop_duplicates(
                subset=["date"],
                keep="last"
            )

            # 四個月資料依照取得順序排列，
            # 再計算移動平均
            df["ma5"] = df["closing"].rolling(
                window=5
            ).mean()

            df["ma20"] = df["closing"].rolling(
                window=20
            ).mean()

            # =========================
            # 6. 只保留使用者指定月份
            # =========================

            target_df = get_stock_monthly(
                stock_no,
                str(year),
                str(month)
            )

            if target_df is None or target_df.empty:
                errors.append(
                    f"{stock_no}（{stock_name}）：指定月份查無資料"
                )
                continue

            target_dates = set(
                target_df["date"].astype(str)
            )

            result_df = df[
                df["date"].astype(str).isin(target_dates)
            ].copy()

            if result_df.empty:
                errors.append(
                    f"{stock_no}（{stock_name}）：無法整理指定月份資料"
                )
                continue

            # =========================
            # 7. 整理表格資料
            # =========================

            records = []

            for _, row in result_df.iterrows():

                records.append({
                    "date": str(row["date"]),
                    "opening": row["opening"],
                    "highest": row["highest"],
                    "lowest": row["lowest"],
                    "closing": float(row["closing"]),
                    "volume": row["volume"],
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

            # =========================
            # 8. 整理折線圖資料
            # =========================

            chart_labels = [
                str(row["date"])
                for _, row in result_df.iterrows()
            ]

            chart_closing = [
                float(row["closing"])
                for _, row in result_df.iterrows()
            ]

            chart_ma5 = [
                round(float(value), 2)
                if pd.notna(value)
                else None
                for value in result_df["ma5"]
            ]

            chart_ma20 = [
                round(float(value), 2)
                if pd.notna(value)
                else None
                for value in result_df["ma20"]
            ]

            # =========================
            # 9. 儲存股票查詢結果
            # =========================

            stock_results.append({
                "stock_no": stock_no,
                "stock_name": stock_name,
                "records": records,
                "chart_labels": chart_labels,
                "chart_closing": chart_closing,
                "chart_ma5": chart_ma5,
                "chart_ma20": chart_ma20
            })

        except Exception as e:

            errors.append(
                f"{stock_no}（{stock_name}）：查詢發生錯誤：{str(e)}"
            )

    # =========================
    # 10. 回傳查詢結果
    # =========================

    return render_template(
        "index.html",
        stock_results=stock_results,
        stocks_input=stocks_input,
        selected_stocks=selected_stocks,
        year=year,
        month=month,
        error="；".join(errors) if errors else None
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
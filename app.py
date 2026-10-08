from flask import Flask,render_template,request#request是Flask 要從瀏覽器取得使用者送過來的資料。
from stock_monthly_catching import get_stock_monthly #2026/10/8更新：呼叫其他程式的函式
app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")
@app.route("/hello")
def hello():
    return "hello student"
#app.route("/stock")
def stock():
	stock=request.args.get("stock")
	year=request.args.get("year")
	month=request.args.get("month")
	return f"股票：{stock}，年份：{year}，月份：{month}"
if __name__ == "__main__":
    app.run(debug=True)
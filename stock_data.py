import requests
import sys
url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
response = requests.get(url)
def get_stock(name):
	data = response.json()
	for stock in data:
    		if stock["Code"] == name:
        		return stock
	return None

def show_stock(stock):
	print("股票名稱：", stock["Name"])
	print("開盤價：", stock["OpeningPrice"])
	print("最高價：", stock["HighestPrice"])
	print("最低價：", stock["LowestPrice"])
	print("收盤價：", stock["ClosingPrice"])
	print("漲跌：", stock["Change"])
	print("成交量：", stock["TradeVolume"])
	endPrice=float(stock["ClosingPrice"])
	change=float(stock["Change"])
	print("漲跌幅：",change/(endPrice-change)*100,'%')

while True:
	stock=input("輸入股票代號(輸入q結束詢問)：")
	if stock=="q":
		break
	result=get_stock(stock)
	if result:
		show_stock(result)
	else:
		print("找不到股票")
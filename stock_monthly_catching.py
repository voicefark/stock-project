#2026/10/8更新：模組化get_stock_monthly以供其他程式使用
import pandas as pd
import requests
url = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"

def get_stock_monthly(stock,year,month):
	params = {
		"stockNo": stock,
		"date": year+(''if len(month)>1 else '0')+month+'01',
		"response": "json"
	}
	response = requests.get(url,params=params)
	if response.status_code!=200:#檢查http狀態
		return None
	data=response.json()
	if data["stat"] == "OK":#檢查TWSE的股票查詢結果
		fields = data["fields"]
		rows = data["data"]
		rows_data=[]
		for row in rows:#將資料轉換成DataFrame能使用的格式
			date = row[0]
			roc_year,month,day=date.split("/")#date回傳民國年
			date=f"{int(roc_year)+1911}/{month}/{day}"#換算成西元年
			volume = int(row[1].replace(",", ""))#成交量
			opening = float(row[3].replace(",", ""))#開盤價
			highest = float(row[4].replace(",", ""))#最高價
			lowest = float(row[5].replace(",", ""))#最低價
			closing = float(row[6].replace(",", ""))#收盤價
			rows_data.append([
				date,
				opening,
				highest,
				lowest,
				closing,
				volume
			])
		df=pd.DataFrame(#建立DateFrame
			rows_data,
			columns=[
				'date',
				'opening',
				'highest',
				'lowest',
				'closing',
				'volume'
				]		
		)
		return df
	else:
		return None
#2026/10/8更新：判斷如果是由其他程式執行此程式，則以下部分不執行
if __name__=="__main__":
	while True:
		stock=input("輸入股票代號(輸入q結束詢問)：")
		if stock=="q":
			break
		year=input("輸入欲查詢西元年分：")
		month=input("輸入欲查詢月份：")
		df=get_stock_monthly(stock,year,month)
		if df is None:
			print("查無資料")
		else:
			print(df)

	
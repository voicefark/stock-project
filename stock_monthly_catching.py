import pandas as pd
import requests
url = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
params = {
    "stockNo": "2330",
    "date": "20260901",
    "response": "json"
}

while True:
	stock=input("輸入股票代號(輸入q結束詢問)：")
	if stock=="q":
		break
	year=input("輸入欲查詢西元年分：")
	month=input("輸入欲查詢月份：")
	params["stockNo"]=stock
	params["date"]=year+'0'+month+'01'
	response = requests.get(url,params=params)
	print(response.status_code)
	data=response.json()
	if data["stat"] == "OK":
		fields = data["fields"]
		rows = data["data"]
		print(fields)
		rows_data=[]
		for row in rows:
			date = row[0]
			roc_year,month,day=date.split("/")
			date=f"{int(roc_year)+1911}/{month}/{day}"
			volume = int(row[1].replace(",", ""))
			opening = float(row[3].replace(",", ""))
			highest = float(row[4].replace(",", ""))
			lowest = float(row[5].replace(",", ""))
			closing = float(row[6].replace(",", ""))
			rows_data.append([
				date,
				opening,
				highest,
				lowest,
				closing,
				volume
			])
		df=pd.DataFrame(
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
		'''
		df["date"]=pd.to_datetime(df["date"],format="%Y/%m/%d")
		print(df)
		print(df.dtypes)
		print("最高收盤價：",df["closing"].max())
		print("最低收盤價：",df["closing"].min())
		print("平均收盤價：",df["closing"].mean())
		print("總成交量：",df["volume"].sum())
		max_volume_day_index=df["closing"].idxmax()
		print("最高收盤價那一天：")
		print(df.loc[max_volume_day_index])
		min_volume_day_index=df["closing"].idxmin()
		print("最低收盤價那一天：")
		print(df.loc[min_volume_day_index])
		'''
		print(df[df["closing"]>1800])
	else:
		print(data["stat"])
	
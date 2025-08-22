from ib_insync import IB, Stock

ib = IB(); ib.connect('127.0.0.1', 7497, clientId=2)
ib.reqMarketDataType(3)

contract = Stock('AAPL','SMART','USD', primaryExchange='NASDAQ')
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='1 D',
    barSizeSetting='5 mins',
    whatToShow='TRADES',
    useRTH=False
)
print(bars[-1])  # son bar
ib.disconnect()

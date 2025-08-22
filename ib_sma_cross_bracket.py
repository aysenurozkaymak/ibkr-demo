# ib_paper_sma_bracket.py
# IBKR Paper: SMA(10) üstündeyse LONG + bracket (TP/SL).
# Notlar:
# - TWS açık + Paper login (port 7497)
# - Canlı veri aboneliğin yoksa bile çalışır (delayed + historical bar)
# - util.nanToNone yerine kendi güvenli helper'ımız var.

from ib_insync import *
from statistics import mean
import math

HOST='127.0.0.1'
PORT=7497            # Paper
CLIENT_ID=7

SYMBOL='AAPL'
EX='SMART'
CCY='USD'
PRIMARY='NASDAQ'

BAR_SIZE='1 min'
DURATION='30 M'
SMA_WIN=10
QTY=1
TP_PCT=0.005         # +%0.5
SL_PCT=0.005         # -%0.5

def nan_to_none(v):
    try:
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
    except Exception:
        return None

def last_from_ticker(t: Ticker):
    # Gecikmeli/izin yoksa bazı alanlar NaN olur; mümkün olanı sırayla deneriz
    for attr in ('last', 'close', 'marketPrice', 'midpoint'):
        val = getattr(t, attr)() if callable(getattr(t, attr, None)) else getattr(t, attr, None)
        val = nan_to_none(val)
        if val is not None:
            return float(val)
    return None

def make_bracket(parentId:int, side:str, qty:int, tp:float, sl:float):
    parent = MarketOrder(side, qty, transmit=False); parent.orderId = parentId
    tpOrd  = LimitOrder('SELL' if side=='BUY' else 'BUY', qty, tp, parentId=parentId, transmit=False); tpOrd.orderId = parentId+1
    slOrd  = StopOrder('SELL' if side=='BUY' else 'BUY', qty, sl, parentId=parentId, transmit=True);  slOrd.orderId = parentId+2
    return parent, tpOrd, slOrd

def main():
    ib = IB()
    print('Bağlanıyor…')
    ib.connect(HOST, PORT, clientId=CLIENT_ID)
    print('Bağlandı.')

    # Gecikmeli veri tipine geç (aboneliğin yoksa gerekli)
    ib.reqMarketDataType(3)  # 3 = delayed

    contract = Stock(SYMBOL, EX, CCY, primaryExchange=PRIMARY)

    # 1) Tarihsel barları çek (abonelik gerektirmez) → SMA hesapla
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr=DURATION,
        barSizeSetting=BAR_SIZE,
        whatToShow='TRADES',
        useRTH=False
    )
    closes = [b.close for b in bars]
    if len(closes) < SMA_WIN:
        print(f"Yeterli bar yok: {len(closes)}/{SMA_WIN}")
        ib.disconnect(); return
    sma = mean(closes[-SMA_WIN:])
    hist_last = closes[-1]   # en son bar kapanışı (gecikmeli olabilir)

    # 2) (Opsiyonel) canlı ticker dene; olmazsa tarihsel son kapanışı kullan
    ticker = ib.reqMktData(contract, '', False, False)
    ib.sleep(2)
    live_last = last_from_ticker(ticker)
    last = live_last if live_last is not None else hist_last

    print(f"Last≈{last:.2f} | SMA({SMA_WIN})={sma:.2f}  (live_last={live_last}, hist_last={hist_last})")

    if last > sma:
        tp = round(last*(1+TP_PCT), 2)
        sl = round(last*(1-SL_PCT), 2)
        oid = ib.client.getReqId()
        p, tpo, slo = make_bracket(oid, 'BUY', QTY, tp, sl)
        print(f">> LONG denemesi: {QTY} {SYMBOL} @MKT | TP={tp} | SL={sl}")
        ib.placeOrder(contract, p); ib.placeOrder(contract, tpo); ib.placeOrder(contract, slo)
        ib.sleep(2)
        print("Emirler gönderildi.")
    else:
        print("Kural tetiklenmedi (Last <= SMA). Emir gönderilmedi.")

    ib.disconnect()
    print("Bağlantı kapandı.")

if __name__ == '__main__':
    util.run(main())

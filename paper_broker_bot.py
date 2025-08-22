# paper_broker_bot.py
# Sanal Paper Broker: SMA(10) kırılımında AL (long) veya SAT (short) açar, TP/SL ile yönetir.

import time
from typing import Optional
import pandas as pd
import yfinance as yf

# ------------------- Ayarlar -------------------
SYMBOL = "AAPL"       # Denemek için TSLA, NVDA, META veya BIST: THYAO.IS
INTERVAL = "1m"       # 1 dakikalık bar
LOOKBACK = "1d"       # 1 gün geriye git
SMA_WINDOW = 10
QTY = 1

TP_PCT = 0.005        # +%0.5 kâr al
SL_PCT = 0.005        # -%0.5 zarar kes
REFRESH_SEC = 5       # Kaç saniyede bir fiyat kontrol edilsin
EPS = 0.02            # SMA kesişimi için tolerans (2 cent)

# ---------------- Yardımcılar ------------------
def scalar(v) -> float:
    try:
        return v.item()
    except Exception:
        return float(v)

def fetch_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False
    )
    if df is None or df.empty:
        raise RuntimeError("Veri alınamadı (Yahoo limit olabilir).")
    try:
        df.index = df.index.tz_localize(None)
    except Exception:
        pass
    return df

def compute_sma(df: pd.DataFrame, window: int) -> float:
    return scalar(df["Close"].tail(window).mean())

# ---------------- Paper Broker -----------------
class PaperBroker:
    def __init__(self):
        self.position: int = 0   # + long, - short
        self.entry_price: Optional[float] = None
        self.tp: Optional[float] = None
        self.sl: Optional[float] = None

    def buy(self, price: float, qty: int):
        if self.position != 0:
            print(">> Pozisyon açık, yeni AL iptal.")
            return
        self.position = qty
        self.entry_price = price
        self.tp = round(price * (1 + TP_PCT), 2)
        self.sl = round(price * (1 - SL_PCT), 2)
        print(f">> LONG AL {qty} @ {price:.2f} | TP={self.tp} | SL={self.sl}")

    def sell(self, price: float, qty: int):
        if self.position != 0:
            print(">> Pozisyon açık, yeni SAT iptal.")
            return
        self.position = -qty
        self.entry_price = price
        self.tp = round(price * (1 - TP_PCT), 2)
        self.sl = round(price * (1 + SL_PCT), 2)
        print(f">> SHORT SAT {qty} @ {price:.2f} | TP={self.tp} | SL={self.sl}")

    def manage_position(self, last_price: float):
        if self.position == 0:
            return
        # Long pozisyon
        if self.position > 0:
            if self.tp and last_price >= self.tp:
                print(f">> TAKE PROFIT LONG @ {last_price:.2f} ✅")
                self.reset()
            elif self.sl and last_price <= self.sl:
                print(f">> STOP LOSS LONG @ {last_price:.2f} ❌")
                self.reset()
        # Short pozisyon
        elif self.position < 0:
            if self.tp and last_price <= self.tp:
                print(f">> TAKE PROFIT SHORT @ {last_price:.2f} ✅")
                self.reset()
            elif self.sl and last_price >= self.sl:
                print(f">> STOP LOSS SHORT @ {last_price:.2f} ❌")
                self.reset()

    def status(self, last_price: float):
        if self.position == 0 or self.entry_price is None:
            print(f"[Pozisyon=0] Last={last_price:.2f}")
            return
        if self.position > 0:
            unrealized = (last_price - self.entry_price) * self.position
            poz = "LONG"
        else:
            unrealized = (self.entry_price - last_price) * (-self.position)
            poz = "SHORT"
        print(f"[Pozisyon={poz} {abs(self.position)} @ {self.entry_price:.2f}] "
              f"Last={last_price:.2f} | UnrealizedPnL={unrealized:.2f} "
              f"| TP={self.tp} | SL={self.sl}")

    def reset(self):
        self.position = 0
        self.entry_price = None
        self.tp = None
        self.sl = None

# ---------------- Çalıştırıcı Döngü -------------
def run():
    broker = PaperBroker()
    last_ts: Optional[pd.Timestamp] = None
    print("Bot başladı… (Ctrl+C ile çık)")

    while True:
        try:
            df = fetch_data(SYMBOL, LOOKBACK, INTERVAL)
            close = scalar(df["Close"].iloc[-1])
            sma = compute_sma(df, SMA_WINDOW)
            ts = df.index[-1]

            prev_close = scalar(df["Close"].iloc[-2]) if len(df) > 1 else close
            prev_sma = compute_sma(df.iloc[:-1], SMA_WINDOW) if len(df) > SMA_WINDOW else sma

            new_bar = (last_ts is None) or (ts != last_ts)
            if new_bar:
                print(f"\n[{ts}] Close={close:.2f} | SMA({SMA_WINDOW})={sma:.2f}")
                last_ts = ts

                # Alt -> Üst kırılım → LONG
                cross_up = (prev_close + EPS) < prev_sma and (close - EPS) > sma
                # Üst -> Alt kırılım → SHORT
                cross_down = (prev_close - EPS) > prev_sma and (close + EPS) < sma

                if cross_up and broker.position == 0:
                    broker.buy(close, QTY)
                elif cross_down and broker.position == 0:
                    broker.sell(close, QTY)

                broker.status(close)

            broker.manage_position(close)

        except KeyboardInterrupt:
            print("\nÇıkılıyor…")
            break
        except Exception as e:
            print("Hata:", e)

        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()

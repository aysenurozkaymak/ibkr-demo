# paper_sma_bot.py
# İlk demo: AAPL 1dk veriyi çek, SMA(10) hesapla, basit sinyal yazdır.

from datetime import datetime
try:
    import yfinance as yf
    import pandas as pd
except ImportError as e:
    print("Gerekli paketler yok. Terminalde şunu çalıştırın: pip install yfinance pandas")
    raise

SYMBOL = "AAPL"
INTERVAL = "1m"   # 1 dakikalık bar
LOOKBACK = "1d"   # 1 gün veri
SMA_WINDOW = 10

def fetch_df(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df is None or df.empty:
        raise RuntimeError("Veri alınamadı (Yahoo limit olabilir). Biraz sonra tekrar deneyin.")
    df.index = df.index.tz_localize(None)
    return df

def main():
    df = fetch_df(SYMBOL, LOOKBACK, INTERVAL)
    close = df["Close"].iloc[-1].item()   # tek elemana direkt float verir
    sma = df["Close"].tail(SMA_WINDOW).mean().item() if len(df) >= SMA_WINDOW else float("nan")

    ts = df.index[-1]

    print(f"[{ts}] {SYMBOL} Close={close:.2f} | SMA({SMA_WINDOW})={sma:.2f}")
    if pd.notna(sma):
        if close > sma:
            print("Sinyal: CLOSE > SMA → (Demo) AL yönünde sinyal.")
        elif close < sma:
            print("Sinyal: CLOSE < SMA → (Demo) SAT yönünde sinyal.")
        else:
            print("Sinyal: Nötr.")
    else:
        print(f"Yeterli bar yok (en az {SMA_WINDOW} lazım).")


if __name__ == "__main__":
    print("Demo çalışıyor…")
    main()

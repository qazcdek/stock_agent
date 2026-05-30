import FinanceDataReader as fdr
import asyncio

sp500 = fdr.StockListing('S&P500')
print(f"S&P 500 count: {len(sp500)}")

krx = fdr.StockListing('KOSPI')
print(f"KOSPI count: {len(krx)}")
if 'Marcap' in krx.columns:
    krx_top100 = krx.sort_values('Marcap', ascending=False).head(100)
    print(f"KOSPI Top 5: {krx_top100['Code'].tolist()[:5]}")

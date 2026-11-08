import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

OUT = "site/data.json"
UA = "QUANTEX-Free-Intelligence/1.0 (GitHub Actions)"
TIMEOUT = 20

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))

def safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)[:240]}

def gdelt_news():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=48)
    query = '(bitcoin OR cryptocurrency OR crypto OR ethereum OR Federal Reserve OR inflation OR interest rates)'
    params = urllib.parse.urlencode({
        "query": query, "mode": "ArtList", "format": "json",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
        "maxrecords": 50, "sort": "DateDesc"
    })
    data = get_json("https://api.gdeltproject.org/api/v2/doc/doc?" + params)
    articles = data.get("articles", [])
    return {
        "status": "connected",
        "window_hours": 48,
        "count": len(articles),
        "items": [{
            "title": a.get("title"), "url": a.get("url"),
            "source": a.get("domain"), "published": a.get("seendate"),
            "language": a.get("language")
        } for a in articles[:50]]
    }

def binance_market():
    base = "https://fapi.binance.com"
    symbol = "BTCUSDT"
    oi = get_json(f"{base}/fapi/v1/openInterest?symbol={symbol}")
    funding = get_json(f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit=1")
    ticker = get_json(f"{base}/fapi/v1/ticker/24hr?symbol={symbol}")
    return {
        "status": "connected", "symbol": symbol,
        "open_interest_contracts": oi.get("openInterest"),
        "open_interest_time": oi.get("time"),
        "latest_funding_rate": funding[-1].get("fundingRate") if funding else None,
        "funding_time": funding[-1].get("fundingTime") if funding else None,
        "price_change_percent_24h": ticker.get("priceChangePercent"),
        "quote_volume_24h": ticker.get("quoteVolume"),
        "source": "Binance USD-M public market data"
    }

def btc_large_transactions():
    # Public mempool.space API: scan recent confirmed blocks.
    # Large-value transfers are NOT automatically whale buys/sells.
    height = get_json("https://mempool.space/api/blocks/tip/height")
    blocks = get_json(f"https://mempool.space/api/v1/blocks/{height}")
    found = []
    cutoff = 100 * 100_000_000  # 100 BTC in satoshis
    for block in blocks[:3]:
        txs = get_json(f"https://mempool.space/api/block/{block['id']}/txs/0")
        for tx in txs:
            vin = sum((i.get("prevout") or {}).get("value", 0) for i in tx.get("vin", []))
            vout = sum(o.get("value", 0) for o in tx.get("vout", []))
            amount = max(vin, vout)
            if amount >= cutoff:
                found.append({
                    "txid": tx.get("txid"),
                    "block_time": block.get("timestamp"),
                    "approx_btc_value": round(amount / 100_000_000, 4),
                    "classification": "large_onchain_transfer_unlabeled",
                    "direction": "unknown",
                    "explorer": "https://mempool.space/tx/" + str(tx.get("txid"))
                })
    return {
        "status": "connected", "network": "Bitcoin",
        "scanned_blocks": len(blocks[:3]), "large_transfers": found[:30],
        "warning": "Large transfers are not proof of whale accumulation, exchange inflow, or selling. Wallet ownership and destination labels are unknown."
    }

def main():
    payload = {
        "product": "QUANTEX Free Intelligence Engine",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": 48,
        "disclaimer": "Informational data only; not a trading signal or investment advice.",
        "news_48h": safe(gdelt_news),
        "btc_onchain_large_transfers": safe(btc_large_transactions),
        "btc_derivatives_market": safe(binance_market),
        "sources": {
            "news": "GDELT DOC API",
            "bitcoin_onchain": "mempool.space public API",
            "derivatives": "Binance USD-M public market-data API"
        }
    }
    os.makedirs("site", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("Wrote", OUT)

if __name__ == "__main__":
    main()

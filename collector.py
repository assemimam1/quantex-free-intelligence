import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

OUT = "site/data.json"
UA = "QUANTEX-Free-Intelligence/1.1"
TIMEOUT = 20

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
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
    query = '(bitcoin OR BTC OR ethereum OR ETH OR cryptocurrency OR crypto OR "digital assets")'
    params = urllib.parse.urlencode({
        "query": query, "mode": "ArtList", "format": "json",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
        "maxrecords": 50, "sort": "DateDesc"
    })
    articles = get_json("https://api.gdeltproject.org/api/v2/doc/doc?" + params).get("articles", [])
    terms = ("bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "digital asset")
    articles = [a for a in articles if any(t in (a.get("title") or "").lower() for t in terms)]
    return {
        "status": "connected", "window_hours": 48, "count": len(articles),
        "items": [{
            "title": a.get("title"), "url": a.get("url"),
            "source": a.get("domain"), "published": a.get("seendate"),
            "language": a.get("language")
        } for a in articles[:50]],
        "filter": "Crypto-related headline keyword filter"
    }

def bybit_market():
    symbol = "BTCUSDT"
    url = "https://api.bybit.com/v5/market/tickers?" + urllib.parse.urlencode({
        "category": "linear", "symbol": symbol
    })
    data = get_json(url)
    if data.get("retCode") != 0:
        raise RuntimeError("Bybit API: " + str(data.get("retMsg", "request failed")))
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        raise RuntimeError("Bybit returned no BTCUSDT linear ticker")
    t = rows[0]
    missing = [k for k in ("openInterest", "fundingRate", "turnover24h") if t.get(k) in (None, "")]
    if missing:
        raise RuntimeError("Bybit ticker missing fields: " + ", ".join(missing))
    return {
        "status": "connected", "symbol": symbol, "instrument": "BTCUSDT linear perpetual",
        "open_interest_contracts": t.get("openInterest"), "open_interest_unit": "BTC",
        "open_interest_value_usdt": t.get("openInterestValue"),
        "latest_funding_rate": t.get("fundingRate"), "funding_time": t.get("nextFundingTime"),
        "price_change_percent_24h": str(float(t.get("price24hPcnt", "0")) * 100),
        "quote_volume_24h": t.get("turnover24h"), "base_volume_24h": t.get("volume24h"),
        "last_price": t.get("lastPrice"), "source": "Bybit V5 public market API",
        "source_endpoint": "/v5/market/tickers",
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }

def okx_market():
    base, inst = "https://www.okx.com", "BTC-USDT-SWAP"
    ticker = get_json(base + "/api/v5/market/ticker?" + urllib.parse.urlencode({"instId": inst}))
    oi = get_json(base + "/api/v5/public/open-interest?" + urllib.parse.urlencode({"instType": "SWAP", "instId": inst}))
    funding = get_json(base + "/api/v5/public/funding-rate?" + urllib.parse.urlencode({"instId": inst}))
    for name, payload in (("ticker", ticker), ("open interest", oi), ("funding rate", funding)):
        if payload.get("code") != "0":
            raise RuntimeError("OKX " + name + " API: " + str(payload.get("msg", "request failed")))
    tr, o, f = (ticker.get("data") or [{}])[0], (oi.get("data") or [{}])[0], (funding.get("data") or [{}])[0]
    if not tr or not o or not f:
        raise RuntimeError("OKX returned incomplete BTC swap market data")
    return {
        "status": "connected", "symbol": inst, "instrument": "BTC-USDT perpetual swap",
        "open_interest_contracts": o.get("oi"), "open_interest_unit": o.get("oiCcy") or "contracts (OKX-reported)",
        "open_interest_value_usdt": o.get("oiUsd"),
        "latest_funding_rate": f.get("fundingRate"), "funding_time": f.get("fundingTime"),
        "price_change_percent_24h": None, "quote_volume_24h": tr.get("volCcy24h"),
        "base_volume_24h": tr.get("vol24h"), "last_price": tr.get("last"),
        "source": "OKX V5 public market API (fallback)",
        "source_endpoint": "ticker + open-interest + funding-rate",
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }

def derivatives_market():
    errors = []
    for provider, fn in (("Bybit", bybit_market), ("OKX", okx_market)):
        try:
            result = fn()
            result["provider"] = provider
            result["fallback_used"] = provider != "Bybit"
            result["provider_errors"] = errors
            return result
        except Exception as e:
            errors.append({"provider": provider, "error": str(e)[:240]})
    return {
        "status": "unavailable", "symbol": "BTCUSDT",
        "error": "All configured public derivatives sources failed",
        "provider_errors": errors
    }

def btc_large_transactions():
    height = get_json("https://mempool.space/api/blocks/tip/height")
    blocks = get_json(f"https://mempool.space/api/v1/blocks/{height}")
    found, cutoff = [], 100 * 100_000_000
    for block in blocks[:3]:
        txs = get_json(f"https://mempool.space/api/block/{block['id']}/txs/0")
        for tx in txs:
            vin = sum((i.get("prevout") or {}).get("value", 0) for i in tx.get("vin", []))
            vout = sum(o.get("value", 0) for o in tx.get("vout", []))
            amount = max(vin, vout)
            if amount >= cutoff:
                found.append({
                    "txid": tx.get("txid"), "block_time": block.get("timestamp"),
                    "approx_btc_value": round(amount / 100_000_000, 4),
                    "classification": "large_onchain_transfer_unlabeled", "direction": "unknown",
                    "explorer": "https://mempool.space/tx/" + str(tx.get("txid"))
                })
    return {
        "status": "connected", "network": "Bitcoin", "scanned_blocks": len(blocks[:3]),
        "large_transfers": found[:30],
        "warning": "Large transfers are not proof of whale accumulation, exchange inflow, or selling. Wallet ownership and destination labels are unknown."
    }

def main():
    payload = {
        "product": "QUANTEX Free Intelligence Engine",
        "generated_at": datetime.now(timezone.utc).isoformat(), "window_hours": 48,
        "disclaimer": "Informational data only; not a trading signal or investment advice.",
        "news_48h": safe(gdelt_news),
        "btc_onchain_large_transfers": safe(btc_large_transactions),
        "btc_derivatives_market": safe(derivatives_market),
        "sources": {
            "news": "GDELT DOC API (crypto-keyword filtered)",
            "bitcoin_onchain": "mempool.space public API",
            "derivatives_primary": "Bybit V5 public market API",
            "derivatives_fallback": "OKX V5 public market API"
        }
    }
    os.makedirs("site", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("Wrote", OUT)

if __name__ == "__main__":
    main()

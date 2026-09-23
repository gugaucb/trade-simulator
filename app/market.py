import asyncio
import json
import httpx
import websockets

class BinanceMarket:
    def __init__(self, rest_url: str, ws_url: str):
        self.rest_url = rest_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/")

    async def klines(self, symbol: str, interval: str, limit: int = 300):
        url = f"{self.rest_url}/api/v3/klines"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params={"symbol": symbol.upper(), "interval": interval, "limit": limit})
            r.raise_for_status()
            return [
                {"time": int(k[0]/1000), "open": float(k[1]), "high": float(k[2]),
                 "low": float(k[3]), "close": float(k[4]), "volume": float(k[5]), "closed": True}
                for k in r.json()
            ]

    async def ticker24h(self, symbol: str):
        url = f"{self.rest_url}/api/v3/ticker/24hr"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params={"symbol": symbol.upper()})
            r.raise_for_status()
            return r.json()

    async def start(self, symbol: str, interval: str, on_kline):
        stream = f"{symbol.lower()}@kline_{interval}"
        url = f"{self.ws_url}/{stream}"
        while True:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=60) as ws:
                    async for raw in ws:
                        msg = json.loads(raw)
                        k = msg.get("k", {})
                        if not k:
                            continue
                        await on_kline({
                            "time": int(k["t"]/1000), "open": float(k["o"]), "high": float(k["h"]),
                            "low": float(k["l"]), "close": float(k["c"]), "volume": float(k["v"]),
                            "closed": bool(k["x"])
                        })
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await on_kline({"error": str(exc)})
                await asyncio.sleep(2)

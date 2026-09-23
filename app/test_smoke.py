import pandas as pd
from .indicators import enrich, latest_context

def test_indicators():
    rows=[]; price=100.0
    for i in range(100):
        price += 0.2 if i % 3 else -0.1
        rows.append({"time":i,"open":price-0.1,"high":price+0.2,"low":price-0.2,"close":price,"volume":100+i})
    ctx=latest_context(enrich(pd.DataFrame(rows)))
    assert ctx["rsi"] is not None
    assert ctx["macd"] is not None

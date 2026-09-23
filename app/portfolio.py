from dataclasses import dataclass, field, asdict

@dataclass
class Portfolio:
    initial_cash: float
    cash: float
    active_symbol: str = "BTCUSDT"
    holdings: dict[str, dict] = field(default_factory=dict)
    realized_pnl: float = 0.0
    last_prices: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
        for s in symbols:
            if s not in self.holdings:
                self.holdings[s] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": 0.0}

    def set_active_symbol(self, symbol: str):
        self.active_symbol = symbol.upper()
        if self.active_symbol not in self.holdings:
            self.holdings[self.active_symbol] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": 0.0}

    @property
    def current_position(self) -> dict:
        return self.holdings.get(self.active_symbol, {"quantity": 0.0, "avg_entry": 0.0, "last_price": 0.0})

    @property
    def quantity(self) -> float:
        return self.current_position["quantity"]

    @quantity.setter
    def quantity(self, val: float):
        if self.active_symbol not in self.holdings:
            self.holdings[self.active_symbol] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": 0.0}
        self.holdings[self.active_symbol]["quantity"] = val

    @property
    def avg_entry(self) -> float:
        return self.current_position["avg_entry"]

    @avg_entry.setter
    def avg_entry(self, val: float):
        if self.active_symbol not in self.holdings:
            self.holdings[self.active_symbol] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": 0.0}
        self.holdings[self.active_symbol]["avg_entry"] = val

    @property
    def last_price(self) -> float:
        return self.current_position["last_price"]

    @last_price.setter
    def last_price(self, val: float):
        if self.active_symbol not in self.holdings:
            self.holdings[self.active_symbol] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": val}
        self.holdings[self.active_symbol]["last_price"] = val

    @property
    def unrealized_pnl(self) -> float:
        total = 0.0
        for s, h in self.holdings.items():
            qty = h["quantity"]
            lp = h["last_price"]
            if qty > 0 and lp > 0:
                total += (lp - h["avg_entry"]) * qty
        return total

    @property
    def position_equity(self) -> float:
        total = 0.0
        for s, h in self.holdings.items():
            total += h["quantity"] * h["last_price"]
        return total

    @property
    def equity(self) -> float:
        return self.cash + self.position_equity

    @property
    def pnl(self) -> float:
        return self.equity - self.initial_cash

    @property
    def pnl_pct(self) -> float:
        return self.pnl / self.initial_cash * 100 if self.initial_cash else 0.0

    def mark(self, price: float, symbol: str | None = None):
        sym = (symbol or self.active_symbol).upper()
        if sym not in self.holdings:
            self.holdings[sym] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": price}
        else:
            self.holdings[sym]["last_price"] = price
        self.last_prices[sym] = price

    def buy(self, price: float, fraction: float = 0.25, symbol: str | None = None) -> float | None:
        if self.cash <= 0 or price <= 0: return None
        sym = (symbol or self.active_symbol).upper()
        if sym not in self.holdings:
            self.holdings[sym] = {"quantity": 0.0, "avg_entry": 0.0, "last_price": price}

        spend = self.cash * max(0.0, min(1.0, fraction))
        if spend <= 0: return None
        qty = spend / price
        pos = self.holdings[sym]
        old_cost = pos["avg_entry"] * pos["quantity"]
        pos["quantity"] += qty
        pos["avg_entry"] = (old_cost + spend) / pos["quantity"]
        pos["last_price"] = price
        self.cash -= spend
        return qty

    def sell(self, price: float, fraction: float = 1.0, symbol: str | None = None) -> dict | None:
        sym = (symbol or self.active_symbol).upper()
        pos = self.holdings.get(sym)
        if not pos or pos["quantity"] <= 0 or price <= 0: return None

        qty = pos["quantity"] * max(0.0, min(1.0, fraction))
        proceeds = qty * price
        pnl = (price - pos["avg_entry"]) * qty
        pos["quantity"] -= qty
        self.cash += proceeds
        self.realized_pnl += pnl
        if pos["quantity"] <= 1e-12:
            pos["quantity"] = 0.0
            pos["avg_entry"] = 0.0
        pos["last_price"] = price
        return {"quantity": qty, "realized_pnl": pnl}

    def snapshot(self):
        curr = self.current_position
        active_unrealized = (curr["last_price"] - curr["avg_entry"]) * curr["quantity"] if curr["quantity"] > 0 else 0.0
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "active_symbol": self.active_symbol,
            "quantity": curr["quantity"],
            "avg_entry": curr["avg_entry"],
            "last_price": curr["last_price"],
            "realized_pnl": self.realized_pnl,
            "equity": self.equity,
            "unrealized_pnl": self.unrealized_pnl,
            "active_unrealized_pnl": active_unrealized,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "holdings": self.holdings
        }

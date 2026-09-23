from dataclasses import dataclass, asdict

@dataclass
class Portfolio:
    initial_cash: float
    cash: float
    quantity: float = 0.0
    avg_entry: float = 0.0
    realized_pnl: float = 0.0
    last_price: float = 0.0

    @property
    def equity(self): return self.cash + self.quantity * self.last_price
    @property
    def unrealized_pnl(self):
        return (self.last_price - self.avg_entry) * self.quantity if self.quantity > 0 else 0.0
    @property
    def pnl(self): return self.equity - self.initial_cash
    @property
    def pnl_pct(self): return self.pnl / self.initial_cash * 100 if self.initial_cash else 0.0

    def mark(self, price): self.last_price = price

    def buy(self, price, fraction=0.25):
        if self.cash <= 0: return None
        spend = self.cash * max(0.0, min(1.0, fraction))
        qty = spend / price
        old_cost = self.avg_entry * self.quantity
        self.quantity += qty
        self.avg_entry = (old_cost + spend) / self.quantity
        self.cash -= spend
        return qty

    def sell(self, price, fraction=1.0):
        if self.quantity <= 0: return None
        qty = self.quantity * max(0.0, min(1.0, fraction))
        proceeds = qty * price
        pnl = (price - self.avg_entry) * qty
        self.quantity -= qty
        self.cash += proceeds
        self.realized_pnl += pnl
        if self.quantity <= 1e-12:
            self.quantity = 0.0
            self.avg_entry = 0.0
        return {"quantity": qty, "realized_pnl": pnl}

    def snapshot(self):
        return {**asdict(self), "equity":self.equity, "unrealized_pnl":self.unrealized_pnl,
                "pnl":self.pnl, "pnl_pct":self.pnl_pct}

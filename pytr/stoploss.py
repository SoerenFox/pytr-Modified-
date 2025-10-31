from pytr.portfolio import Portfolio
from pytr.utils import get_logger

class StopLossUpdater:
    def __init__(self, tr):
        self.tr = tr
        self.log = get_logger(__name__)

    def update(self, percent_diff, expiry, expiry_date):
        """Delete existing stop losses and create new ones by default 5% below current prices."""
        self.log.info("Fetching existing stop-market sell orders...")
        orders = self.tr.blocking_order_overview().get("orders", [])
        deleted = 0

        # Remove existing stop-market sell orders
        for order in orders:
            if order["mode"] == "stopMarket" and order["type"] == "sell":
                self.tr.blocking_cancel_order(order["id"])
                deleted += 1
        self.log.info(f"Deleted {deleted} old stop-market orders.")

        # Renew stop losses for each portfolio position
        p = Portfolio(self.tr).portfolioData()
        created = 0
        for pos in p:
            amount = int(float(pos["netSize"]))
            if amount < 1:
                continue

            price = round(float(pos["netValue"]) / float(pos["netSize"]) * (1 - percent_diff), 2)

            self.tr.blocking_stop_market_order(
                pos["instrumentId"],
                pos["exchangeIds"][0],
                "sell",
                amount,
                price,
                expiry,
                expiry_date
            )
            created += 1
            self.log.info(f"Set stop loss for {pos['name']} ({pos['instrumentId']}): {amount} @ {price}")

        self.log.info(f"Created {created} new stop losses.")

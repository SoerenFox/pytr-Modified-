from pytr.utils import get_logger

class OrderOverview:
    def __init__(self, tr):
        self.tr = tr
        self.log = get_logger(__name__)

    def get(self):
        """Displaying all active orders."""
        self.log.info("Fetching order overview...")
        orders = self.tr.blocking_order_overview()

        for order in orders["orders"]:
            if order["status"] == "active":
                print("ID:\t\t", order["id"])
                print("ISIN:\t\t", order["instrumentId"])
                print("Name:\t\t", order["instrumentName"])
                print(f"Expiry:\n- Type:\t\t{order['expiry']['type']}" + (f"\n- Date:\t\t{order['expiry']['value']}" if order['expiry']['value'] else ""))
                print("Exchange ID:\t", order["exchangeId"])
                print("Mode:\t\t", order["mode"])
                print("Type:\t\t", order["type"])
                print("Size:\t\t", order["size"])
                print("Stop:\t\t", order["stop"])
                print()

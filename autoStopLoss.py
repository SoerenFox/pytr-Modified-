import json
from pytr.account import login
from pytr.portfolio import Portfolio

PERCENT_DIFF = 0.05 # in decimal

tr = login()

# delete to renew stop losses
for order in tr.blocking_order_overview()["orders"]:
  if order["mode"] == "stopMarket" and order["type"] == "sell":
    # print("Deleted order:", order["id"])
    tr.blocking_cancel_order(order["id"])

# renew stop loss for each relevant position
for pos in Portfolio(tr).portfolioData():
  if int(float(pos["netSize"])) <= 0:
    continue
  res = tr.blocking_stop_market_order(
    pos["instrumentId"],
    pos["exchangeIds"][0],
    "sell",
    int(float(pos["netSize"])),
    round(pos["netValue"] / float(pos["netSize"]) * (1 - PERCENT_DIFF), 2),
    "gfd"
  )
  # print(json.dumps(res, indent=2))
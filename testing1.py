import json
from pytr.account import login
from pytr.portfolio import Portfolio


PERCENT_DIFF = 0.05 # in decimal
tr = login()

p = Portfolio(tr).portfolioData()

for pos in p:
  if int(float(pos["netSize"])) <= 0:
    continue
  print("Name:", pos["name"])
  print("ISIN:", pos["instrumentId"])
  print("Market:", pos["exchangeIds"][0])
  print("Sharecount:", pos["netSize"], "->", int(float(pos["netSize"])))
  print("Value:", pos["netValue"], "-> Value per Share:", pos["netValue"] / float(pos["netSize"]))
  print("5% lower stop loss:", round(pos["netValue"] / float(pos["netSize"]) * (1 - PERCENT_DIFF), 5))
  print()


# delete to renew stop losses
for order in tr.blocking_order_overview()["orders"]:
  if order["mode"] == "stopMarket" and order["type"] == "sell":
    print(order["id"])
    #del order w 

# renew stop loss for each relevant position
for pos in Portfolio(tr).portfolioData():
  if int(float(pos["netSize"])) <= 0:
    tr.blocking_stop_market_order(
    pos["instrumentId"],
    pos["exchangeIds"][0],
    "sell",
    int(float(pos["netSize"])),
    round(pos["netValue"] / float(pos["netSize"]) * (1 - PERCENT_DIFF), 5),
    "gfd"
  )



res = tr.blocking_stop_market_order(
  "LU1900066033",
  "LSX",
  "sell",
  1.0,
  65.0,
  "gfd"
)
print(json.dumps(res, indent=2, ensure_ascii=False))
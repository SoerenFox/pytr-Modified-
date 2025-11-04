from time import time
from datetime import date, timedelta
from pytr.utils import get_logger
from pytr.portfolio import Portfolio

class News:
    def __init__(self, tr):
        self.tr = tr
        self.log = get_logger(__name__)

    def get(self, isin):
        "Display recent news for an ISIN"
        self.log.info("Fetching ISIN news...")
        news = self.tr.blocking_news(isin)

        for article in news:
            print("Headline:\t", article["headline"])
            print("Publication:\t", date.fromtimestamp(article["createdAt"] / 1000).strftime("%A, %d. %B %Y"))
            print("URL:\t\t", article["url"])
            print("ID:\t\t", article["id"])
            print()

    def get_for_portfolio(self):
        "Display recent headlines for all portfolio instruments"
        self.log.info("Fetching portfolio data...")
        p = Portfolio(self.tr).portfolio_data()

        self.log.info(f"Fetching {len(p)} instrument news...")
        for pos in p:
            news = self.tr.blocking_news(pos["instrumentId"])
            if not news:
                continue
            sent = False
            for article in news:
                if (int(time()) - article["createdAt"] / 1000 > timedelta(days=14).total_seconds()):
                    continue
                if not sent:
                    print(f"News for {pos["name"]}.")
                    sent = True
                print("\tHeadline:\t", article["headline"])
                print("\tPublication:\t", date.fromtimestamp(article["createdAt"] / 1000).strftime("%A, %d. %B %Y"))
                print("\tURL:\t\t", article["url"])
                print()

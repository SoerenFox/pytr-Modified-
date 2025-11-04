from datetime import date
from pytr.utils import get_logger

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

    
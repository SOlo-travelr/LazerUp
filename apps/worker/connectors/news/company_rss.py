"""Company/startup-focused RSS connector for battery commercialization signals."""

from __future__ import annotations

from connectors.news.rss import RSSConnector

COMPANY_FEEDS = [
    "https://www.electrive.com/feed/",
    "https://insideevs.com/feed/",
    "https://www.batterytechonline.com/feed/",
    "https://www.batterycompanies.com/feed/",
]


class CompanyRSSConnector(RSSConnector):
    name = "company_rss"

    def __init__(self) -> None:
        super().__init__(feeds=COMPANY_FEEDS)

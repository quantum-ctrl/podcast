"""Assign sortable RSS dates to Zhuoke episodes and list newest first."""

import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path


def sort_feed(feed):
    # Use a fixed day per episode number so adding an episode keeps existing dates.
    base_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items_by_number = defaultdict(list)
    items = list(re.finditer(r"(?ms)^<item>\n.*?^</item>\n", feed))
    if not items:
        return feed

    for item in items:
        title = re.search(r"<title>(.*?)</title>", item[0])[1]
        prefix = re.match(r"[0-9]+", title)
        number = int(prefix[0]) if prefix else -1
        items_by_number[number].append((title, item[0]))

    sorted_items = []
    for number in sorted(items_by_number, reverse=True):
        # Same-number episodes use title order, with distinct seconds for clients.
        group = sorted(items_by_number[number])
        for index, (_, item) in enumerate(group):
            date = base_date + timedelta(days=number, seconds=len(group) - 1 - index)
            pub_date = f"<pubDate>{format_datetime(date)}</pubDate>"
            sorted_items.append(re.sub(r"<pubDate>[^<]*</pubDate>", pub_date, item, count=1))

    return feed[:items[0].start()] + "".join(sorted_items) + feed[items[-1].end():]


if __name__ == "__main__":
    path = Path(sys.argv[1])
    path.write_text(sort_feed(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")

import feedparser
from datetime import datetime
#TODO: check if feedparser is installed

__all__ = ['scmp']

url = "http://www.scmp.com/rss/91/feed"  #all
#url = "http://www.scmp.com/rss/2/feed"   #hk

class scmp(object):

    sleep_time = 60
    amount = 5
    msgs = []
    feeds = []
    lastpublished = None
    notified_amount = 0
    last_feeds = None

    def prepare(self):
        last_feeds = self.last_feeds
        now = datetime.now()
        if not last_feeds or (now - last_feeds).seconds > 59:
            self.last_feeds = now
            self.get_feeds()

    def get(self):
        while len(self.msgs): yield self.msgs.pop(0)

    def task(self, task):
        msgs = self.msgs
        feeds = self.feeds

        task = task.split()
        if task[0]=='empty':
            self.feeds[:] = []
            self.notified_amount = 0
        if task[0]=='amount': self.msgs_left()
        if task[0]=='get':
            l = len(feeds)
            r = l if l<self.amount else self.amount
            for x in range(r):
                entry = feeds.pop(0)
                msgs.append('-'*10+entry.published+'-'*10)
                msgs.append(entry.title)
                msgs.append('-'*50)
                msgs.append(entry.summary)
                msgs.append('=> '+entry.link)
                msgs.append('-'*50)
            self.msgs_left()

    def msgs_left(self):
        l = len(self.feeds)
        if l:
            self.notified_amount = l
            self.msgs.append('SCMP messages left: '+str(l))

    def get_feeds(self):
        amount = self.notified_amount
        NewsFeed = feedparser.parse(url)

        NewFeed = sorted(NewsFeed['entries'], key=lambda k: k['published_parsed'], reverse=True)
        feeds = []
        for entry in NewFeed:
            if self.lastpublished == (entry.published_parsed, entry.title[:20]): break
            feeds.append(entry)
        if feeds:
            feeds = sorted(feeds, key=lambda k: k['published_parsed'])
            self.lastpublished = (feeds[-1:][0]['published_parsed'], feeds[-1:][0]['title'][:20])
            self.feeds+=feeds
            if len(self.feeds) + 10 > amount: self.msgs_left()

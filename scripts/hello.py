from time import sleep

__all__ = ['hello']

class hello(object):

    sleep_time = 2
    msgs = []

    def prepare(self):
        self.msgs.append('hello')

    def get(self):
        while len(self.msgs): yield self.msgs.pop(0)

    def task(self, task):
        self.msgs.append(task)

    def sleep(self):
        sleep(self.sleep_time)

""" ircbot """
import sys
import os
import errno
import signal
import socket
import threading
import importlib

import time

__all__ = ['Ircbot']

class Ircthread(threading.Thread):
    """ Ircthread """

    tasks = []

    def __init__(self, bot, script):
        threading.Thread.__init__(self)
        bot.privmsg('loading script ' + script)
        self.bot = bot
        self.script = script

        try:
            reload = False
            if 'scripts.'+script in sys.modules.keys(): reload=True
            self.module = importlib.import_module('scripts.'+script)
            if reload: self.module = importlib.reload(self.module)
            self.mod = getattr(self.module, script)()
        except:
            if __debug__: bot.l.log_exception(script)
            self.mod = None

    def run(self):
        mod = self.mod
        if not mod: return
        bot = self.bot
        privmsg = bot.privmsg
        script = self.script
        threads = bot.threads
        task = mod.task if 'task' in dir(mod) else None
        tasks = self.tasks
        prepare = mod.prepare if 'prepare' in dir(mod) else None
        sleep = mod.sleep if 'sleep' in dir(mod) else None
        get = mod.get if 'get' in dir(mod) else None

        while script in threads.keys() and not bot.exit:
            try:
                while task and len(tasks): task(tasks.pop(0))
                if prepare: mod.prepare()
                if get and mod.msgs:
                    for msg in get(): privmsg(msg)
                sleep() if sleep else time.sleep(0.5)
            except:
                privmsg(script + ' crashed')
                bot.threads.pop(script)
                if __debug__: bot.l.log_exception(script)
        privmsg('unloading script ' + script)
        if script in threads.keys(): threads.pop(script)


class Ircbot(object):
    """ Ircbot """
    params = {}
    threads = {}
    no_irc = False
    exit = False
    log = False
    msg_log = None

    def __init__(self, params):
        """ constructor """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #load config
        for l in params:
            p = l.strip().split('=')
            if p[0]=='adminnames': self.params[p[0]] = p[1].split(',')
            else: self.params[p[0]] = p[1]

        if __debug__:
            self.l = Log('Ircbot debug')
            self.l.log('debugging mode on')
            self.l.log(self.params)

    def socket_error(self, e):
        """ handle socket.error exceptions """
        if e.errno == errno.ECONNREFUSED:
            print("can't connect to server " + self.params['server'])
        elif e.errno == errno.EINTR:
            print('exit requested')
            exit(0)
        #TODO: BrokenPipeError: [Errno 32] Broken pipe
        else: raise
        exit(1)

    def connect(self):
        """ connect to server, set params and got to channel """
        sock = self.sock
        params = self.params
        send = self.send

        try: sock.connect((self.params['server'], 6667))
        except socket.error as e: self.socket_error(e)

        botnick = params['botnick']
        send(' '.join(['USER', *([botnick]*4) ])) # USER botnick botnick botnick botnick
        send(' '.join(['NICK', botnick]))
        send(' '.join(['JOIN', params['channel'] ]))

        msg = ''
        #This message indicates we have successfully joined the channel.
        while msg.find('End of /NAMES list.') == -1 and not self.no_irc:
            try: msg = sock.recv(2048).decode('utf-8').strip()
            except socket.error as e: self.socket_error(e)
            except socket.timeout: self.l.log('timeout')
            if __debug__: self.l.log(msg)
        self.privmsg("hello, i'm " + botnick)

    def send(self, cmd):
        """ send cmd through socket """
        cmd = cmd + '\n'
        if __debug__: self.l.log(cmd.strip())
        try: self.sock.send(cmd.encode('utf-8'))
        except socket.error as e: self.socket_error(e)

    def privmsg(self, msg, target=None):
        if not target: target = self.params['channel']
        self.send('PRIVMSG ' + target + ' :' + msg)

    def split_privmsg(self, ircmsg):
        if self.no_irc: return 'debugger', ircmsg
        name = ircmsg.split('!',1)[0][1:]
        msg = ircmsg.split('PRIVMSG',1)[1].split(':',1)[1]
        return name, msg

    def loopmsgs(self):
        sock = self.sock
        params = self.params
        send = self.send
        split_privmsg = self.split_privmsg

        self.sock.settimeout(2)

        while not self.exit:
            try: msg = sock.recv(2048).decode('utf-8').strip()
            except socket.timeout: continue
            except socket.error as e: self.socket_error(e)
            if __debug__: self.l.log(msg)
            if self.log: self.msg_log.log(msg)
            if not msg: exit(1)
            if msg.find('PRIVMSG') != -1 or self.no_irc:
                name, cmd = split_privmsg(msg)
                if __debug__: self.l.log(self.split_privmsg(msg))

                if cmd.startswith('.'): self.cmds(name, cmd[1:])
                else: self.reactions(name, cmd)

            if msg.find('PING :') != -1: send('PONG :YohBroh') #staying alive

    def valid_script(self, msg):
        cmd = msg[0]
        if len(msg)<2:
            self.privmsg(cmd + ' what?')
            return False
        script = msg[1]
        if script in self.threads.keys(): return True          #already checked
        if not os.path.isfile('./scripts/' + script + '.py'):
            self.privmsg('script ' + script + ' not existing')
            return False
        return True

    def cmds(self, name, line):
        params = self.params
        send = self.send
        privmsg = self.privmsg

        #admins
        if not name.lower() in params['adminnames'] and not self.no_irc:
            send("you're not in the adminnames")
            return

        msg = line.split()
        cmd = msg[0]

        #scripts
        script_cmds = ['load', 'unload', 'tell']
        if cmd in script_cmds and self.valid_script(msg):
            script = msg[1]
            threads = self.threads
            task = ' '.join(msg[2:]) if len(msg)>2 else ''

            loaded = (script in threads.keys())

            if cmd=='load':
                if not loaded:
                    threads[script] = Ircthread(self, script)
                    threads[script].start()
                else: privmsg('script ' + script + ' already loaded')

            if cmd=='unload':
                if loaded: threads.pop(script)
                else: privmsg('script ' + script + ' not loaded')

            if cmd=='tell':
                if loaded: threads[script].tasks.append(task)
                else: privmsg('script ' + script + ' not loaded')

        #exit
        if cmd=='quit':
            privmsg('bye bye ' + name)
            self.exit = True
            cnt = 0
            while self.threads and cnt<100:
                cnt+=1
                time.sleep(0.1)
            send('QUIT')

        if cmd=='log':
            if len(msg)<2:
                self.privmsg(cmd + ' what?')
            elif msg[1]=='on' and not self.log:
                self.log = True
                if not self.msg_log:
                    self.msg_log = Log('Ircbot messages', filename='messages.log')
                self.privmsg(cmd + ' switched on')
            elif msg[1]=='on' and self.log:
                self.privmsg(cmd + ' already on')
            elif msg[1]=='off' and self.log:
                self.log = False
                self.privmsg(cmd + ' switched off')
            elif msg[1]=='off' and not self.log:
                self.privmsg(cmd + ' already off')
            else: self.privmsg(cmd + ' on/off?')

    def reactions(self, name, msg):
        params = self.params
        privmsg = self.privmsg

        if msg.lower()=='hi ' + params['botnick']:
            privmsg('hello ' + name)


class Log(object):
    """ log features """
    logger = None

    def __init__(self, name, filename='exceptions.log'):
        """ constructor """
        import logging
        import logging.handlers

        #rotating logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        if not os.path.exists('./log'): os.makedirs('./log')
        handler = logging.handlers.RotatingFileHandler(
            filename='./log/'+filename, maxBytes=10485760, backupCount=10) #10485760
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_exception(self, info=None):
        """ exception handling to logfile  """
        import sys
        import traceback

        exception = sys.exc_info()
        exc_type, exc_value, exc_traceback = exception
        logexc = '\n################ START EXCEPTION #####################\n'\
                 '#### sys.exc_info() ####\n'+str(exception)+'\n'\
                 '#### traceback.print_exception ####\n'+(''.join(traceback.format_exception(
                     exc_type, exc_value, exc_traceback)))+''\
                 '################# END EXCEPTION ######################\n'
        self.logger.error(logexc)
        if info:
            self.logger.info('\n################ START EXCEPTION INFO #####################\n'\
                ''+str(info)+'\n################# END EXCEPTION INFO ######################\n')

    def log(self, info, level=None):
        """ log info/debug/warnings """
        if level == 'debug':
            self.logger.debug(info)
        elif level == 'info':
            self.logger.info(info)
        else:
            self.logger.warning(info)


def main():
    """ main """
    l = Log('ircbot')

    def signalhandler(signum, stack):
        l.log('... exiting nicely')
        bot.cmds('local', 'quit')

    try:
        f = open('config.conf', 'r')
        bot = Ircbot(f)
        f.close()
        signal.signal(signal.SIGTERM, signalhandler)
        signal.signal(signal.SIGINT, signalhandler)

        if len(sys.argv)>1 and sys.argv[1] == 'no_irc': bot.no_irc = True
        bot.connect()
        bot.loopmsgs()
        exit(0)
    except SystemExit as e:
        exit(e.code)
#    except KeyboardInterrupt:
#        pass
    except:
        l.log_exception('ircbot')


if __name__ == "__main__":
    main()

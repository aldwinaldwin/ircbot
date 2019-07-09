""" ircbot """
import sys
import socket
import errno
import threading
import os

from time import sleep

__all__ = ['Ircbot']

#TODO: review socket.error exceptions
#TODO: study thread stopping clean
#TODO: add signal

class Ircthread(threading.Thread):
    """ Ircthread """
    def __init__(self, bot, script):
        threading.Thread.__init__(self)
        bot.send('loading script ' + script)
        self.bot = bot
        self.script = script

    def run(self):
        bot = self.bot
        privmsg = bot.privmsg
        script = self.script

        while script in bot.threads.keys():
            try:
                #privmsg('hello world from ' + script)
                sleep(5)
            except:
                privmsg(script + ' crashed')
                bot.threads.pop(script)
                if __debug__: bot.l.log_exception(script)
        privmsg('unloading script ' + script)


class Ircbot(object):
    """ Ircbot """
    params = {}
    threads = {}
    no_irc = False

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
            print("can't connect to server " + params['server'])
        elif e.errno == errno.EINTR:
            print('exit requested')
            exit(0)
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

        while True:
            try: msg = sock.recv(2048).decode('utf-8').strip()
            except socket.error as e: self.socket_error(e)
            if __debug__: self.l.log(msg)

            if not msg: exit(1)
            if msg.find('PRIVMSG') != -1 or self.no_irc:
                name, cmd = split_privmsg(msg)
                if __debug__: self.l.log(self.split_privmsg(msg))

                if cmd.startswith('.'): self.cmds(name, cmd[1:])
                else: self.reactions(name, cmd)

            if msg.find('PING :') != -1: send('PONG :YohBroh') #staying alive

    def valid_script(self, msg, cmd):
        if len(msg)<2:
            self.privmsg(cmd + ' what?')
            return False
        script = msg[1]
        if not os.path.isfile('./scripts/' + script + '.py'):
            self.privmsg('script ' + script + ' not existing')
            return False
        loaded = script in self.threads.keys()
        if cmd == 'unload' and not loaded:
            self.privmsg('script ' + script + ' not loaded')
            return False
        if cmd == 'load' and loaded:
            self.privmsg('script ' + script + ' already loaded')
            return False
        return True

    def cmds(self, name, cmd):
        params = self.params
        send = self.send
        privmsg = self.privmsg

        msg = cmd.split()

        #admins
        if not name.lower() in params['adminnames'] and not self.no_irc:
            send("you're not in the adminnames")
            return

        cmd = msg[0]
        script_cmds = ['load', 'unload']
        if cmd in script_cmds and self.valid_script(msg, cmd):
            script = msg[1]
            threads = self.threads

            if cmd == 'load':
                t = Ircthread(self, script)
                threads[script] = t
                t.start()

            if cmd=='unload':
                t = threads[script]
                threads.pop(script)
                t.join()

        if cmd==params['exitcode']:
            privmsg('bye bye ' + name)
            send('QUIT')

    def reactions(self, name, msg):
        params = self.params
        privmsg = self.privmsg

        if msg.lower()=='hi ' + params['botnick']:
            privmsg('hello ' + name)


class Log(object):
    """ log features """
    logger = None

    def __init__(self, name):
        """ constructor """
        self.set_env(name)

    def set_env(self, name, filename='exceptions.log'):
        """ set logfile parameters """
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
    l = Log('ircbot')
    try:
        f = open('config.conf', 'r')
        bot = Ircbot(f)
        f.close()
        if sys.argv[1] == 'no_irc': bot.no_irc = True
        bot.connect()
        bot.loopmsgs()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except:
        l.log_exception('ircbot')


if __name__ == "__main__":
    main()

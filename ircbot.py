""" ircbot """

__all__ = ['Ircbot']

class Ircbot(object):

    params = {}

    def __init__(self):
        """ constructor """
        import socket

        self.ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #TODO: get config load outside
        #load config
        f = open('config.conf', 'r')
        for l in f:
            p = l.strip().split('=')
            if p[0]=='adminnames': self.params[p[0]] = p[1].split(',')
            else: self.params[p[0]] = p[1]

        if __debug__:
            print('debugging')
            self.l = Log('Ircbot debug')
            self.l.log(self.params)

    def connect(self):
        ircsock = self.ircsock
        params = self.params
        send = self.send

        #TODO: socket.timeout exception
        ircsock.connect((self.params['server'], 6667))
        botnick = params['botnick']
        channel = params['channel']
        botnicks = [botnick]*4
        send(' '.join(['USER', *botnicks]))
        send(' '.join(['NICK', botnick]))
        send(' '.join(['JOIN', channel]))
        ircmsg = ''
        #This message indicates we have successfully joined the channel.
        while ircmsg.find('End of /NAMES list.') == -1:
            #TODO catch signal
            ircmsg = ircsock.recv(2048).decode('utf-8').strip()
            if __debug__: self.l.log(ircmsg)
            #TODO: raise exception or how check if connection is alive? reconnect?
            if not ircmsg: exit(1)


    def send(self, cmd):
        cmd = cmd + '\n'
        if __debug__: self.l.log(cmd.strip())
        #TODO: capture exception on fail
        self.ircsock.send(cmd.encode('utf-8'))

    def privmsg(self, msg, target=None):
        if not target: target = self.params['channel']
        self.send('PRIVMSG ' + target + ' :' + msg)

    def split_privmsg(self, ircmsg):
        name = ircmsg.split('!',1)[0][1:]
        msg = ircmsg.split('PRIVMSG',1)[1].split(':',1)[1]
        return name, msg

    def loopmsgs(self):
        ircsock = self.ircsock
        params = self.params
        send = self.send
        privmsg = self.privmsg
        split_privmsg = self.split_privmsg

        while True:
            #TODO catch signal
            ircmsg = ircsock.recv(2048).decode('utf-8').strip()
            if __debug__: self.l.log(ircmsg)

            #TODO: raise exception or how check if connection is alive? reconnect?
            if not ircmsg: exit(1)

            if ircmsg.find('PRIVMSG') != -1:
                name, msg = split_privmsg(ircmsg)
                if __debug__: self.l.log(self.split_privmsg(ircmsg))

                if msg.lower()=='hi ' + params['botnick']:
                    privmsg('hello '+name)

                #TODO FIX ... not working
                if name.lower() in params['adminnames']:
                    if msg==params['exitcode']:
                        sprivmsg('bye bye '+name)
                        send('QUIT')

            #keep connection alive   TODO: pingis necessary?
            if ircmsg.find('PING :') != -1:
                send('PONG :pingis')


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
        #TODO: create dir log if not exist
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
        bot = Ircbot()
        bot.connect()
        bot.loopmsgs()
    except:
        l.log_exception('ircbot')


if __name__ == "__main__":
    main()

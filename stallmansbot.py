import re
import socket
from collections import defaultdict
from contextlib import suppress
from io import StringIO


class Client:
    ADDR = ("irc.twitch.tv", 6667)
    _callbacks = defaultdict(list)

    def __init__(self, nick, password):
        self.con = socket.socket()
        self.con.connect(self.ADDR)

        self.push_cmd("pass", password)
        self.push_cmd("nick", nick)

        self.mode = "run"

    @classmethod
    def register(cls, *patterns):
        def wrapper(func):
            cls._callbacks[patterns].append(func)
            return func

        return wrapper

    def connect(self, room):
        self._room = room
        self.push_cmd("join", room)

        buffer = str()
        while self.mode != "quit":
            buffer = buffer + self.con.recv(1024).decode("UTF-8")
            _buffer = re.split(r"[~\r\n]+", buffer)
            buffer = _buffer.pop()

            for line in _buffer:
                line = line.strip().split()
                if len(line) >= 1:
                    if line[0] == "PING":
                        self.push_cmd("pong", line[1])
                    if line[1] == "PRIVMSG":
                        author, *message = line[2:]
                        message = " ".join(message)[1:]
                        author = author[1:]

                        print(f"{author}: {message}")
                        for patterns, callbacks in self._callbacks.items():
                            pass_this = True
                            matches = []

                            for pattern in patterns:
                                if pattern in message.lower():
                                    pass_this = False
                                    matches.append(pattern)

                            if pass_this:
                                continue

                            for callback in callbacks:
                                callback(self, author, message, matches)

    def push_cmd(self, cmd, value):
        request = f"{cmd.upper()} {value}\r\n"
        self.con.send(request.encode("utf8"))

    def send_message(self, message):
        self.push_cmd("privmsg", f"{self._room} :{message}")


@Client.register("nano", "linux", "emacs", "grep")
def gnu_receiver(self, author, message, matches):
    def not_generator(thing):
        return f"Not {thing}, GNU/{thing.title()}"

    if "gnu" not in message.lower():
        msg = ". ".join(not_generator(thing) for thing in matches)
        self.send_message(f"Guys, please. {msg}")


if __name__ == "__main__":
    pass

import json
import re
import shelve
import socket
from collections import defaultdict
from contextlib import suppress
from io import StringIO

with open("assets/interject.txt") as f:
    INTERJECTION_MESSAGE = f.read()


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
    def from_conf(cls, config_file):
        with open(config_file) as f:
            content = f.read()

        config = json.loads(content)
        return cls(**config)

    @classmethod
    def register(cls, *patterns):
        def wrapper(func):
            cls._callbacks[patterns].append(func)
            return func

        return wrapper

    def connect(self, room):
        if not room.startswith("#"):
            room = "#" + room
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
                        self.dispatch_message(line)

    def dispatch_message(self, line):
        author = self.obtain_author(line.pop(0))
        room, *message = line[1:]
        message = " ".join(message)[1:]

        print(f"{room}/{author}: {message}")
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
                callback(self, room, author, message, matches)

    def push_cmd(self, cmd, value):
        request = f"{cmd.upper()} {value}\r\n"
        print(request)
        self.con.send(request.encode("utf8"))

    def send_message(self, room, message):
        self.push_cmd("privmsg", f"{room} :{message}")

    def whisper(self, room, author, message):
        self.send_message(room, f"/w {author} {message}")

    @staticmethod
    def obtain_author(header):
        return header.split("!")[0][1:]


def interject(author):
    with shelve.open("not_gnu_folks") as db:
        db[author] = db.get(author, 0) + 1
        if db[author] > 25:
            db[author] = 0
            return True
    return False


@Client.register("nano", "linux", "emacs", "grep")
def gnu_receiver(self, room, author, message, matches):
    def not_generator(thing):
        return f"Not {thing}, GNU/{thing.title()}"

    if "gnu" not in message.lower():
        if interject(author):
            self.whisper(room, author, INTERJECTION_MESSAGE)
        msg = ". ".join(not_generator(thing) for thing in matches)
        self.send_message(room, f"Guys, please. {msg}")


if __name__ == "__main__":
    c = Client.from_conf("../configs/stallmansbot.json")
    c.connect("btaskaya")

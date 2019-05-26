import json
import re
import shelve
import socket
from collections import defaultdict
from contextlib import suppress
from io import StringIO
from tools import add_channel, get_channels

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

    def _connect(self, room):
        if not room.startswith("#"):
            room = "#" + room
        self.push_cmd("join", room)

    def connect(self, room):
        self._connect(room)

        buffer = str()
        try:
            while self.mode != "quit":
                with suppress(Exception):
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
        except KeyboardInterrupt:
            new_channel_to_spread_free_software_movement = input("Channel: ")
            add_channel(new_channel_to_spread_free_software_movement)
            self.connect(new_channel_to_spread_free_software_movement)

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
        self.con.send(request.encode("utf8"))

    def send_message(self, room, message):
        self.push_cmd("privmsg", f"{room} :{message}")

    def whisper(self, room, author, message):
        self.send_message(room, f"/w {author} {message}")

    @staticmethod
    def obtain_author(header):
        return header.split("!")[0][1:]


def interject(author):
    with shelve.open("db/not_gnu_folks") as db:
        db[author] = db.get(author, 0) + 1
        if db[author] > 25:
            db[author] = 0
            return True
    return False


@Client.register("nano", "linux", "emacs", "grep", "windows", "vscode", "visual studio")
def gnu_receiver(self, room, author, message, matches):
    def not_generator(thing):
        return f"Not {thing}, GNU/{thing.title()}"

    if "gnu" not in message.lower():
        if interject(author):
            self.whisper(room, author, INTERJECTION_MESSAGE)
        msg = ". ".join(not_generator(thing) for thing in matches)
        self.send_message(room, f"Guys, please. {msg}")

@Client.register("stallman", "richard stallman", "rms")
def rms_receiver(self, room, author, message, matches):
    match = matches.pop()
    if "holy" not in message.lower():
        self.send_message(room, f"Guys please. Not {match}, HOLY {match}")
    else:
        self.send_message(room, f"God may bless HOLY {match}")

if __name__ == "__main__":
    c = Client.from_conf("../configs/stallmansbot.json")
    for channel in get_channels():
        print(f"Connecting to #{channel}")
        c._connect(channel)

    print(f"Starting receiver")
    c.connect("btaskaya")

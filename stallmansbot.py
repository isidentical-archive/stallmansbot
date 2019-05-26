from __future__ import annotations

import atexit
import json
import logging
import mmap
import operator
import platform
import random
import re
import sched
import shelve
import socket
import sys
import traceback
from abc import ABC, abstractmethod
from calendar import TextCalendar
from collections import defaultdict
from configparser import ConfigParser
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from functools import partial
from io import StringIO
from typing import Any, AnyStr, Callable, Sequence, Union

from tools import add_channel, get_channels


def _get_total_lines(f):
    buffer = mmap.mmap(f.fileno(), 0)
    counter = 0
    while buffer.readline():
        counter += 1
    return counter


@atexit.register
def thanker():
    with open(f"assets/quotes.txt") as quotes:
        quotes = quotes.read().strip().split("%")

    print(random.choice(quotes))


with open("assets/interject.txt") as f:
    INTERJECTION_MESSAGE = f.read()


@dataclass(frozen=True)
class Marker:
    lhs: Markers
    operation: Callable
    rhs: Callable
    post_hooks: Sequence[Callable[[Any], Any]] = ()

    @classmethod
    def mark(cls, lhs, operation, rhs, *post_hooks):
        def wrapper(callback):
            callback._marker = cls(lhs, operation, rhs, post_hooks)
            return callback

        return wrapper


class Markers(Enum):
    ROOM = "room"
    AUTHOR = "author"
    MESSAGE = "message"

    def __str__(self):
        return self.value


class AbstractTwitchClient(ABC):
    @abstractmethod
    def push_cmd(self, cmd: str, value: str) -> None:
        """Sends an IRC message to active socket connection"""

    @abstractmethod
    def connect(self, room: str):
        """Sends `connect` command to active socket connection
        and runs until it get a `KeyboardInterrupt`"""

    @abstractmethod
    def dispatch_message(self, message: Union[AnyStr, Sequence[AnyStr]]):
        """Parses message and dispatches to specified callbacks"""


class Client(AbstractTwitchClient):
    ADDR = ("irc.twitch.tv", 6667)
    _callbacks = defaultdict(list)

    def __init__(self, nick, password):
        self.con = socket.socket()
        self.con.connect(self.ADDR)

        self.push_cmd("pass", password)
        self.push_cmd("nick", nick)

        self.mode = "run"
        self.scheduler = sched.scheduler()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    @classmethod
    def from_microsofts_ini(cls, config_file):
        cfg = ConfigParser()
        cfg.read(config_file)
        return cls(**cfg["bot"])

    @classmethod
    def from_conf(cls, config_file):
        if config_file.endswith(".ini"):
            return cls.from_microsofts_ini(config_file)

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
        self.logger.debug("Connecting to %s", room)
        if not room.startswith("#"):
            room = "#" + room
        self.push_cmd("join", room)

    def connect(self, room):
        self._connect(room)

        buffer = str()
        try:
            self.logger.info("Starting receiver")
            while self.mode != "quit":
                try:
                    buffer = buffer + self.con.recv(1024).decode("UTF-8")
                    _buffer = re.split(r"[~\r\n]+", buffer)
                    buffer = _buffer.pop()

                    for line in _buffer:
                        line = line.strip().split()
                        if len(line) >= 1:
                            if line[0] == "PING":
                                self.push_cmd("pong", line[1])
                            if line[1] == "PRIVMSG":
                                self.scheduler.enter(
                                    0.5, 1, self.dispatch_message, argument=(line,)
                                )
                    self.scheduler.run()
                except Exception as e:
                    self.logger.exception(e)

        except KeyboardInterrupt:
            new_channel_to_spread_free_software_movement = input("Channel: ")
            add_channel(new_channel_to_spread_free_software_movement)
            self.connect(new_channel_to_spread_free_software_movement)

    def dispatch_message(self, line):
        author = self.obtain_author(line.pop(0))
        room, *message = line[1:]
        message = " ".join(message)[1:]

        self.logger.debug(f"{room}/{author}: {message}")
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
                if hasattr(callback, "_marker"):
                    rhs = tuple(callback._marker.rhs())
                    lhs = locals().get(str(callback._marker.lhs))
                    marker = callback._marker.operation(rhs, lhs)
                    for post_hook in callback._marker.post_hooks:
                        marker = post_hook(marker)
                    if not marker:
                        continue

                callback(self, room, author, message, matches)

    def push_cmd(self, cmd, value):
        request = f"{cmd.upper()} {value}\r\n"
        self.con.send(request.encode("utf8"))

    def send_message(self, room, message):
        self.logger.info("Sending %s to %s", message, room)
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
@Marker.mark(
    Markers.ROOM,
    operator.contains,
    partial(get_channels, "audited_by_gnu"),
    operator.not_,
)
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
        self.send_message(room, f"Guys please. Not {match}, Holy {match}")
    else:
        self.send_message(room, f"God may bless Holy {match}")


@Client.register("total gnu domination")
def domination_receiver(self, room, *args):
    calendar = TextCalendar()
    self.send_message(room, calendar.formatmonth(2020, 1))


@Client.register("platform")
def platform_receiver(self, room, *args):
    plat = platform.system()
    self.send_message(room, f"This bot runs under GNU/{plat}")


@Client.register("source")
def source_receiver(self, room, *args):
    self.send_message(
        room,
        "The GNU/stallmansbot 's source licensed under GPLv3 and distributed through github. https://github.com/isidentical/stallmansbot",
    )


if __name__ == "__main__":
    c = Client.from_conf("../configs/stallmansbot.ini")
    for channel in get_channels():
        c._connect(channel)

    c.connect("btaskaya")

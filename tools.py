import shelve


def remove_channel(channel, remove_from="channels"):
    with shelve.open("db/communities", writeback=True) as db:
        if channel in db.get(remove_from, ()):
            db[remove_from].remove(channel)


def add_channel(channel, to="channels"):
    with shelve.open("db/communities", writeback=True) as db:
        if not db.get(to):
            db[to] = []

        if channel not in db[to]:
            db[to].append(channel)


def get_channels(get_from="channels"):
    with shelve.open("db/communities") as db:
        yield from db.get(get_from, ())

import shelve


def remove_channel(channel):
    with shelve.open("db/communities", writeback=True) as db:
        if channel in db.get("channels", ()):
            db["channels"].remove(channel)


def add_channel(channel):
    with shelve.open("db/communities", writeback=True) as db:
        if not db.get("channels"):
            db["channels"] = []

        if channel not in db["channels"]:
            db["channels"].append(channel)


def get_channels():
    with shelve.open("db/communities") as db:
        yield from db.get("channels", ())

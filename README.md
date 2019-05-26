# Stallman's Bot
Not thing, GNU/thing please. 

[Preview](https://i.imgyukle.com/2019/05/26/kTy4Kc.png)

## Handlers
Feel free to add handlers and PR.

## Tools
```
$ python -i tools.py
>>> remove_channel(<ch>)
>>> add_channel(<ch>)
>>> get_channels()
```

## GNU/Callback Language
A Microsoft's INI based language for creating callbacks

example;
```ini
[on_kde]
handles = kde
checks = name:message op:contains plasma
post_checks = op:not_
message = FYI, {matches[0]} is not the name of DE. {matches[0]} Plasma is the name of DE.
```

### How it works
It constructs Python AST under the hood. The nearest python implementation of handler upper there is;
```py
def on_kde(self, room, author, message, matches):
    if operator.not_(operator.contains(message, "plasma")):
        self.send_message(
            room,
            f"FYI, {matches[0]} is not the name of DE. {matches[0]} Plasma is the name of DE.",
        )
```

## Trolled Streams
- [AnthonyWritesCode](https://www.twitch.tv/anthonywritescode/clips?tt_content=player_profile_img) - May 25 - [Clip](https://clips.twitch.tv/CovertColdbloodedReubenCoolCat)
- [syanoks](https://www.twitch.tv/syanoks) - May 26 - [Clip](https://clips.twitch.tv/HumbleObservantAnteaterPraiseIt)

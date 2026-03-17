# Telegram-ads-bot

Telegram bot for advertising (forwarding/sending) messages to all joined groups automatically by interval.

**By: fearxaura**

### Config

Configure in `accounts.json`, supported multiple accounts in json structure

*Note*
* For forwarding message `"promo_message"` will be ignored, when is `"forward_message"` filled.
* `"time_interval"` is in minutes.
* `"reply_message"` is a feature that auto-replies when someone writes to the user-bot.

### Run
```
pip install telethon termcolor colorama
py promov2.py
```

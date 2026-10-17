# Greeks.live / Laevitas options tape collector

Read-only monitoring bridge for public Telegram channels `@greekslivenews2` and `@laevitas`.

- Sources: Telegram public posts, RSSHub fallback, optional authenticated Telegram session.
- Output: `data/latest.json` (machine-readable snapshot), `data/messages.json` (45-day deduplicated archive).
- Scheduled hourly via GitHub Actions, with a manual workflow trigger. `no new posts` does **not** mean the data provider is down.
- **Not** an official Greeks.live Option Flow API, **not** full Deribit order-flow coverage, **not** automated trade execution.

## Check operation

[Open Actions](https://github.com/edisonlauu/greeks-live-monitor/actions) and run **Collect public option-tape posts** once; then check `data/latest.json` and individual source status. The static read-only snapshot URL will be:

https://raw.githubusercontent.com/edisonlauu/greeks-live-monitor/main/data/latest.json

If publicly scraped Telegram messages are stale, you can optionally configure Telegram MTProto access via GitHub Actions secrets `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`. **Never commit these values or send the session to ChatGPT.** Prefer a dedicated, empty Telegram account. Session generation instructions will be available in `create_telegram_session.py`.

A green Action means the script ran, **not** that a fresh Greeks.live post was obtained. Verify `channels.greekslivenews2.state`, `latest_utc` and `methods` in the snapshot. This repository is public: all saved channel posts are public.

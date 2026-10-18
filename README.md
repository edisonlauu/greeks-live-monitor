# Greeks.live / Laevitas options tape collector

Read-only monitoring bridge for public Telegram channels `@greekslivenews2` and `@laevitas`.

- Sources: Telegram public posts, RSSHub fallback, optional authenticated Telegram session.
- Output: `data/latest.json` (machine-readable snapshot), `data/messages.json` (up-to-45-day deduplicated archive), `data/recent.json` (rolling 48h inbox).
- Scheduled several times hourly (best-effort; GitHub may delay jobs) via GitHub Actions, with a manual workflow trigger. `no new posts` does **not** mean the data provider is down.
- **Not** an official Greeks.live Option Flow API, **not** full Deribit order-flow coverage, **not** automated trade execution.

## Check operation

[Open Actions](https://github.com/edisonlauu/greeks-live-monitor/actions) and run **Collect public option-tape posts** once; then check `data/latest.json` and individual source status. The static read-only snapshot URL will be:

https://raw.githubusercontent.com/edisonlauu/greeks-live-monitor/main/data/latest.json

If publicly scraped Telegram messages are stale, you can optionally configure Telegram MTProto access via GitHub Actions secrets `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`. **Never commit these values or send the session to ChatGPT.** Prefer a dedicated, empty Telegram account. Session generation instructions will be available in `create_telegram_session.py`.

A green Action means the script ran, **not** that a fresh Greeks.live post was obtained. Verify `channels.greekslivenews2.state`, `latest_utc` and `methods` in the snapshot. This repository is public: all saved channel posts are public.

## Reliability and known limits

Scheduled runs are **best effort**, not an SLA: GitHub Actions can delay or skip scheduled ticks. The workflow now schedules at UTC minutes 07, 27 and 47 to improve coverage. The watcher should always read `data/recent.json` (last 48h) using the last observed message IDs, not depend only on the transient `latest.json.new_posts` array. Channel-post IDs identify Telegram **posts**, not independently verified Deribit executions. Media-only Greeks.live posts often omit strike/legs; those must remain unknown until independently confirmed.

The 45-day archive is a *retention window*, not guaranteed 45-day historical coverage. The bootstrap reads only the latest pages; long historical comparisons require explicit backfilling or external metrics. GitHub Actions being green does not prove all relevant option block trades were captured.

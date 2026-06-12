# Event Focus

Event Focus collects market news candidates and asks DeepSeek to turn them into concise decision cards.

Each card includes:

- priority and category
- bullish, bearish, neutral, or divergent impact
- affected industries, indices, or securities
- expected impact horizon
- confidence score
- verifiable watch points
- source, publication time, and source link

The service normalizes publication times, removes duplicate headlines, sorts
newer candidates first, caches each market independently, and falls back to raw
source cards when DeepSeek is unavailable.

Current markets:

- A股: `a_share`
- 港股: `hk_share`
- 美股: `us_share`

Required environment variable:

- `DEEPSEEK_API_KEY`

Optional environment variables:

- `EVENT_FOCUS_MODEL`: defaults to `deepseek-chat`
- `EVENT_FOCUS_CACHE_SECONDS`: defaults to `1800`
- `EVENT_FOCUS_MAX_CARDS`: defaults to `6`
- `EVENT_FOCUS_A_SHARE_URLS`: comma-separated RSS URLs
- `EVENT_FOCUS_HK_SHARE_URLS`: comma-separated RSS URLs
- `EVENT_FOCUS_US_SHARE_URLS`: comma-separated RSS URLs

If no source URLs are configured, the service uses Google News RSS search queries as a first-pass public source. For production use, replace these with stable licensed news, exchange公告, or vendor feeds.

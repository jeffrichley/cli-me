# Network and Performance

Rate limiting, proxy configuration, geo bypass, concurrent downloads, retry strategies, and other network tuning options.

## Rate Limiting

```bash
# Limit download speed to 500 KB/s
yt-dlp -r 500K "URL"

# Limit to 2 MB/s
yt-dlp -r 2M "URL"

# Limit to 50 KB/s (very slow, for background downloads)
yt-dlp -r 50K "URL"
```

### Throttle Detection

```bash
# Re-extract video data if speed drops below 100 KB/s
# (YouTube throttles direct downloads; this triggers a new URL)
yt-dlp --throttled-rate 100K "URL"
```

The `--throttled-rate` flag detects when YouTube (or other sites) throttle the download speed and automatically re-extracts the video URL to get an unthrottled connection.

## Proxy Configuration

```bash
# HTTP proxy
yt-dlp --proxy "http://proxy.example.com:8080" "URL"

# HTTPS proxy
yt-dlp --proxy "https://proxy.example.com:8080" "URL"

# SOCKS5 proxy
yt-dlp --proxy "socks5://127.0.0.1:1080" "URL"

# SOCKS5 with authentication
yt-dlp --proxy "socks5://user:pass@127.0.0.1:1080" "URL"

# Geo-verification proxy (only used for verification, not downloading)
yt-dlp --geo-verification-proxy "http://proxy.example.com:8080" "URL"
```

## Geo Bypass

```bash
# Enable geo bypass via X-Forwarded-For header (enabled by default)
yt-dlp --geo-bypass "URL"

# Bypass with a specific country code
yt-dlp --geo-bypass-country US "URL"
yt-dlp --geo-bypass-country GB "URL"
yt-dlp --geo-bypass-country DE "URL"

# Bypass with a specific IP block (CIDR notation)
yt-dlp --geo-bypass-ip-block "198.51.100.0/24" "URL"

# Disable geo bypass
yt-dlp --no-geo-bypass "URL"
```

The `--geo-bypass` flag works by adding an `X-Forwarded-For` header with an IP address from the target country. This only works if the server trusts this header (many don't).

## Concurrent Fragment Downloads

DASH and HLS streams are delivered in fragments. Download multiple fragments simultaneously to speed up the download.

```bash
# Download 4 fragments concurrently (default is 1)
yt-dlp -N 4 "URL"

# Download 8 fragments concurrently
yt-dlp -N 8 "URL"

# Download 16 fragments concurrently (aggressive)
yt-dlp -N 16 "URL"
```

## Retry Configuration

```bash
# Set HTTP retries (default is 10)
yt-dlp -R 5 "URL"

# Infinite retries
yt-dlp -R infinite "URL"

# Set fragment retries (for DASH/HLS, default is 10)
yt-dlp --fragment-retries 20 "URL"

# Infinite fragment retries
yt-dlp --fragment-retries infinite "URL"

# Set file access retries (default is 3)
yt-dlp --file-access-retries 5 "URL"

# Set extractor retries (default is 3)
yt-dlp --extractor-retries 5 "URL"
```

### Retry Sleep (Backoff)

```bash
# Fixed sleep between retries (seconds)
yt-dlp --retry-sleep 5 "URL"

# Linear backoff: start at 1s, increase by 1s each retry
yt-dlp --retry-sleep "linear=1" "URL"

# Linear backoff: 1s to 10s in steps of 2s
yt-dlp --retry-sleep "linear=1:10:2" "URL"

# Exponential backoff: start at 1s, double each retry
yt-dlp --retry-sleep "exp=1" "URL"

# Exponential backoff with cap at 60s
yt-dlp --retry-sleep "exp=1:60" "URL"

# Different sleep for different retry types
yt-dlp --retry-sleep "http:exp=1:30" --retry-sleep "fragment:linear=1:5" "URL"
```

Retry sleep types: `http`, `fragment`, `file_access`, `extractor`.

## IP and Protocol Options

```bash
# Force IPv4
yt-dlp -4 "URL"
yt-dlp --force-ipv4 "URL"

# Force IPv6
yt-dlp -6 "URL"
yt-dlp --force-ipv6 "URL"

# Bind to a specific local IP address
yt-dlp --source-address "192.168.1.100" "URL"

# Set socket timeout (seconds)
yt-dlp --socket-timeout 30 "URL"
```

## Client Impersonation

Impersonate a real browser's TLS fingerprint and HTTP headers to avoid bot detection.

```bash
# Impersonate Chrome
yt-dlp --impersonate chrome "URL"

# Impersonate a specific Chrome version
yt-dlp --impersonate chrome-110 "URL"

# Impersonate Chrome on Windows 10
yt-dlp --impersonate "chrome:windows-10" "URL"

# Impersonate any available client
yt-dlp --impersonate "" "URL"

# List available impersonation targets
yt-dlp --list-impersonate-targets
```

## Request Throttling

```bash
# Sleep between requests (seconds, for metadata extraction)
yt-dlp --sleep-requests 1 "URL"

# Sleep between downloads
yt-dlp --sleep-interval 5 "URL"

# Random sleep between downloads (5 to 30 seconds)
yt-dlp --sleep-interval 5 --max-sleep-interval 30 "URL"

# Sleep between subtitles
yt-dlp --sleep-subtitles 2 "URL"
```

## Custom Headers and User Agent

```bash
# Set custom User-Agent
yt-dlp --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "URL"

# Add custom HTTP headers
yt-dlp --add-headers "Referer:https://example.com" "URL"
yt-dlp --add-headers "Authorization:Bearer TOKEN" "URL"
```

## Resuming Interrupted Downloads

```bash
# Continue partially downloaded files (default behavior)
yt-dlp -c "URL"
yt-dlp --continue "URL"

# Force restart (don't continue)
yt-dlp --no-continue "URL"
```

## Performance Combo: Fast Download

```bash
# Maximum speed: concurrent fragments + no rate limit
yt-dlp -N 8 -f "bestvideo+bestaudio" "URL"

# Resilient download: retries + throttle detection
yt-dlp -N 4 -R infinite --fragment-retries infinite \
  --throttled-rate 100K --retry-sleep "exp=1:60" "URL"
```

## Gotchas and Edge Cases

- **`-r` applies per fragment when using `-N`.** With `-r 1M` and `-N 4`, total bandwidth can reach ~4 MB/s. The rate limit is per-connection, not global.
- **`--geo-bypass` only fakes the X-Forwarded-For header.** It does not route traffic through a different country. For real geo-unblocking, use `--proxy` with a proxy in the target country.
- **`-N` (concurrent fragments) only works with DASH/HLS streams.** Regular HTTP downloads are single-threaded regardless of this setting.
- **High `-N` values may trigger rate limiting.** Some CDNs will throttle or block you if you open too many concurrent connections. Start with `-N 4` and increase if stable.
- **`--throttled-rate` is YouTube-specific in practice.** While technically site-agnostic, it's primarily useful for YouTube's throttling behavior.
- **`--source-address` must be a local IP.** It binds the socket to a local network interface. It doesn't change your public IP.
- **`--impersonate` requires `curl_cffi` or `requests` with TLS fingerprint support.** Not all yt-dlp installations support this. Check with `--list-impersonate-targets`.
- **Retry sleep expressions don't use spaces.** It's `linear=1:10:2` not `linear = 1 : 10 : 2`.
- **Socket timeout affects the entire connection.** A too-low value will cause slow connections to fail. The default is usually fine.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [Rate limit with -N issue #7878](https://github.com/yt-dlp/yt-dlp/issues/7878)
- [How to use Proxies for yt-dlp - HuntAPI](https://www.huntapi.com/blog/yt-dlp-proxy-guide)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [RapidSeedbox yt-dlp Guide](https://www.rapidseedbox.com/blog/yt-dlp-complete-guide)

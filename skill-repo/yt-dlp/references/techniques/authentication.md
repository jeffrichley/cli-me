# Authentication

Access private, age-restricted, and premium content using cookies, credentials, and netrc files.

## Cookies from Browser (Recommended)

The easiest and most reliable method. yt-dlp extracts cookies directly from your browser's cookie store.

```bash
# Extract cookies from Chrome
yt-dlp --cookies-from-browser chrome "URL"

# Extract cookies from Firefox
yt-dlp --cookies-from-browser firefox "URL"

# Extract cookies from Edge
yt-dlp --cookies-from-browser edge "URL"

# Extract cookies from Brave
yt-dlp --cookies-from-browser brave "URL"

# Extract cookies from Safari (macOS only)
yt-dlp --cookies-from-browser safari "URL"

# Extract cookies from Opera
yt-dlp --cookies-from-browser opera "URL"

# Extract cookies from Vivaldi
yt-dlp --cookies-from-browser vivaldi "URL"

# Extract cookies from Chromium
yt-dlp --cookies-from-browser chromium "URL"
```

### Browser Profiles and Containers

```bash
# Use a specific browser profile
yt-dlp --cookies-from-browser "chrome:Profile 2" "URL"

# Use a specific Firefox container
yt-dlp --cookies-from-browser "firefox::Container Name" "URL"

# Specify keyring backend (Linux)
yt-dlp --cookies-from-browser "chrome+gnomekeyring" "URL"
yt-dlp --cookies-from-browser "chrome+kwallet" "URL"
```

Full syntax: `BROWSER[+KEYRING][:PROFILE][::CONTAINER]`

Supported keyring backends: `basictext`, `gnomekeyring`, `kwallet`, `kwallet5`, `kwallet6`

### Exporting Cookies to a File

```bash
# Extract from browser and save to a cookie file (without downloading)
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download "https://www.youtube.com/"

# Use the saved cookie file (doesn't need browser running)
yt-dlp --cookies cookies.txt "URL"
```

## Cookie Files (Manual)

If browser extraction doesn't work, export cookies manually using a browser extension.

```bash
# Use a Netscape-format cookie file
yt-dlp --cookies cookies.txt "URL"
```

### Cookie File Format

The file must start with a magic comment and use tab-separated fields:

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735689600	cookie_name	cookie_value
```

Fields: domain, include subdomains, path, secure, expiry, name, value.

### Cookie File Requirements

- Must start with `# HTTP Cookie File` or `# Netscape HTTP Cookie File`
- Use correct line endings for your OS (CRLF on Windows, LF on Unix) if you encounter HTTP 400 errors with cookie files
- Can be exported using browser extensions like "Get cookies.txt LOCALLY"

## Login Credentials

```bash
# Username and password (password will be prompted if omitted)
yt-dlp -u "username" -p "password" "URL"

# Username only (prompts for password)
yt-dlp -u "username" "URL"

# With two-factor authentication code
yt-dlp -u "username" -p "password" -2 "123456" "URL"

# Video-specific password (e.g., Vimeo private videos)
yt-dlp --video-password "secretpass" "URL"
```

## Netrc Authentication

The `.netrc` file stores credentials for automatic login, following the standard Unix netrc format.

```bash
# Use default ~/.netrc file
yt-dlp -n "URL"
# or
yt-dlp --netrc "URL"

# Use a custom netrc file
yt-dlp --netrc-location "/path/to/my-netrc" "URL"

# Use a command to generate netrc output
yt-dlp --netrc-cmd "pass show yt-dlp/youtube" "URL"
```

### Netrc File Format

Create `~/.netrc` (or `%USERPROFILE%/_netrc` on Windows):

```
machine youtube
login your_email@gmail.com
password your_password

machine vimeo
login your_email@example.com
password your_password

machine twitch
login your_username
password your_oauth_token
```

The `machine` field is the extractor name (use `yt-dlp --list-extractors` to find names).

## Age-Gated Content

YouTube age-restricted content requires authentication to prove the user is of age.

```bash
# Best approach: use browser cookies from a logged-in session
yt-dlp --cookies-from-browser chrome "https://www.youtube.com/watch?v=AGE_RESTRICTED_ID"

# Alternative: saved cookie file
yt-dlp --cookies cookies.txt "https://www.youtube.com/watch?v=AGE_RESTRICTED_ID"
```

There is no way to bypass age-restriction without authentication. The cookies must come from a browser session where the user is logged in to a verified (18+) Google account.

## Adobe Pass (TV Provider Auth)

```bash
# List available TV providers
yt-dlp --ap-list-mso

# Authenticate with a TV provider
yt-dlp --ap-mso "Comcast_SSO" --ap-username "user" --ap-password "pass" "URL"
```

## Client Certificates

```bash
# Use client certificate for authentication
yt-dlp --client-certificate cert.pem "URL"

# With separate key file
yt-dlp --client-certificate cert.pem --client-certificate-key key.pem "URL"

# With encrypted key
yt-dlp --client-certificate cert.pem --client-certificate-key key.pem \
  --client-certificate-password "keypass" "URL"
```

## Common Flags Reference

| Flag | Effect |
|------|--------|
| `--cookies-from-browser BROWSER` | Extract cookies from installed browser |
| `--cookies FILE` | Use Netscape-format cookie file |
| `-u` / `--username` | Login username |
| `-p` / `--password` | Login password |
| `-2` / `--twofactor` | Two-factor auth code |
| `-n` / `--netrc` | Use ~/.netrc credentials |
| `--netrc-location PATH` | Custom netrc file path |
| `--netrc-cmd CMD` | Command that outputs netrc-format credentials |
| `--video-password PASS` | Video-specific password |
| `--ap-mso MSO` | Adobe Pass TV provider |
| `--no-cookies` | Don't use any cookies |
| `--no-cookies-from-browser` | Don't extract from browser |

## Gotchas and Edge Cases

- **Browser must be closed (sometimes).** On some systems, `--cookies-from-browser` can't read the cookie database while the browser is open. Close the browser or use a cookie export extension.
- **Cookie files are security-sensitive.** A cookies.txt file is essentially a session token for your account. Never share it. Delete it when done.
- **Cookies expire.** Browser cookies have expiration dates. If downloads start failing, re-export fresh cookies.
- **`-u`/`-p` doesn't work for most sites anymore.** YouTube and many sites require OAuth or browser-based login. Direct username/password auth is limited to older sites.
- **Netrc machine names are extractor names, not domains.** Use `youtube` not `youtube.com`. Check with `yt-dlp --list-extractors`.
- **Cloudflare-protected sites may need user-agent matching.** If you get 403 errors even with cookies, pass `--user-agent` matching the browser you exported from.
- **Two-factor auth (`-2`) only works with direct login.** It doesn't apply to cookie-based auth (which already includes the authenticated session).
- **Cookies from browser may need keyring access on Linux.** If cookie extraction fails, try specifying the keyring: `--cookies-from-browser "chrome+gnomekeyring"`.
- **Refresh cookies frequently for Cloudflare-protected sites.** Challenge tokens expire quickly. Visit the target site in your browser, then immediately export/use cookies.

## Sources

- [yt-dlp GitHub README](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp man page (Arch)](https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en)
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [Authentication - yt-dlp Mintlify](https://mintlify.wiki/yt-dlp/yt-dlp/core-concepts/authentication)

# Downtime — live-service recon notes (verified by hand)

Endpoint: https://8a61c865dfab6d76.live.sbhost.io (HTTPS only, SNI/TLS-routed to the instance)
Connect over TLS with the SNI/hostname set to the endpoint (plain TCP or wrong SNI => not routed).

## Architecture
- Client -> (TLS, SNI) -> Go net/http reverse proxy ("edge") -> (HTTP/1.1, port 80) -> Apache 2.4.68 (Debian) container.
- Backend image = php:8.2.34-apache-bookworm (pinned digest). Server header leaks: `Apache/2.4.68 (Debian)`, `X-Powered-By: PHP/8.2.34`.
- Edge tells: malformed header gives Go's `400 Bad Request: invalid header name`; double Transfer-Encoding gives Go's `501 Not Implemented / Unsupported transfer encoding`. So the edge is Go's net/http.
- Host header routing: Host = endpoint -> reaches Apache. Any other Host -> Go 404 (`404 page not found`, text/plain, nosniff).
- To a fresh connection the edge speaks HTTP/2; `curl --http1.1` also works (edge downgrades).

## Backend config (given in Dockerfile)
- mpm_prefork.conf: StartServers 1, MinSpareServers 1, MaxSpareServers 1, **MaxRequestWorkers 1**, **MaxConnectionsPerChild 0** (single worker, never recycled).
- keepalive.conf: **KeepAlive Off**.
- public/index.php: ALWAYS replies 503 + `Retry-After: 3600` and prints `PHP 8.2.34`. No input, no parameters, no other dynamic code.
- flag at **/flag.txt** (COPY flag.txt /flag.txt; chmod 0444) -> world-readable but OUTSIDE the document root (/var/www/html).
- CMD: apache2 -DFOREGROUND -C 'PidFile /tmp/ap.pid' -C 'ServerName localhost'

## Observed behaviour (probes already done — don't repeat)
- GET / and /index.php -> 503 (832 bytes). GET /nope, /flag.txt, /flag, /backup.zip, /.git/HEAD, ... -> Apache's own 404 (333 bytes, iso-8859-1, leaks `Server: Apache/2.4.68 (Debian) ... Port 80`).
- /server-status and /server-info -> 403. /icons/ -> 403 but a real asset /icons/apache_pb.gif -> 200. /cgi-bin/ -> 404 (ScriptAlias NOT enabled => no CGI dir; CVE-2026-42356 needs a CGI program and does not apply here).
- Path traversal variants (/../flag.txt, %2e%2e, /icons/..%2f..%2fflag.txt, /cgi-bin/../../..) -> 404.
- TRACE -> 405. OPTIONS/PUT/POST -> 503. Duplicate Content-Length -> Go 400. Conflicting CL+TE -> edge handles, Apache mainline.

## Delta to the published 2.4.69 CVE list (all appear NOT reachable in this config)
mod_http2 (h2c not enabled on the backend), mod_dav/mod_dav_fs (DAV off), mod_rewrite/proxy_*/session/auth_digest/charset_lite/xml2enc/heartmonitor (not loaded), mod_vhost_alias/userdir (not configured), mod_ssl (TLS terminates at the edge). So the intended bug is probably NOT one of the shipped 2.4.69 CVEs.

## Where to look next (hypotheses to test, not conclusions)
1. HTTP/1.1 request smuggling / desync at the Go-edge <-> Apache hop. The single-worker + KeepAlive-Off config is deliberate. Test CL.TE / TE.CL / CL.0 / H2-to-H1 downgrade smuggling and look for a cross-request contaminated response (a request you did NOT send coming back), then use the smuggled request to reach a handler that reads /flag.txt.
2. Whether a smuggled request can reach Apache with a Host/URI the edge would normalise differently, or reach a different vhost (/flag or a localhost vhost).
3. Apache internal-redirect / handler-confusion tricks (mod_dir subrequest, ErrorDocument, mod_negotiation) that make Apache treat a file outside the docroot (or /flag.txt via some alias) as a servable/executable target.

Goal: recover the exact flag string. Flag format for this event family is likely `MetaCTF{...}` (a placeholder `NotAFlag{Fake_Flag_For_Testing}` ship in the zip shows the braces shape). Do NOT report a flag you did not actually obtain from the live server.

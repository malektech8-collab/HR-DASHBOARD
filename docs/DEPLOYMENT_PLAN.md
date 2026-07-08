# Deployment Plan — v1.0.0 "Genesis" → Live on `hr.10fold.im`

> **Status: ACCEPTED, NOT YET EXECUTED.** This plan was reviewed and approved on 2026-07-08. No infrastructure, DNS, or server changes have been made. Do not begin execution until explicitly instructed.

## Target
- Domain: `10fold.im` (owned)
- Subdomain: `hr.10fold.im`
- Server: existing Contabo VPS
- DNS: Cloudflare (proxied)
- Release: `v1.0.0` tag / `production` branch only — never deploy from `main` directly

## 1. Pre-flight fixes (before anything is public)
- **JWT secret**: [backend/app/core/security.py:7](../backend/app/core/security.py:7) hardcodes `SECRET_KEY = "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD"` — move to an env var (`JWT_SECRET_KEY`), generate a real random secret, set only in a server-side `.env` (never committed).
- **CORS_ORIGINS**: add `https://hr.10fold.im` in `docker-compose.yml`'s backend env.
- **Don't publish the backend port publicly**: [frontend/nginx.conf](../frontend/nginx.conf) already proxies `/api` + `/health` to `backend:8000` internally, so in production drop the `8000:8000` host port mapping — only the reverse proxy (Caddy) needs to be internet-facing.

## 2. Server (Contabo)
- Use the existing Contabo VPS.
- Harden: create a non-root sudo user, SSH key auth only (disable password/root login), `ufw` allowing only `22, 80, 443`, `fail2ban` for SSH.
- Install Docker Engine + Compose plugin.
- Clone the repo, `git checkout production`.

## 3. DNS (Cloudflare)
- Add `A` record: `hr` → Contabo VPS public IP.
- **Proxy status: Proxied (orange cloud)** — free DDoS protection, hides origin IP, edge caching for static assets.
- **SSL/TLS mode: Full (Strict)** — requires a real, valid cert at the origin. Caddy's automatic Let's Encrypt cert satisfies this. Avoid "Flexible" mode.

## 4. TLS termination at origin
Add **Caddy** as a third Compose service (ports 80/443 only, published to the host), reverse-proxying to `hr-frontend:8080`. Caddy auto-issues/renews a Let's Encrypt cert via HTTP-01 — works fine through Cloudflare's proxy since Cloudflare passes `/.well-known/acme-challenge/*` straight to the origin. No Cloudflare API token / DNS-01 plugin needed.

## 5. Known caveat: Cloudflare's proxy timeout vs. the data-refresh endpoint
`POST /api/data/refresh` runs a full dbt rebuild and nginx already allows it up to 200s ([frontend/nginx.conf:19-21](../frontend/nginx.conf)). Cloudflare's proxy (Free/Pro plans) kills idle origin connections around **100s**, which would surface as a `524` for that action (cosmetic — the refresh still finishes server-side). Decide at execution time between:
- **(a)** Accept it, document "refresh may show a timeout but completes in the background — reload after ~2 min" (no infra change). *Leaning toward this.*
- **(b)** Trigger refreshes via SSH (`docker compose exec backend python scripts/refresh_all.py`) instead of the public endpoint; hide/disable that UI button in the deployed build. *Or this.*
- **(c)** Set that one DNS record to DNS-only (grey cloud), sacrificing Cloudflare's edge protection for the whole subdomain just to fix one action. *Least preferred.*

## 6. Deploy branch discipline
Deploy only from **`production` branch / `v1.0.0` tag**, never `main` directly — matches the branch policy in [DOCUMENTATION.md §17](../DOCUMENTATION.md). Future releases: fast-forward `production` to a reviewed `main` commit, tag it, redeploy.

## 7. First cutover — step order (when execution is authorized)
1. Provision/confirm the Contabo VPS, harden SSH/firewall, install Docker.
2. Clone repo → `git checkout production`.
3. Create server-side `.env`: `JWT_SECRET_KEY=<generated>`, `CORS_ORIGINS=https://hr.10fold.im`, `VITE_API_URL=https://hr.10fold.im`.
4. Add Caddy service + `Caddyfile` (`hr.10fold.im { reverse_proxy hr-frontend:8080 }`) to Compose; remove public port mappings from `backend`/`frontend` services.
5. Add the Cloudflare `A` record (proxied), set SSL/TLS mode to Full (Strict).
6. `docker compose up -d --build`; confirm Caddy obtains its cert and the site loads over HTTPS.
7. Smoke test: `/health`, login as each of the 3 synthetic roles, spot-check a few dashboard pages, theme toggle, logo upload.

## 8. Ongoing redeploys
Manual for now: SSH in, `git pull` on `production`, `docker compose up -d --build`. Automating via GitHub Actions (build → push to GHCR → SSH deploy on tag push) is a future improvement, not part of the first cutover.

## 9. Backups
Cron a daily `tar`/`rsync` of the host-mounted `warehouse/` and `data/` directories on the Contabo box.

## 10. Rollback
`production`/`v1.0.0` are frozen — rollback is `git checkout` the previous production commit/tag on the server + `docker compose up -d --build`.

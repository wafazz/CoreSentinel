# Deployment Memory
> How each project gets deployed. No more re-explaining server setup.

---

## Project Deployment Index

| Project | Target | Status | Domain |
|---|---|---|---|
| Basic Custom E-Commerce | VPS (Nginx + PHP 8.3 + MySQL 8) | Handed off, not yet deployed | TBC |
<!-- Add your projects here as you deploy them -->

---

## Deployment Recipes

### Recipe A: Laravel on VPS (Nginx)

```bash
# 1. Server setup
sudo apt update && sudo apt upgrade -y
sudo apt install nginx mysql-server php8.3-fpm php8.3-{cli,mbstring,xml,curl,zip,gd,mysql,redis,bcmath} composer nodejs npm -y

# 2. Clone & install
cd /var/www
git clone {repo} {project}
cd {project}
composer install --no-dev --optimize-autoloader
npm install && npm run build
cp .env.example .env && php artisan key:generate

# 3. Configure .env
# APP_ENV=production, APP_DEBUG=false, APP_URL, DB_*, MAIL_*

# 4. Database
php artisan migrate --force
php artisan db:seed --force

# 5. Storage & permissions
php artisan storage:link
sudo chown -R www-data:www-data storage bootstrap/cache
sudo chmod -R 775 storage bootstrap/cache

# 6. Nginx config
# server_name domain.com; root /var/www/{project}/public;
# location / { try_files $uri $uri/ /index.php?$query_string; }

# 7. SSL
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d domain.com

# 8. Queue worker (supervisor)
# command=php /var/www/{project}/artisan queue:work --sleep=3 --tries=3

# 9. Scheduler
# * * * * * cd /var/www/{project} && php artisan schedule:run >> /dev/null 2>&1

# 10. Optimize
php artisan config:cache && php artisan route:cache && php artisan view:cache
```

### Recipe A2: Laravel server-rendered — no Node, no queue worker

Use when the app is **Blade-only with no build step** and `QUEUE_CONNECTION=sync`.
Recipe A's `npm install && npm run build`, `storage:link` and Supervisor block are all
**wrong** here and will either fail or install a service that does nothing.
First shipped: Basic Custom E-Commerce (Laravel 12, PHP 8.3).

```bash
# 1. Server — note: no nodejs/npm
sudo apt install -y nginx mysql-server \
  php8.3-fpm php8.3-{cli,mbstring,xml,curl,zip,mysql,bcmath} \
  composer certbot python3-certbot-nginx git unzip

# 2. Install
cd /var/www && git clone {repo} {project} && cd {project}
composer install --no-dev --optimize-autoloader
cp .env.example .env
php artisan key:generate          # ONCE — see the warning below

# 3. Database — do NOT run a blanket db:seed in production
php artisan migrate --force
php artisan db:seed --class=SettingSeeder --force   # config rows only, no demo data
php artisan shop:create-admin                       # prompts; never echoes the password

# 4. Permissions — no storage:link; uploads go straight into public/
sudo chown -R www-data:www-data storage bootstrap/cache public/uploads
sudo chmod -R 775 storage bootstrap/cache public/uploads

# 5. Caches
php artisan config:cache && php artisan route:cache && php artisan view:cache

# 6. TLS
sudo certbot --nginx -d {domain}
```

Nginx: `root /var/www/{project}/public;` — the document root on `public/` is what keeps
`.env`, `app/`, `config/`, `database/`, `storage/`, `vendor/` off the web. Add
`location ~ /\.(?!well-known).* { deny all; }` and set `client_max_body_size` above the
app's upload cap.

**Deploy an update**

```bash
git pull && composer install --no-dev --optimize-autoloader
php artisan migrate --force
php artisan optimize:clear
php artisan config:cache && php artisan route:cache && php artisan view:cache
```

**Traps this recipe exists to avoid**

| Trap | Detail |
|---|---|
| `APP_KEY` rotation | If any column uses the `encrypted` cast (OAuth tokens, API secrets), regenerating `APP_KEY` makes those rows undecryptable. Generate **once**; back `.env` up **separately from the DB dump** — one backup holding both carries its own key. Same for the app `cipher`: fix it before the first ciphertext is written. |
| Blanket `db:seed` | Demo-catalogue seeders will happily insert test products into a live store. Seed named classes only, and make the admin seeder **refuse** to run in production without env credentials. |
| `env()` after `config:cache` | Returns **null**. Only ever call `env()` inside `config/`. Silent, and only in production — the worst combination. |
| MariaDB under the `mysql` driver | Set `DB_CONNECTION=mariadb` on a MariaDB host. `renameColumn()` is a hard syntax error on MariaDB ≤ 10.5.2 under the `mysql` grammar — a future migration fails on deploy, not in testing. |
| Payment callback URL | Must be publicly reachable over **HTTPS** before the first real transaction; a gateway cannot call `localhost`. Verify from outside the box, not from the box. |
| Handover credentials | Ship a forced first-login password change (DB flag + middleware), not a runbook instruction. See `11-pattern-library.md`. |

### Recipe B: Docker

```yaml
# docker-compose.yml structure:
# - app (PHP-FPM + Nginx)
# - db (MySQL/PostgreSQL)
# - redis (if needed)
# - queue worker (if needed)
# - scheduler (if needed)
```

```bash
docker-compose build --no-cache
docker-compose run --rm app php artisan migrate --force
docker-compose up -d
```

### Recipe C: Next.js / Node.js on Vercel

```bash
# 1. Connect GitHub repo to Vercel
# 2. Set environment variables in Vercel dashboard
# 3. Deploy (automatic on push to main)
# 4. Custom domain in Vercel settings
```

### Recipe D: Static / SPA on Netlify

```bash
# 1. Connect GitHub repo
# 2. Build command: npm run build
# 3. Publish directory: dist/ or build/
# 4. Environment variables in Netlify dashboard
```

---

## Post-Deploy Checklist

- [ ] `.env` configured (production mode, debug off)
- [ ] Database migrated
- [ ] Storage/uploads accessible
- [ ] File permissions correct
- [ ] SSL certificate installed
- [ ] Queue worker running (if applicable)
- [ ] Scheduler cron active (if applicable)
- [ ] Cache optimized
- [ ] Webhooks/callbacks point to production URL
- [ ] DNS configured
- [ ] Login works
- [ ] Core features tested
- [ ] Error logging configured

---

## Troubleshooting

| Issue | Fix |
|---|---|
| 403 on uploaded files | Check storage symlink + file permissions |
| 500 error, no details | Check error logs, temporarily enable debug |
| Queue jobs not processing | Check supervisor/worker status |
| Scheduled tasks not running | Check crontab entry |
| CSS/JS not loading | Run build command, check manifest |
| Mixed content (HTTP/HTTPS) | Set APP_URL to https |
| Redis connection refused | Check Redis service is running |

---

## Recipe A3 — Laravel 12 + Inertia/Vue PWA on a small VPS

First used: **Daily Spend** (2026-08-29). nginx + PHP-FPM 8.3 + MySQL 8 or MariaDB 10.5+.

**Node is a build-time dependency only.** `npm run build` emits `public/build`; the server
needs no Node at runtime. If the host cannot run Node, build in CI and ship `public/build`
as an artifact.

```bash
composer install --no-dev --optimize-autoloader
php artisan migrate --force
npm ci && npm run build
php artisan config:cache route:cache view:cache
sudo systemctl reload php8.3-fpm
```

Cron, one line — the only scheduled work is recurring-expense generation at 00:15:
```
* * * * * cd /var/www/app && php artisan schedule:run >> /dev/null 2>&1
```

**TLS is not optional.** A service worker will not register over plain HTTP, so without a
certificate the PWA requirement simply does not function — no install prompt, no offline
shell. Set `SESSION_SECURE_COOKIE=true` at the same time.

**Keep the previous `public/build` for a grace period** after an atomic-symlink deploy.
Inertia 3 lazy-splits chunks by default, so an open tab 404s on a stale chunk otherwise;
the app handles `vite:preloadError` by reloading, but only if the old chunk 404s rather
than the whole origin failing.

**Gotchas found the hard way:**
- `config/app.php` in the slim skeleton hardcodes `'timezone' => 'UTC'`. Fix it to read
  `env('APP_TIMEZONE')` or the scheduler runs on a different calendar day from your users.
- On **MariaDB ≤ 10.4**, `DB_CONNECTION=mariadb` is mandatory, not stylistic — the `mysql`
  driver emits `RENAME COLUMN`, which that engine does not have.
- Private user uploads (`storage/app/private/`) are in the backup set and must not be
  web-reachable. `storage:link` is not needed if nothing user-uploaded is public.
- Take the database backup **before** any risky DDL, not after it goes wrong.

---

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
- [ ] **Token-refresh jobs proved, not assumed** — see below

### When the scheduler holds a credential's lifetime

"Scheduler cron active (if applicable)" is too soft when a scheduled job is what keeps an API
credential alive. Several providers issue tokens that expire on a **calendar** — Meta Threads is
60 days, and once lapsed it cannot be refreshed or exchanged, only replaced by hand. If
`schedule:run` is not in cron on the production host, nothing fails at deploy time. It fails
weeks later, silently, and the first symptom is a listening tool that has quietly stopped
returning results.

So on any deploy of an app with a token-refresh command:

1. Confirm the cron entry exists on the **production** host, not just in `routes/console.php`.
2. Run the command by hand once (`php artisan threads:refresh-token --dry-run`) and read the output.
3. Note the token's expiry somewhere a person will see it before it lapses.

*(Recorded 2026-09-11 from Social Media Listening Tools.)*

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


---

## Recipe A4 — Laravel 12 + PostgreSQL + queue workers, third-party integration SaaS

> From SociaPulse (2026-09-12). Use where the app holds **other people's OAuth tokens** and does
> its real work on queues. The four items below are the ones that do not announce themselves:
> each fails silently, or cannot be fixed after the fact.

### A4.1 Four things that must be right before the first customer

| # | Item | Why it cannot wait |
|---|---|---|
| 1 | **`'timezone' => 'UTC'` on the pgsql connection** | Laravel sends UTC wall-clock text; `timestamptz` attaches the **server's** offset without this. Every timestamp lands offset by the machine's UTC offset — scheduled work fires early, day-bucketed reports land on the wrong day. Invisible to a developer in UTC. |
| 2 | **Token encryption key, versioned and stored apart from the database** | The cipher cannot be changed after tokens exist without a re-encryption path. A backup holding both the ciphertext and its key is a plaintext backup. |
| 3 | **Object storage with publicly fetchable URLs** | Providers that *fetch* media themselves (Meta's do) cannot reach a local disk. Media publishing does not degrade — it simply cannot work. |
| 4 | **Exact OAuth redirect URIs on a settled domain** | No provider accepts a wildcard subdomain. Changing the domain means re-registering everywhere, and for Google re-verifying. |

### A4.2 Two processes, both mandatory

```bash
php artisan schedule:run          # every minute — cron or systemd timer
php artisan horizon               # or queue:work over every queue name
```

If either is missing, scheduled work sits `queued` **in silence** until it ages past its window.
There is no error, no failed job, and nothing in the log — which makes this the first thing to
check when "nothing is publishing".

Separate queues by **failure mode, not by feature**: a stuck long-poll must not delay a reply,
and a webhook burst must not delay scheduled work.

### A4.3 Post-deploy verification specific to this shape

```bash
php artisan tinker --execute='echo DB::selectOne("SHOW TIME ZONE")->TimeZone;'   # must be UTC
php artisan sociapulse:rotate-token-keys --status                                 # keys resolve
php artisan schedule:list                                                         # every entry present
php artisan queue:monitor publish,sync,webhooks --max=100
```

Then the **restore drill**, whose pass condition is the whole point: key available → app
restored → database restored → **stored tokens still decrypt and provider connections still
work, with no customer reconnecting.** A backup is not valid until a restore has been tested.

### A4.4 Gotchas met in the field

- **Two PostgreSQL servers on one machine** is common on developer Macs (an EDB installer on
  5432 and Homebrew on 5433). `psql --version`, `pg_isready` and the `pg_hba.conf` you happen to
  open can all point at the wrong one. Read the running postmasters directly:
  `ps -ax -o pid,command | grep "[b]in/postgres"` shows each `-D` data directory, then check
  `port` in that directory's `postgresql.conf`.
- **Rotating an app secret invalidates webhook signatures immediately.** Expect signature
  failures between rotation and deploy — rotate, update config, deploy, *then* scrub history.
- **A missing spend ceiling must mean "off", not "unlimited"**, for any metered provider. Ship
  the config key unset and the feature disabled.

### A4.5 CI for this shape — the sentinel-credential log scan

> From SociaPulse (2026-09-12). Use wherever the claim is *"no credential appears in any log
> line"*. A test can prove what reaches the browser. Only a pass over real log output can prove
> what reaches the log, and a regex alone cannot do it honestly.

**The problem with grepping for credentials.** A search for `client_secret` or `access_token`
finds field *names* — form labels, array keys, log messages saying a token is missing. Tune the
pattern until those stop matching and it no longer matches a real leak either.

**The technique.** CI sets every credential the app reads from the environment to a *sentinel*:
a long, unmistakable string. The suite runs. Then grep the logs for those exact strings.

```yaml
env:
  FACEBOOK_APP_SECRET: s3ntinel-facebook-app-secret-must-never-be-logged
  LOG_CHANNEL: single          # one destination, so the scan has one place to read
```

- **Zero false positives.** The sentinel has no other reason to exist, so a hit is proof that a
  credential-carrying code path writes to a log.
- **A second pass catches what no sentinel can stand in for**: stored tokens never come from the
  environment. Match a credential *name followed by a value* (`name[:=]value`, value ≥ 12 chars),
  allowlisting `[REDACTED]`, `null`, `missing`. A bare name passes; a name with a value does not.
- **An absent or empty log file must FAIL, not pass.** A suite that logged nothing proves nothing
  about what it would log, and treating silence as a pass lets a misconfigured `LOG_CHANNEL`
  masquerade as a clean result. This is the failure mode that makes such a scan decorative.

**Never upload CI logs when the scan is what failed.** The logs then contain a credential, and an
artifact copies that leak into downloadable storage with its own retention. Condition the upload
on the *test step's* outcome, not the job's. The scan's own output already names the lines.

**Two further CI notes for a Laravel + Postgres project:**

- **`phpunit.xml`'s `<env>` entries are not `force`d by default**, so a real environment variable
  wins. That is the whole reason CI needs no edit to the committed config: export
  `DB_HOST`/`DB_PORT`/`DB_USERNAME`/`DB_PASSWORD` in the workflow and the suite follows, while a
  developer's local ports stay in the file. Verify it rather than trusting it —
  `DB_PORT=19999 vendor/bin/phpunit` must fail to connect.
- **Run CI against the real database engine.** A schema using CHECK constraints, JSONB or
  `timestamptz` is not exercised by SQLite; a green SQLite run is a green run against a different
  database than production.

### A4.6 Keeping deploy config from drifting — test it like code

Deploy configuration is the one layer whose mistakes are **silent**. A job dispatched to a queue
no worker consumes waits forever: no exception, no failed job, nothing in the log. A command
missing from the schedule simply never runs. Nobody reports either, because from the outside the
application looks perfect.

So assert *agreement*, not well-formedness. Parse the queue names out of the job classes and the
commands out of the schedule file, then require each to appear in the worker units, the
post-deploy check, and the runbook:

```
every onQueue('x') in app/Jobs  →  a documented worker instance for x
                                →  a post-deploy assertion that x has a worker
                                →  a runbook line naming x
every Schedule::command('y')    →  a registered artisan command
                                →  a post-deploy assertion + a runbook consequence line
```

Two things make this worth writing rather than skipping:

1. **Guard the parser.** If the regex stops matching, every assertion passes vacuously and the
   test becomes decoration. Assert the parsed list is non-empty.
2. **Prove it fails.** Introduce a queue with no worker and watch the assertions go red, each
   naming the consequence. A guard never seen to fail is an unverified guard.

### A4.7 Production posture — the settings that are wrong silently (added 2026-09-12)

Everything in A4.3 checks that the machinery *runs*. These four check that it runs **safely**,
and every one of them leaves the site serving pages perfectly while it is wrong. Add them to
the post-deploy script, not to a wiki page.

```bash
php artisan tinker --execute='echo config("app.debug") ? "on" : "off";'            # must be off
php artisan tinker --execute='echo count((array) config("app.trusted_proxies"));'  # must be > 0
php artisan tinker --execute='echo config("app.url");'                             # https, real host
php artisan tinker --execute='echo config("session.secure") ? "yes" : "auto/no";'
```

- **`APP_DEBUG` is the one that leaks rather than breaks.** The site behaves normally right up
  until the first unhandled exception, which renders the resolved environment — `APP_KEY`, every
  third-party client secret, the database password — to whoever triggered it. Nothing about a
  working site reveals the setting, so it must be asserted, never assumed.
- **`TRUSTED_PROXIES` empty is not a tuning problem.** Behind Nginx every request appears to come
  from the loopback, which silently falsifies any audit column fed by `Request::ip()` and
  collapses every IP-keyed rate limiter into one bucket shared by the whole customer base. See
  the *Trust the Reverse Proxy* pattern in `11-pattern-library.md` for the config-cache trap that
  makes the obvious fix fail only in production.
- **`APP_URL` on http or localhost fails at the provider, not here.** Every OAuth redirect URI,
  email verification link and signed URL is built from it, and a registered redirect URI must
  match character for character.
- **Session cookie `Secure`**: leaving it to auto-detect is only correct once the proxy is
  trusted, because an untrusted request looks like plain http. Set it explicitly in production.

**Also worth a line in the runbook**: the recovery procedure for work abandoned by a dead
worker — what state it lands in, and the instruction *not* to retry it before checking the
third party, since the side effect may already have happened. See *Reaping an Abandoned Claim*
in `11-pattern-library.md`.

# Deployment Memory
> How each project gets deployed. No more re-explaining server setup.

---

## Project Deployment Index

| Project | Target | Status | Domain |
|---|---|---|---|
<!-- Add your projects here as you deploy them -->
<!-- Example: | My App | VPS (DigitalOcean) | Deployed | myapp.com | -->

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

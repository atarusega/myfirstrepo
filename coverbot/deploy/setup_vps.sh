#!/usr/bin/env bash
# Первичная настройка VPS для coverbot (Ubuntu 24.04/26.04, запуск от root):
#   curl -fsSL <ссылка на этот файл> | bash
# Бот работает от пользователя coverbot как systemd-сервис, база — SQLite.
# Обновления без SSH: таймер раз в 5 минут забирает ветку с GitHub и перезапускает бота (deploy/update.sh).
set -euo pipefail

REPO=https://github.com/atarusega/myfirstrepo.git
BRANCH=claude/new-session-fpj0mr
HOME_DIR=/opt/coverbot
SRC=$HOME_DIR/src
APP=$SRC/coverbot
PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEa0eOgTJkjIy1oy416GrtgmV89rZGrFA1wdVhcc+YFD coverbot-vps'

echo "== 1/6 пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3-venv python3-pip sqlite3 curl >/dev/null

echo "== 2/6 убираем тестовое и закрываем вход по паролю"
pkill -f "http.server 8080" 2>/dev/null || true
rm -f /etc/ssh/sshd_config.d/p.conf
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/10-coverbot.conf
mkdir -p /root/.ssh && chmod 700 /root/.ssh
grep -qF "$PUBKEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$PUBKEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
systemctl daemon-reload && systemctl restart ssh.socket 2>/dev/null || systemctl restart ssh

echo "== 3/6 код и зависимости"
id coverbot >/dev/null 2>&1 || useradd --system --create-home --home-dir "$HOME_DIR" --shell /usr/sbin/nologin coverbot
if [ ! -d "$SRC/.git" ]; then
  sudo -u coverbot git clone -q --depth 1 --branch "$BRANCH" "$REPO" "$SRC"
else
  sudo -u coverbot git -C "$SRC" pull -q --ff-only
fi
sudo -u coverbot python3 -m venv "$APP/.venv"
sudo -u coverbot "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"
mkdir -p "$HOME_DIR/backups" && chown coverbot:coverbot "$HOME_DIR/backups"

echo "== 4/6 настройки бота (.env)"
if [ ! -f "$APP/.env" ]; then
  while true; do
    printf "Токен бота от @BotFather: "
    read -r TOKEN </dev/tty
    ME=$(curl -s "https://api.telegram.org/bot$TOKEN/getMe" || true)
    if echo "$ME" | grep -q '"ok":true'; then
      USERNAME=$(echo "$ME" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
      echo "Токен подходит: @$USERNAME"
      break
    fi
    echo "Telegram не принял токен, введите ещё раз (проверьте опечатки)."
  done
  printf "Telegram ID админа: "
  read -r ADMIN </dev/tty
  cat > "$APP/.env" <<EOF
BOT_TOKEN=$TOKEN
BOT_USERNAME=$USERNAME
ADMIN_IDS=$ADMIN
SEARCH_ENABLED=false
DATABASE_URL=sqlite+aiosqlite:///./coverbot.db
REDIS_URL=
ANTHROPIC_API_KEY=
EOF
  chown coverbot:coverbot "$APP/.env" && chmod 600 "$APP/.env"
fi

echo "== 5/6 сервис, обновления, бэкап"
cat > /etc/systemd/system/coverbot.service <<EOF
[Unit]
Description=coverbot (Telegram)
After=network-online.target
Wants=network-online.target

[Service]
User=coverbot
WorkingDirectory=$APP
ExecStart=$APP/.venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/coverbot-update.service <<EOF
[Unit]
Description=coverbot: забрать обновления с GitHub

[Service]
Type=oneshot
ExecStart=/bin/bash $APP/deploy/update.sh
EOF

cat > /etc/systemd/system/coverbot-update.timer <<EOF
[Unit]
Description=coverbot: проверять обновления раз в 5 минут

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# копия базы каждую ночь в 04:00, хранить 14 дней
cat > /etc/cron.d/coverbot-backup <<EOF
0 4 * * * coverbot sqlite3 $APP/coverbot.db ".backup $HOME_DIR/backups/coverbot-\$(date +\%F).db" && find $HOME_DIR/backups -name 'coverbot-*.db' -mtime +14 -delete
EOF

systemctl daemon-reload
systemctl enable --now coverbot coverbot-update.timer >/dev/null

echo "== 6/6 проверка"
sleep 8
if systemctl is-active --quiet coverbot; then
  echo "ГОТОВО: бот запущен. Журнал: journalctl -u coverbot -n 20"
else
  echo "ОШИБКА: бот не запустился, последние строки журнала:"
  journalctl -u coverbot -n 15 --no-pager
fi

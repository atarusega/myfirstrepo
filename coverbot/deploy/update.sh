#!/usr/bin/env bash
# Запускается таймером coverbot-update раз в 5 минут (deploy/setup_vps.sh):
# если на GitHub в ветке появились новые коммиты — забрать, доставить зависимости, перезапустить бота.
set -euo pipefail

SRC=/opt/coverbot/src
APP=$SRC/coverbot
git_() { sudo -u coverbot git -C "$SRC" "$@"; }

git_ fetch -q origin
LOCAL=$(git_ rev-parse HEAD)
REMOTE=$(git_ rev-parse FETCH_HEAD)
[ "$LOCAL" = "$REMOTE" ] && exit 0

git_ reset -q --hard FETCH_HEAD
sudo -u coverbot "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"
systemctl restart coverbot
echo "coverbot updated: ${LOCAL:0:7} -> ${REMOTE:0:7}"

"""Держит бота запущенным в фоне: один экземпляр, перезапуск при падении, лог в logs/bot.log.

Запускается ярлыком CoverBot в автозагрузке Windows через pythonw (без окна).
"""
import msvcrt
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # папка coverbot: там .env и coverbot.db
PY = ROOT / ".venv" / "Scripts" / "python.exe"
LOGS = ROOT / "logs"
LOG = LOGS / "bot.log"
MAX_LOG = 5 * 1024 * 1024
MIN_DELAY, MAX_DELAY = 10, 300
STABLE_RUN = 300  # бот проработал столько секунд — пауза перед перезапуском снова минимальная


def log(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} supervisor: {line}\n")


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    lock = open(LOGS / "supervisor.lock", "w")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return  # уже запущен: один токен нельзя поллить дважды (Telegram Conflict)

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    delay = MIN_DELAY
    while True:
        if LOG.exists() and LOG.stat().st_size > MAX_LOG:
            LOG.replace(LOGS / "bot.log.1")
        log(f"запуск бота (pid supervisor {os.getpid()})")
        started = time.monotonic()
        with open(LOG, "a", encoding="utf-8") as out:
            code = subprocess.call(
                [str(PY), "-m", "app.main"], cwd=ROOT, env=env,
                stdout=out, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        # при старте Windows сеть и VPN поднимаются не сразу — бот выходит, ждём и пробуем снова
        delay = MIN_DELAY if time.monotonic() - started > STABLE_RUN else min(delay * 2, MAX_DELAY)
        log(f"бот завершился с кодом {code}, перезапуск через {delay} с")
        time.sleep(delay)


if __name__ == "__main__":
    main()

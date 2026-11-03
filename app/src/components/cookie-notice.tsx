import { useState } from "react"
import { analyticsEnabled } from "@/lib/analytics"

const KEY = "struktorum:cookie-ok"

function wasAccepted() {
  try {
    return window.localStorage.getItem(KEY) === "1"
  } catch {
    return false
  }
}

/** Плашка о cookie и Метрике. Показывается, только пока счётчик включён и «Ок» ещё не нажимали. */
export function CookieNotice() {
  const [visible, setVisible] = useState(() => analyticsEnabled && !wasAccepted())
  if (!visible) return null

  const accept = () => {
    try {
      window.localStorage.setItem(KEY, "1")
    } catch {
      /* приватный режим: плашка просто не запомнится */
    }
    setVisible(false)
  }

  return (
    <div
      role="region"
      aria-label="Уведомление о cookie"
      className="fixed right-4 bottom-4 left-4 z-[60] flex items-center gap-3 rounded-2xl bg-graphite/95 py-3 pr-3 pl-4 text-white shadow-[0_20px_40px_-15px_rgba(0,0,0,0.8)] ring-1 ring-white/10 sm:right-auto sm:max-w-[420px] md:bottom-6 md:left-6"
    >
      <p className="text-[11px] leading-snug font-medium text-white/80">
        Сайт использует cookie и Яндекс Метрику для статистики посещений
      </p>
      <button
        type="button"
        onClick={accept}
        className="shrink-0 rounded-full bg-brand px-4 py-2 text-[11px] font-medium tracking-[0.06em] text-white uppercase transition-colors hover:bg-brand/85"
      >
        Ок
      </button>
    </div>
  )
}

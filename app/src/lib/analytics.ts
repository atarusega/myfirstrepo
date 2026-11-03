// Яндекс Метрика. Номер счётчика — в app/.env (VITE_YM_COUNTER_ID), больше нигде.
// Сам счётчик подключается в index.html; здесь — цели и просмотры проектов без перезагрузки страницы.

declare global {
  interface Window {
    ym?: (id: number, method: string, ...args: unknown[]) => void
  }
}

const RAW_ID = String(import.meta.env.VITE_YM_COUNTER_ID ?? "")

/** Счётчик включён, только если в .env настоящий номер (одни цифры) */
export const analyticsEnabled = /^\d+$/.test(RAW_ID)
const YM_ID = analyticsEnabled ? Number(RAW_ID) : 0

function ym(method: string, ...args: unknown[]) {
  if (!analyticsEnabled) return
  try {
    window.ym?.(YM_ID, method, ...args)
  } catch {
    /* сбой статистики не должен ломать сайт */
  }
}

/** Цель Метрики: contact_click, case_open, cv_download */
export function reachGoal(goal: string, params?: Record<string, unknown>) {
  ym("reachGoal", goal, params)
}

/** Открыли проект: виртуальный просмотр страницы /projects/<id> + цель case_open с названием */
export function trackProjectOpen(project: { id: number; title: string }) {
  const url = `${location.origin}/projects/${project.id}`
  ym("hit", url, { title: `${project.title} — Структорум`, referer: location.href })
  reachGoal("case_open", { case: project.title })
}

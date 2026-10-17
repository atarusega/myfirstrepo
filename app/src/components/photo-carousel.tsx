import { useEffect, useRef, useState } from "react"
import { animate, type MotionValue } from "motion/react"

type Item = { src: string; alt: string; width: number; height: number }

type Props = {
  items: Item[]
  label: string
  // Сдвиг всего окна проекта: смахнули вниз — проект уезжает и закрывается
  pull: MotionValue<number>
  onClose: () => void
  onIndex?: (index: number) => void
}

// Карусель-«поворотный круг» (по мотивам bencho.dev/blocks/carousel): текущее фото впереди,
// соседние повёрнуты и уходят назад; карточки покачиваются, круг наклоняется за курсором,
// листается перетаскиванием с инерцией и доводкой до ближайшего фото. Своя реализация на CSS 3D.
const STEP = 0.62 // радиан между соседними карточками на круге
const SPREAD = 0.68 // насколько соседняя карточка выглядывает сбоку, доля ширины текущей
const FLOAT = 7 // амплитуда покачивания, px
const SINK = 26 // насколько боковые карточки опускаются, px
const DEPTH = 220 // насколько боковые карточки уходят вглубь, px
const LEAN = 7 // наклон за курсором, градусы
const SETTLE = 110 // время доводки, мс (меньше — резче)

export function PhotoCarousel({ items, label, pull, onClose, onIndex }: Props) {
  const root = useRef<HTMLDivElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const cards = useRef<(HTMLDivElement | null)[]>([])
  const pos = useRef(0)
  const target = useRef(0)
  const lean = useRef({ x: 0, y: 0, tx: 0, ty: 0 })
  const box = useRef({ w: 0, h: 0 })
  const n = items.length
  const [index, setIndex] = useState(0)

  // Смещение карточки относительно текущей по кругу: -n/2..n/2
  const offset = (i: number) => {
    let o = (i - pos.current) % n
    if (o > n / 2) o -= n
    if (o < -n / 2) o += n
    return o
  }

  const layout = (t: number) => {
    const { w, h } = box.current
    if (!w || !h) return
    const maxH = h * 0.72
    const maxW = Math.min(w * (w < 640 ? 0.8 : 0.5), 900)
    // Радиус круга подбираем так, чтобы соседняя карточка выглядывала на SPREAD своей ширины
    const R = (maxW * SPREAD) / Math.sin(STEP)
    items.forEach((it, i) => {
      const el = cards.current[i]
      if (!el) return
      const o = n > 1 ? offset(i) : 0
      const a = Math.abs(o)
      if (a > 2.6) {
        el.style.visibility = "hidden"
        return
      }
      const fit = Math.min(maxW / it.width, maxH / it.height)
      const cw = it.width * fit
      const ch = it.height * fit
      const th = o * STEP
      const x = Math.sin(th) * R
      const z = (Math.cos(th) - 1) * R - Math.min(a, 2) * DEPTH
      const bob = Math.sin(t / 1100 + i * 1.7) * FLOAT
      const tilt = Math.sin(t / 1700 + i * 2.3) * 1.2
      const y = bob + Math.min(a, 1.5) * SINK
      el.style.visibility = "visible"
      el.style.width = `${cw}px`
      el.style.height = `${ch}px`
      el.style.marginLeft = `${-cw / 2}px`
      el.style.marginTop = `${-ch / 2}px`
      el.style.transform = `translate3d(${x}px, ${y}px, ${z}px) rotateY(${th * 0.45}rad) rotateZ(${tilt}deg)`
      el.style.zIndex = String(100 - Math.round(a * 10))
      el.style.opacity = String(Math.max(0, Math.min(1, 2.4 - a)))
      el.style.filter = `brightness(${1 - Math.min(a, 1.5) * 0.35})`
      el.style.cursor = a < 0.5 ? "grab" : "pointer"
    })
    const l = lean.current
    if (stage.current) stage.current.style.transform = `rotateX(${-l.y * LEAN}deg) rotateY(${l.x * LEAN}deg)`
  }

  // Постоянный цикл: покачивание идёт всегда, позиция и наклон доводятся по времени
  useEffect(() => {
    let raf = 0
    let last = 0
    const tick = (now: number) => {
      const dt = Math.min(64, last ? now - last : 16)
      last = now
      const k = 1 - Math.exp(-dt / SETTLE)
      if (!drag.current?.moved) pos.current += (target.current - pos.current) * k
      const l = lean.current
      const kl = 1 - Math.exp(-dt / 180)
      l.x += (l.tx - l.x) * kl
      l.y += (l.ty - l.y) * kl
      layout(now)
      setIndex((((Math.round(pos.current) % n) + n) % n))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

  useEffect(() => onIndex?.(index), [index, onIndex])

  useEffect(() => {
    const el = root.current!
    const ro = new ResizeObserver(() => (box.current = { w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const goTo = (t: number) => (target.current = t)

  // Колесо / тачпад: горизонталь и вертикаль крутят круг, после паузы — доводка
  useEffect(() => {
    const el = root.current!
    let acc = 0
    let idle = 0
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY
      acc += e.deltaMode === 1 ? d * 16 : d
      // Шаг на одно фото за «щелчок» колеса, тачпад копит
      if (Math.abs(acc) > 60) {
        target.current = Math.round(target.current) + Math.sign(acc)
        acc = 0
      }
      clearTimeout(idle)
      idle = window.setTimeout(() => (acc = 0), 160)
    }
    el.addEventListener("wheel", onWheel, { passive: false })
    return () => {
      el.removeEventListener("wheel", onWheel)
      clearTimeout(idle)
    }
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented) return
      if (e.key === "ArrowRight") goTo(Math.round(target.current) + 1)
      else if (e.key === "ArrowLeft") goTo(Math.round(target.current) - 1)
      else return
      e.preventDefault()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  // Перетаскивание: направление фиксируем после 8 px. Вбок — крутим круг, вниз — тянем окно (закрытие).
  const drag = useRef<{
    id: number
    x: number
    y: number
    start: number
    t: number
    lastX: number
    lastT: number
    v: number
    lock: "x" | "y" | null
    moved: boolean
  } | null>(null)
  const unit = () => Math.min(box.current.w * (box.current.w < 640 ? 0.8 : 0.5), 900) * 0.8

  const onPointerMove = (e: React.PointerEvent) => {
    const { w, h } = box.current
    if (e.pointerType === "mouse" && w && h) {
      const r = root.current!.getBoundingClientRect()
      lean.current.tx = ((e.clientX - r.left) / w) * 2 - 1
      lean.current.ty = ((e.clientY - r.top) / h) * 2 - 1
    }
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (!d.lock) {
      if (Math.hypot(dx, dy) < 8) return
      d.lock = dy > 0 && Math.abs(dy) > Math.abs(dx) * 1.2 ? "y" : "x"
      d.moved = true
      try {
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
      } catch {
        /* указатель уже отпущен */
      }
    }
    if (d.lock === "y") {
      pull.set(Math.max(0, dy))
      return
    }
    const now = performance.now()
    if (now > d.lastT) d.v = (e.clientX - d.lastX) / (now - d.lastT)
    d.lastX = e.clientX
    d.lastT = now
    pos.current = d.start - dx / unit()
  }

  const onPointerUp = (e: React.PointerEvent) => {
    const d = drag.current
    drag.current = null
    if (!d || d.id !== e.pointerId) return
    if (!d.moved) {
      // Клик по соседней — повернуть круг к ней
      const hit = (e.target as HTMLElement).closest<HTMLElement>("[data-i]")
      if (!hit) return
      const i = Number(hit.dataset.i)
      const o = Math.round(offset(i))
      if (o !== 0) goTo(Math.round(target.current) + o)
      return
    }
    if (d.lock === "y") {
      const dy = e.clientY - d.y
      const speed = dy / Math.max(1, performance.now() - d.t)
      if (dy > 120 || (dy > 40 && speed > 0.6)) {
        animate(pull, window.innerHeight, { duration: 0.22, ease: "easeIn" })
        onClose()
      } else animate(pull, 0, { type: "spring", stiffness: 500, damping: 40 })
      return
    }
    // Инерция: бросок докручивает ещё на одно фото, потом доводка до ближайшего
    const fling = Math.max(-1, Math.min(1, (-d.v * 220) / unit()))
    goTo(Math.round(pos.current + fling))
  }

  return (
    <div
      ref={root}
      role="region"
      aria-label={label}
      tabIndex={0}
      className="relative size-full touch-none overflow-hidden outline-none select-none"
      style={{ perspective: "1100px" }}
      onPointerDown={(e) => {
        if (e.button !== 0) return
        drag.current = {
          id: e.pointerId,
          x: e.clientX,
          y: e.clientY,
          start: pos.current,
          t: performance.now(),
          lastX: e.clientX,
          lastT: performance.now(),
          v: 0,
          lock: null,
          moved: false,
        }
      }}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onPointerLeave={(e) => {
        if (e.pointerType === "mouse") lean.current.tx = lean.current.ty = 0
      }}
    >
      <div ref={stage} className="absolute inset-0" style={{ transformStyle: "preserve-3d" }}>
        {items.map((it, i) => (
          <div
            key={it.src}
            ref={(el) => {
              cards.current[i] = el
            }}
            data-i={i}
            className="absolute top-1/2 left-1/2 overflow-hidden rounded-[20px] bg-white/5 shadow-[0_30px_60px_-20px_rgba(0,0,0,0.7)] will-change-transform"
            style={{ visibility: "hidden" }}
          >
            <img src={it.src} alt={it.alt} decoding="async" draggable={false} className="size-full object-cover" />
          </div>
        ))}
      </div>
    </div>
  )
}

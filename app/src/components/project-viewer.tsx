import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { AnimatePresence, animate, motion, useMotionValue } from "motion/react"
import { DraggableMarquee } from "@/components/block/draggable-marquee"
import type { Project } from "@/data/projects"

type Props = {
  project: Project
  onClose: () => void
}

const pad = (n: number) => String(n).padStart(2, "0")

// Просмотр проекта: фото крутятся лентой (ObsidianUI Draggable Marquee), клик по фото — крупно.
export function ProjectViewer({ project, onClose }: Props) {
  const images = project.images
  const [zoom, setZoom] = useState<number | null>(null)
  // Ширина и высота известны заранее — лента сразу верной длины и не пересчитывается по мере загрузки фото
  const items = useMemo(
    () =>
      images.map((src, i) => ({
        id: i,
        src,
        alt: `${project.title} — ${i + 1}`,
        width: project.sizes?.[i]?.[0] ?? 800,
        height: project.sizes?.[i]?.[1] ?? 533,
      })),
    [images, project.title, project.sizes],
  )

  // Клик отличаем от перетаскивания ленты: засчитываем, только если указатель почти не сдвинулся
  const down = useRef({ x: 0, y: 0 })
  const isClick = (e: React.MouseEvent) => Math.hypot(e.clientX - down.current.x, e.clientY - down.current.y) < 6

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return
      if (zoom !== null) setZoom(null)
      else onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [zoom, onClose])

  // Смахивание вниз закрывает проект (на телефоне до крестика тянуться далеко).
  // Направление фиксируем после первых 10 px: по горизонтали — это лента, её не трогаем.
  const y = useMotionValue(0)
  const swipe = useRef<{ x: number; y: number; t: number; lock: "x" | "y" | null } | null>(null)
  const onTouchStart = (e: React.TouchEvent) => {
    if (zoom !== null || e.touches.length > 1) return
    const t = e.touches[0]
    swipe.current = { x: t.clientX, y: t.clientY, t: performance.now(), lock: null }
  }
  const onTouchMove = (e: React.TouchEvent) => {
    const s = swipe.current
    if (!s) return
    const dx = e.touches[0].clientX - s.x
    const dy = e.touches[0].clientY - s.y
    if (!s.lock && Math.hypot(dx, dy) > 10) s.lock = dy > 0 && Math.abs(dy) > Math.abs(dx) * 1.2 ? "y" : "x"
    if (s.lock === "y") y.set(Math.max(0, dy))
  }
  const onTouchEnd = (e: React.TouchEvent) => {
    const s = swipe.current
    swipe.current = null
    if (!s || s.lock !== "y") return
    const dy = e.changedTouches[0].clientY - s.y
    const speed = dy / (performance.now() - s.t) // px/мс
    if (dy > 120 || (dy > 40 && speed > 0.6)) {
      animate(y, window.innerHeight, { duration: 0.22, ease: "easeIn" })
      onClose()
    } else {
      animate(y, 0, { type: "spring", stiffness: 500, damping: 40 })
    }
  }

  const year = project.date.slice(0, 4)

  return (
    <motion.div
      className="fixed inset-0 z-50 flex touch-none flex-col bg-graphite text-white"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      style={{ y }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onTouchCancel={onTouchEnd}
    >
      <header className="flex h-16 shrink-0 items-center gap-4 bg-brand pl-5 md:h-[72px] md:gap-8 md:pl-10">
        {/* Цвет проекта — акцентной точкой, как цвета «подушки» в брендбуке */}
        <span className="size-3 shrink-0 rounded-full" style={{ background: project.color }} />
        <h2 className="line-clamp-2 min-w-0 flex-1 text-[clamp(14px,2.2vw,28px)] font-bold uppercase leading-[1.15] tracking-[0.04em] md:truncate">
          {project.title}
        </h2>
        <a
          href={project.url}
          target="_blank"
          rel="noopener"
          className="hidden text-[13px] font-medium uppercase tracking-[0.06em] transition-opacity hover:opacity-70 md:inline"
        >
          Пост в Telegram ↗
        </a>
        <button
          type="button"
          onClick={onClose}
          aria-label="Закрыть"
          className="h-full w-16 shrink-0 text-3xl transition-colors hover:bg-white/10 md:w-[72px]"
        >
          ×
        </button>
      </header>

      <div
        className="flex min-h-0 flex-1 flex-col justify-center gap-8 py-8"
        onPointerDownCapture={(e) => (down.current = { x: e.clientX, y: e.clientY })}
      >
        <div>
          <DraggableMarquee
            items={items}
            speed={0.6}
            gapClassName="gap-4 md:gap-6"
            itemClassName="rounded-[14px] overflow-hidden"
            label={`${project.title}: фото. Тяни ленту или используй стрелки.`}
            renderItem={(it: { src: string; [key: string]: unknown }, i: number) => {
              const item = it as (typeof items)[number]
              return (
              <img
                src={item.src}
                alt={item.alt}
                width={item.width}
                height={item.height}
                decoding="async"
                draggable={false}
                onClick={(e) => isClick(e) && setZoom(i)}
                style={{ aspectRatio: `${item.width} / ${item.height}` }}
                className="block h-[min(58vh,620px)] w-auto cursor-zoom-in select-none bg-white/5 object-cover max-sm:h-[46vh]"
              />
              )
            }}
          />
        </div>

        <div className="flex items-baseline justify-between px-5 text-[11px] font-medium uppercase tracking-[0.1em] text-white/40 md:px-10 md:text-[13px]">
          <span>
            {pad(images.length)} фото · {year}
          </span>
          <span className="hidden sm:inline">тяни ленту · нажми на фото</span>
        </div>
      </div>

      <AnimatePresence>
        {zoom !== null && <PhotoZoom images={images} start={zoom} title={project.title} onClose={() => setZoom(null)} />}
      </AnimatePresence>
    </motion.div>
  )
}

// Одно фото на весь экран, листается стрелками, свайпом и клавишами
function PhotoZoom({ images, start, title, onClose }: { images: string[]; start: number; title: string; onClose: () => void }) {
  const [[index, dir], setSlide] = useState<[number, number]>([start, 1])
  const go = useCallback(
    (step: number) => setSlide(([cur]) => [(cur + step + images.length) % images.length, step]),
    [images.length],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") go(-1)
      if (e.key === "ArrowRight") go(1)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [go])

  const touchX = useRef<number | null>(null)

  return (
    <motion.div
      className="fixed inset-0 z-60 flex items-center justify-center bg-graphite/95 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClose}
      onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (touchX.current === null) return
        const dx = e.changedTouches[0].clientX - touchX.current
        touchX.current = null
        if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1)
      }}
    >
      <AnimatePresence initial={false} custom={dir}>
        <motion.img
          key={index}
          src={images[index]}
          alt={`${title} — ${index + 1}`}
          custom={dir}
          variants={{
            enter: (d: number) => ({ opacity: 0, x: `${d * 4}%`, scale: 1.03 }),
            center: { opacity: 1, x: 0, scale: 1 },
            exit: (d: number) => ({ opacity: 0, x: `${-d * 4}%`, scale: 1.03 }),
          }}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }}
          className="absolute inset-0 m-auto max-h-[calc(100%-96px)] max-w-[calc(100%-32px)] rounded-[14px] object-contain sm:max-w-[calc(100%-176px)]"
          draggable={false}
          onClick={(e) => e.stopPropagation()}
        />
      </AnimatePresence>

      {(["prev", "next"] as const).map((side) => (
        <button
          key={side}
          type="button"
          aria-label={side === "prev" ? "Назад" : "Вперёд"}
          onClick={(e) => {
            e.stopPropagation()
            go(side === "prev" ? -1 : 1)
          }}
          className={
            "absolute inset-y-0 z-10 hidden w-[88px] text-3xl text-white/50 transition-colors hover:text-white sm:block " +
            (side === "prev" ? "left-0" : "right-0")
          }
        >
          {side === "prev" ? "←" : "→"}
        </button>
      ))}

      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 text-[13px] font-medium tracking-[0.1em] text-white/60 tabular-nums">
        {pad(index + 1)} / {pad(images.length)}
      </div>
      <button
        type="button"
        aria-label="Закрыть фото"
        onClick={onClose}
        className="absolute top-0 right-0 z-10 size-16 bg-brand text-3xl text-white md:size-[72px]"
      >
        ×
      </button>
    </motion.div>
  )
}

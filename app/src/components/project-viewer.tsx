import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"
import { AnimatePresence, motion } from "motion/react"
import type { Project } from "@/data/projects"

type Props = {
  project: Project
  onClose: () => void
}

const pad = (n: number) => String(n).padStart(2, "0")

// Полноэкранный просмотр проекта: большое фото, номера кадров, лента миниатюр.
export function ProjectViewer({ project, onClose }: Props) {
  const images = project.images
  const [[index, dir], setSlide] = useState<[number, number]>([0, 1])
  const indexRef = useRef<HTMLDivElement>(null)
  const thumbsRef = useRef<HTMLDivElement>(null)

  const go = useCallback(
    (next: number, direction?: number) => {
      setSlide(([cur]) => {
        const n = (next + images.length) % images.length
        return [n, direction ?? (n >= cur ? 1 : -1)]
      })
    },
    [images.length],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
      if (e.key === "ArrowLeft") go(index - 1, -1)
      if (e.key === "ArrowRight") go(index + 1, 1)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [go, index, onClose])

  // Держим активный номер и миниатюру в поле зрения
  useEffect(() => {
    const opts: ScrollIntoViewOptions = { inline: "center", block: "nearest", behavior: "smooth" }
    indexRef.current?.children[index]?.scrollIntoView(opts)
    thumbsRef.current?.children[index]?.scrollIntoView(opts)
    new Image().src = images[(index + 1) % images.length]
  }, [index, images])

  const touchX = useRef<number | null>(null)
  const style = { "--c": project.color, "--t": project.textColor } as CSSProperties

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col bg-[#0d0d0d] text-white"
      style={style}
      initial={{ opacity: 0, scale: 1.02 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.02 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (touchX.current === null) return
        const dx = e.changedTouches[0].clientX - touchX.current
        touchX.current = null
        if (Math.abs(dx) > 50) go(index + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1)
      }}
    >
      <header className="flex h-16 shrink-0 items-center gap-6 pl-6">
        <h2 className="min-w-0 flex-1 truncate text-[clamp(18px,2.6vw,34px)] font-black uppercase text-[var(--c)]">
          {project.title}
        </h2>

        {/* Номера кадров с подчёркиванием активного (идея codrops/NavigationIndicators) */}
        <nav ref={indexRef} className="hidden max-w-[40vw] items-baseline overflow-hidden tabular-nums sm:flex">
          {images.map((_, k) => (
            <button
              key={k}
              type="button"
              onClick={() => go(k)}
              className={
                "relative px-[7px] pt-1 pb-2 text-[13px] font-bold transition-colors hover:text-white " +
                "after:absolute after:inset-x-[7px] after:bottom-[3px] after:h-0.5 after:origin-left after:bg-[var(--c)] after:transition-transform " +
                (k === index ? "text-[15px] text-[var(--c)] after:scale-x-100" : "text-neutral-600 after:scale-x-0")
              }
            >
              {pad(k + 1)}
            </button>
          ))}
        </nav>

        <a
          href={project.url}
          target="_blank"
          rel="noopener"
          className="hidden border-b-2 border-[var(--c)] pb-0.5 text-[13px] font-bold uppercase tracking-[0.06em] md:inline"
        >
          Пост в Telegram ↗
        </a>
        <button
          type="button"
          onClick={onClose}
          aria-label="Закрыть"
          className="h-16 w-16 shrink-0 bg-[var(--c)] text-4xl text-[var(--t)]"
        >
          ×
        </button>
      </header>

      <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden sm:px-[72px]">
        <button
          type="button"
          aria-label="Назад"
          onClick={() => go(index - 1, -1)}
          className="absolute inset-y-0 left-0 z-10 hidden w-[72px] text-4xl opacity-40 transition hover:text-[var(--c)] hover:opacity-100 sm:block"
        >
          ←
        </button>

        {/* Направленный слайд между кадрами (идея codrops/MultiLayoutSlideshow) */}
        <div
          className="relative h-full w-full"
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect()
            const left = e.clientX - r.left < r.width / 2
            go(index + (left ? -1 : 1), left ? -1 : 1)
          }}
        >
          <AnimatePresence initial={false} custom={dir}>
            <motion.img
              key={index}
              src={images[index]}
              alt={project.title}
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
              className="absolute inset-0 m-auto max-h-full max-w-full cursor-pointer object-contain"
              draggable={false}
            />
          </AnimatePresence>
        </div>

        <button
          type="button"
          aria-label="Вперёд"
          onClick={() => go(index + 1, 1)}
          className="absolute inset-y-0 right-0 z-10 hidden w-[72px] text-4xl opacity-40 transition hover:text-[var(--c)] hover:opacity-100 sm:block"
        >
          →
        </button>
      </div>

      <div ref={thumbsRef} className="flex shrink-0 gap-1.5 overflow-x-auto px-6 pt-3.5 pb-[18px] sm:justify-center">
        {images.map((src, k) => (
          <img
            key={src}
            src={src}
            alt=""
            onClick={() => go(k)}
            className={
              "h-16 w-24 shrink-0 cursor-pointer object-cover outline-3 -outline-offset-3 transition-opacity " +
              (k === index ? "opacity-100 outline-[var(--c)]" : "opacity-45 outline-transparent hover:opacity-85")
            }
          />
        ))}
      </div>
    </motion.div>
  )
}

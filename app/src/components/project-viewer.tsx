import { useEffect, useMemo, useState } from "react"
import { motion, useMotionValue } from "motion/react"
import { PhotoCarousel } from "@/components/photo-carousel"
import type { Project } from "@/data/projects"

type Props = {
  project: Project
  onClose: () => void
}

const pad = (n: number) => String(n).padStart(2, "0")

// Просмотр проекта: фото каруселью-кругом (PhotoCarousel).
export function ProjectViewer({ project, onClose }: Props) {
  const images = project.images
  const [current, setCurrent] = useState(0)
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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  // Смахнули вниз — окно проекта уезжает следом и закрывается
  const y = useMotionValue(0)

  const year = project.date.slice(0, 4)

  return (
    <motion.div
      className="fixed inset-0 z-50 flex touch-none flex-col bg-graphite text-white"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      style={{ y }}
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

      <div className="flex min-h-0 flex-1 flex-col pb-5 md:pb-6">
        <div className="min-h-0 flex-1">
          <PhotoCarousel
            items={items}
            label={`${project.title}: фото. Листай вбок, колесом или стрелками; смахни вниз, чтобы закрыть.`}
            pull={y}
            onClose={onClose}
            onIndex={setCurrent}
          />
        </div>

        <div className="flex items-baseline justify-between px-5 text-[11px] font-medium uppercase tracking-[0.1em] text-white/40 tabular-nums md:px-10 md:text-[13px]">
          <span>
            {pad(current + 1)} / {pad(images.length)} · {year}
          </span>
          <span className="hidden sm:inline">тяни вбок</span>
        </div>
      </div>
    </motion.div>
  )
}

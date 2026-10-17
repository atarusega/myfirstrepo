import { useState } from "react"
import { AnimatePresence } from "motion/react"
import { ArrowUpRight, Send } from "lucide-react"
import { ArtGallery } from "@/components/block/art-gallery"
import { BrandLogo, BrandMark } from "@/components/brand"
import { ProjectViewer } from "@/components/project-viewer"
import { captions, colors, covers, projects } from "@/data/projects"

const CHANNEL = "https://t.me/struktorum"
const PROFILE = "https://t.me/nkt_klmv"
// Кто и что — на первом экране (формулировка из отзыва, согласовать с Никитой)
const TAGLINE = "Никита Климов — 3D-визуализация бренд-зон и фестов"

// Ячейка галереи задаётся в долях высоты экрана. На вертикальном телефоне — ровно две целые колонки
// по центру (cellSize 0.5 при видимой ширине ≈0.92 высоты), дрейф только вверх, чтобы колонки не уезжали
// вбок, а после броска сетка сама встаёт по колонкам (snapX). Картинки там крупнее.
const isPortrait = () => window.innerWidth / window.innerHeight < 0.8
const MOBILE = { cellSize: 0.5, imageSize: 0.7, textSize: 0.075, drift: [0, 0.0005] as [number, number], snapX: true }
const DESKTOP = { cellSize: 0.75, imageSize: 0.64, textSize: 0.05, drift: undefined, snapX: false }

export default function App() {
  const [open, setOpen] = useState<number | null>(null)
  const [layout] = useState(() => (isPortrait() ? MOBILE : DESKTOP))

  return (
    <main className="flex h-full w-full flex-col bg-graphite">
      {/* Шапка по брендбуку: синяя полоса, логотип слева, кто и что — по центру, канал и кнопка справа */}
      <header className="z-10 flex h-16 shrink-0 items-center justify-between gap-3 bg-brand px-4 text-white sm:px-5 md:h-[72px] md:px-10">
        <a href="./" aria-label="STRUKTORUM — на главную" className="shrink-0">
          {/* На телефоне знак + мелкое слово; уже 400 px слово прячем — иначе не влезает кнопка «Обсудить» */}
          <span className="flex items-center gap-2 sm:hidden">
            <BrandMark size={26} />
            <span className="text-[14px] font-bold uppercase leading-none tracking-[0.08em] max-[399px]:hidden">Struktorum</span>
          </span>
          <span className="hidden sm:block">
            <BrandLogo size={36} />
          </span>
        </a>

        {/* На компьютере описание стоит в шапке; на телефоне оно плашкой поверх сетки (ниже) */}
        <h1 className="hidden min-w-0 flex-1 truncate text-[13px] font-medium leading-none tracking-[0.01em] text-white/80 md:block lg:text-[14px]">
          {TAGLINE}
        </h1>

        {/* Справа: канал — тихой ссылкой, личка — кнопкой */}
        <nav className="flex shrink-0 items-center gap-3 text-[11px] font-medium uppercase tracking-[0.06em] md:gap-6 md:text-[13px]">
          <a
            href={CHANNEL}
            target="_blank"
            rel="noopener"
            className="flex items-center gap-1 transition-opacity hover:opacity-70"
          >
            Канал
            <ArrowUpRight className="size-3.5 md:size-4" strokeWidth={2.25} aria-hidden="true" />
          </a>
          <a
            href={PROFILE}
            target="_blank"
            rel="noopener"
            aria-label="Обсудить проект с Никитой в Telegram"
            className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-white px-3 py-2 text-brand transition-colors hover:bg-brand-soft md:px-4"
          >
            <Send className="size-4" strokeWidth={2.25} aria-hidden="true" />
            <span className="sm:hidden">Обсудить</span>
            <span className="hidden sm:inline">Обсудить проект</span>
          </a>
        </nav>
      </header>

      <div className="relative min-h-0 flex-1">
        <ArtGallery
          images={covers}
          items={captions}
          colors={colors}
          cellSize={layout.cellSize}
          imageSize={layout.imageSize}
          textSize={layout.textSize}
          drift={layout.drift}
          snapX={layout.snapX}
          paused={open !== null}
          onSelect={setOpen}
          className="h-full"
        />
        {/* Телефон: описание плашкой поверх сетки, чтобы не отнимать высоту у плиток */}
        <p
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-3 z-10 w-max max-w-[calc(100%-2rem)] -translate-x-1/2 rounded-full bg-graphite/85 px-4 py-2 text-center text-[11px] font-medium leading-snug text-white/85 md:hidden"
        >
          {TAGLINE}
        </p>
      </div>

      <AnimatePresence>
        {open !== null && <ProjectViewer key={open} project={projects[open]} onClose={() => setOpen(null)} />}
      </AnimatePresence>
    </main>
  )
}

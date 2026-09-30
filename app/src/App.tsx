import { useState } from "react"
import { AnimatePresence } from "motion/react"
import { ArtGallery } from "@/components/block/art-gallery"
import { BrandLogo } from "@/components/brand"
import { ProjectViewer } from "@/components/project-viewer"
import { captions, covers, projects } from "@/data/projects"

// Ячейка галереи задаётся в долях высоты экрана: на вертикальном телефоне делаем её мельче,
// чтобы в ширину помещалось хотя бы две плитки. Там же картинки крупнее и сетка сама медленно плывёт.
const isPortrait = () => window.innerWidth / window.innerHeight < 0.8
const MOBILE = { cellSize: 0.42, imageSize: 0.74, drift: [0.0009, 0.0004] as [number, number] }
const DESKTOP = { cellSize: 0.75, imageSize: 0.64, drift: undefined }

export default function App() {
  const [open, setOpen] = useState<number | null>(null)
  const [layout] = useState(() => (isPortrait() ? MOBILE : DESKTOP))

  return (
    <main className="flex h-full w-full flex-col bg-graphite">
      {/* Шапка по брендбуку: синяя полоса, логотип слева, канал справа */}
      <header className="z-10 flex h-16 shrink-0 items-center justify-between bg-brand px-5 text-white md:h-[72px] md:px-10">
        <a href="./" aria-label="STRUKTORUM — на главную">
          <BrandLogo size={36} />
        </a>
        <a
          href="https://t.me/struktorum"
          target="_blank"
          rel="noopener"
          className="text-[11px] font-medium uppercase tracking-[0.06em] transition-opacity hover:opacity-70 md:text-[13px]"
        >
          <span className="hidden sm:inline">t.me/struktorum </span>→
        </a>
      </header>

      <ArtGallery
        images={covers}
        items={captions}
        cellSize={layout.cellSize}
        imageSize={layout.imageSize}
        drift={layout.drift}
        onSelect={setOpen}
        className="h-auto min-h-0 flex-1"
      />

      <AnimatePresence>
        {open !== null && <ProjectViewer key={open} project={projects[open]} onClose={() => setOpen(null)} />}
      </AnimatePresence>
    </main>
  )
}

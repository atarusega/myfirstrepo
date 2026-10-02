import { useState } from "react"
import { AnimatePresence } from "motion/react"
import { ArrowUpRight, Send } from "lucide-react"
import { ArtGallery } from "@/components/block/art-gallery"
import { BrandLogo, BrandMark } from "@/components/brand"
import { ProjectViewer } from "@/components/project-viewer"
import { captions, covers, projects } from "@/data/projects"

// Ячейка галереи задаётся в долях высоты экрана: на вертикальном телефоне делаем её мельче,
// чтобы в ширину помещалось хотя бы две плитки. Там же картинки крупнее и сетка сама медленно плывёт.
const CHANNEL = "https://t.me/struktorum"
const PROFILE = "https://t.me/nkt_klmv"

const isPortrait = () => window.innerWidth / window.innerHeight < 0.8
const MOBILE = { cellSize: 0.42, imageSize: 0.7, textSize: 0.075, drift: [0.0009, 0.0004] as [number, number] }
const DESKTOP = { cellSize: 0.75, imageSize: 0.64, textSize: 0.05, drift: undefined }

export default function App() {
  const [open, setOpen] = useState<number | null>(null)
  const [layout] = useState(() => (isPortrait() ? MOBILE : DESKTOP))

  return (
    <main className="flex h-full w-full flex-col bg-graphite">
      {/* Шапка по брендбуку: синяя полоса, логотип слева, канал справа */}
      <header className="z-10 flex h-16 shrink-0 items-center justify-between gap-3 bg-brand px-4 text-white sm:px-5 md:h-[72px] md:px-10">
        <a href="./" aria-label="STRUKTORUM — на главную" className="shrink-0">
          {/* На телефоне знак + мелкое слово; на совсем узком экране только знак */}
          <span className="flex items-center gap-2 sm:hidden">
            <BrandMark size={26} />
            <span className="text-[14px] font-bold uppercase leading-none tracking-[0.08em] max-[339px]:hidden">Struktorum</span>
          </span>
          <span className="hidden sm:block">
            <BrandLogo size={36} />
          </span>
        </a>

        {/* Справа: канал — тихой ссылкой, личка — кнопкой */}
        <nav className="flex items-center gap-3 text-[11px] font-medium uppercase tracking-[0.06em] md:gap-6 md:text-[13px]">
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
            aria-label="Написать Никите в Telegram"
            className="flex items-center gap-1.5 rounded-full bg-white p-2.5 text-brand transition-colors hover:bg-brand-soft sm:px-3 sm:py-2 md:px-4"
          >
            <Send className="size-4" strokeWidth={2.25} aria-hidden="true" />
            <span className="hidden sm:inline">Написать</span>
          </a>
        </nav>
      </header>

      <ArtGallery
        images={covers}
        items={captions}
        cellSize={layout.cellSize}
        imageSize={layout.imageSize}
        textSize={layout.textSize}
        drift={layout.drift}
        paused={open !== null}
        onSelect={setOpen}
        className="h-auto min-h-0 flex-1"
      />

      <AnimatePresence>
        {open !== null && <ProjectViewer key={open} project={projects[open]} onClose={() => setOpen(null)} />}
      </AnimatePresence>
    </main>
  )
}

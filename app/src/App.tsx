import { useState } from "react"
import { AnimatePresence } from "motion/react"
import { ArtGallery } from "@/components/block/art-gallery"
import { ProjectViewer } from "@/components/project-viewer"
import { captions, covers, projects } from "@/data/projects"

export default function App() {
  const [open, setOpen] = useState<number | null>(null)

  return (
    <main className="relative h-full w-full">
      <ArtGallery images={covers} items={captions} onSelect={setOpen} className="h-full" />

      <header className="pointer-events-none absolute inset-x-0 top-0 z-10 flex h-16 items-center justify-between px-6">
        <span className="text-xl font-black tracking-[0.04em]">STRUKTORUM</span>
        <a
          href="https://t.me/struktorum"
          target="_blank"
          rel="noopener"
          className="pointer-events-auto text-[13px] font-bold uppercase tracking-[0.06em] text-white/70 transition-colors hover:text-white"
        >
          t.me/struktorum →
        </a>
      </header>

      <AnimatePresence>
        {open !== null && <ProjectViewer key={open} project={projects[open]} onClose={() => setOpen(null)} />}
      </AnimatePresence>
    </main>
  )
}

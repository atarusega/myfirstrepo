import raw from "./projects.json"

export type Project = {
  id: number
  title: string
  text: string[]
  date: string
  url: string
  images: string[]
  color: string
  textColor: string
  sizes: [number, number][]
}

export const projects = raw as Project[]

// Для галереи: по одной обложке и подписи на проект (стабильные массивы — сцена не пересобирается)
export const covers = projects.map((p) => p.images[0])
export const captions = projects.map((p) => ({ title: p.title, year: p.date.slice(0, 4) }))

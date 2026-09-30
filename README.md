# STRUKTORUM — портфолио

Сайт-портфолио Никиты Климова: 3D-визуализация событийных пространств.
Опубликован на https://struktorum.space (GitHub Pages).

## Как устроено

- `app/` — React + Vite + Tailwind. Главная — бесконечная WebGL-галерея
  (`app/src/components/block/art-gallery.jsx`, основа — ObsidianUI Art Gallery),
  клик по плитке открывает просмотр проекта (`app/src/components/project-viewer.tsx`).
- `app/src/data/projects.json` — проекты: название, фото, цвет подписи.
- `app/public/images/<id>/` — фото проектов.
- `tools/sync_telegram.py` — тянет посты из t.me/struktorum, качает фото
  и пересобирает `projects.json`. Новый проект — добавить id поста в `POSTS`.

## Команды

```bash
python tools/sync_telegram.py   # обновить проекты из Telegram
cd app && npm install           # один раз
npm run dev                     # локально, http://localhost:5173
npm run build                   # сборка в app/dist
```

Публикация автоматическая: пуш в `claude/portfolio-site-mvp-suuwg4` запускает
`.github/workflows/deploy.yml`, который собирает `app/` и выкладывает на Pages.

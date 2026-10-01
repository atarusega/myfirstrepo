from html import escape

from app.dictionaries import GENRES, INSTRUMENTS, LINEUPS, PROGRAM_FORMATS, SERVICES, SOUND, TRAVEL, labels
from app.utils import fmt_money

STATUS_LABELS = {
    "draft": "черновик",
    "pending": "на модерации",
    "published": "опубликована",
    "rejected": "отклонена",
    "archived": "в архиве",
}


def trust_line(band, recs: dict[str, int] | None) -> str:
    recs = recs or {}
    marks = []
    if band.source == "tutvse":
        marks.append("✅ Резидент «Тут все»")
    if recs.get("tutvse"):
        marks.append(f"👍 Рекомендуют резиденты «Тут все» ({recs['tutvse']})")
    if recs.get("producer"):
        marks.append(f"⭐ Рекомендуют продюсеры ({recs['producer']})")
    return "\n".join(marks)


def band_card(band, recs=None, reason: str | None = None, price: int | None = None, full: bool = False) -> str:
    g = lambda v: escape(str(v)) if v else "—"  # noqa: E731
    lines = [f"<b>🎸 {g(band.name)}</b>"]
    lineup = LINEUPS.get(band.lineup, "")
    instr = labels(band.instruments, INSTRUMENTS)
    lines.append(f"👥 {escape(lineup)}{': ' + escape(instr) if instr else ''}")
    lines.append(f"🎵 {escape(labels(band.genres, GENRES)) or '—'}")
    city = g(band.city)
    if band.travel_scope and band.travel_scope != "city":
        city += f" ({TRAVEL[band.travel_scope].lower()})"
    lines.append(f"📍 {city}")
    if price is not None and not full:
        lines.append(f"💰 от {fmt_money(price)}")
    else:
        lines.append(
            "💰 Частное: {} · Корпоратив: {} · Новый год: {}".format(
                fmt_money(band.price_private), fmt_money(band.price_corporate), fmt_money(band.price_newyear)
            )
        )
    extras = []
    if band.program_format:
        extras.append(PROGRAM_FORMATS.get(band.program_format, band.program_format))
    if band.sound:
        extras.append(SOUND.get(band.sound, band.sound))
    if extras:
        lines.append("🎛 " + escape(" · ".join(extras)))
    if band.services:
        lines.append("➕ " + escape(labels(band.services, SERVICES)))
    if full and band.description:
        lines.append(f"\n{escape(band.description[:600])}")
    if band.video_links:
        vids = " ".join(f'<a href="{escape(u)}">видео {i + 1}</a>' for i, u in enumerate(band.video_links[:3]))
        lines.append(f"▶️ {vids}")
    t = trust_line(band, recs)
    if t:
        lines.append(t)
    if reason:
        lines.append(f"\n<i>💡 {escape(reason)}</i>")
    return "\n".join(lines)


def contact_card(band) -> str:
    lines = [f"<b>Контакты: {escape(band.name)}</b>"]
    if band.tg_username:
        lines.append(f"Telegram: @{escape(band.tg_username)}")
    elif band.tg_user_id:
        lines.append(f'Telegram: <a href="tg://user?id={band.tg_user_id}">написать</a>')
    if band.phone:
        lines.append(f"Телефон: {escape(band.phone)}")
    if band.website:
        lines.append(f"Сайт/соцсети: {escape(band.website)}")
    lines.append("\nСкажите, что нашли через бота — так группы охотнее отвечают быстро 🙂")
    return "\n".join(lines)

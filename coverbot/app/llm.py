import json
import logging
import re
from datetime import date

from anthropic import AsyncAnthropic

from app.config import settings
from app.criteria import Criteria, fallback_parse
from app.dictionaries import EVENT_TYPES, GENRES, INSTRUMENTS, LINEUPS, SERVICES, labels

log = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def client() -> AsyncAnthropic | None:
    global _client
    if not settings.anthropic_api_key:
        return None
    if _client is None:
        _client = AsyncAnthropic(
            api_key=settings.anthropic_api_key, base_url=settings.anthropic_base_url, timeout=25
        )
    return _client


def _codes(d: dict) -> str:
    return "; ".join(f"{k} = {v}" for k, v in d.items())


PARSE_SYSTEM = """Ты разбираешь запросы ивент-продюсеров, которые ищут кавер-группу для мероприятия.
Верни ТОЛЬКО JSON-объект, без пояснений и без markdown.

Схема:
{{"event_type": "private"|"corporate"|"newyear"|null,
 "budget": целое число в рублях или null,
 "budget_any": true|false,
 "city": "город в именительном падеже" или null,
 "genres": [коды жанров],
 "date": "YYYY-MM-DD" или null,
 "guests": целое число или null,
 "instruments": [коды инструментов],
 "lineup": [коды состава],
 "need_sound": true|false|null,
 "services": [коды услуг],
 "free_text": "всё важное, что не легло в поля" или null}}

Типы событий: {events}
Жанры: {genres}
Инструменты: {instruments}
Состав: {lineups}
Услуги: {services}

Правила:
- «120к», «120 тыс», «120 000» → 120000. Бюджет «не важно», «любой» → budget_any=true, budget=null.
- Свадьба, день рождения, юбилей, выпускной, частная вечеринка → private. Новогодний корпоратив, праздник в конце декабря → newyear.
- «Подмосковье» → "Московская область". Сокращения городов раскрывай: мск → Москва, спб/питер → Санкт-Петербург.
- Используй только коды из списков. Не придумывай то, чего нет в сообщении.
- «чтобы была своя аппаратура/свой звук» → need_sound=true.
- Если передан предыдущий JSON, обнови его по новому сообщению: поля, которые пользователь не менял, сохрани как есть.
- Сегодня {today}. Дату без года относи к ближайшему будущему.
"""

EXPLAIN_SYSTEM = """Ты помогаешь продюсеру выбрать кавер-группу. Для каждой группы напиши одну короткую строку
(до 110 символов) — почему она подходит под запрос. Опирайся ТОЛЬКО на данные карточки и запроса, ничего не выдумывай.
Если группа подходит частично (например, дороже бюджета), честно укажи это.
Верни ТОЛЬКО JSON: {"<id>": "строка", ...}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


async def parse_request(text: str, previous: Criteria | None = None) -> Criteria:
    c = client()
    if c is None:
        return fallback_parse(text, previous)
    system = PARSE_SYSTEM.format(
        events=_codes(EVENT_TYPES),
        genres=_codes(GENRES),
        instruments=_codes(INSTRUMENTS),
        lineups=_codes(LINEUPS),
        services=_codes(SERVICES),
        today=date.today().isoformat(),
    )
    prev = previous.model_dump_json() if previous else "нет"
    try:
        resp = await c.messages.create(
            model=settings.llm_model,
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": f"Предыдущий JSON: {prev}\n\nСообщение продюсера: {text}"}],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return Criteria(**_extract_json(raw))
    except Exception as e:  # noqa: BLE001 — бот не должен падать из-за LLM
        log.warning("LLM parse failed, fallback: %s", e)
        return fallback_parse(text, previous)


def template_reason(band, crit: Criteria, price: int | None) -> str:
    parts = []
    common = [g for g in crit.genres if g in (band.genres or [])]
    if common:
        parts.append(labels(common, GENRES))
    if crit.instruments and all(i in (band.instruments or []) for i in crit.instruments):
        parts.append("есть " + labels(crit.instruments, INSTRUMENTS).lower())
    if crit.need_sound and band.sound == "included":
        parts.append("свой звук в цене")
    if crit.budget and price:
        parts.append("в бюджете" if price <= crit.budget else "чуть выше бюджета")
    common_s = [s for s in crit.services if s in (band.services or [])]
    if common_s:
        parts.append(labels(common_s, SERVICES).lower())
    return ", ".join(parts).capitalize() if parts else "Подходит по городу и бюджету"


async def explain(crit: Criteria, items: list[tuple]) -> dict[int, str]:
    """items: [(band, score, price)]. Возвращает {band_id: причина}."""
    fallback = {b.id: template_reason(b, crit, p) for b, _, p in items}
    c = client()
    if c is None or not items:
        return fallback
    cards = [
        {
            "id": b.id,
            "name": b.name,
            "city": b.city,
            "genres": labels(b.genres, GENRES),
            "instruments": labels(b.instruments, INSTRUMENTS),
            "price_for_event": p,
            "sound": b.sound,
            "services": labels(b.services, SERVICES),
            "description": (b.description or "")[:300],
        }
        for b, _, p in items
    ]
    try:
        resp = await c.messages.create(
            model=settings.llm_model,
            max_tokens=600,
            system=EXPLAIN_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Запрос: {crit.model_dump_json()}\n\nГруппы: {json.dumps(cards, ensure_ascii=False)}",
            }],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        data = _extract_json(raw)
        return {int(k): str(v)[:160] for k, v in data.items()} | {
            k: v for k, v in fallback.items() if str(k) not in data
        }
    except Exception as e:  # noqa: BLE001
        log.warning("LLM explain failed: %s", e)
        return fallback

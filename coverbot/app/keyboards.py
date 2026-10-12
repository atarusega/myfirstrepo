from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.dictionaries import BUDGET_OPTIONS, PRICE_PRESETS, TOP_CITIES
from app.utils import fmt_short

# кнопки под полем ввода на шаге «Телефон» приходят обычным текстом
PHONE_SHARE = "📱 Поделиться номером"
PHONE_KEEP = "Оставить текущий"
PHONE_SKIP = "Пропустить"
BACK_TEXT = "← Назад"


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Ищу кавер-группу", callback_data="role:search")
    kb.button(text="🎸 Я музыкант — добавить группу", callback_data="role:band")
    kb.button(text="💬 Написать в поддержку", callback_data="support")
    kb.adjust(1)
    return kb.as_markup()


def single_select(options: dict, current: str | None = None, cols: int = 1) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, label in options.items():
        mark = "✓ " if code == current else ""
        kb.button(text=f"{mark}{label}", callback_data=f"ss:{code}")
    kb.adjust(cols)
    return kb.as_markup()


def multi_select(options: dict, selected: list[str], cols: int = 2) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, label in options.items():
        mark = "✅ " if code in selected else ""
        kb.button(text=f"{mark}{label}", callback_data=f"ms:{code}")
    kb.adjust(cols)
    done = InlineKeyboardBuilder()
    done.button(text="Готово ➡️", callback_data="ms_done")
    kb.attach(done)
    return kb.as_markup()


def keep_or_skip(current: str | None = None, skip_text: str | None = None) -> InlineKeyboardMarkup | None:
    kb = InlineKeyboardBuilder()
    if current:
        kb.button(text=f"Оставить: {str(current)[:40]}", callback_data="keep")
    if skip_text:
        kb.button(text=skip_text, callback_data="skip")
    kb.adjust(1)
    return kb.as_markup() if (current or skip_text) else None


def with_rows(markup: InlineKeyboardMarkup | None, *rows: tuple[str, str], back: bool = False
              ) -> InlineKeyboardMarkup | None:
    """Добавить снизу кнопки по одной в ряд и «← Назад» последней."""
    buttons = [list(r) for r in (markup.inline_keyboard if markup else [])]
    buttons += [[InlineKeyboardButton(text=t, callback_data=c)] for t, c in rows]
    if back:
        buttons.append([InlineKeyboardButton(text=BACK_TEXT, callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def city_select(current: str | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, label in TOP_CITIES.items():
        mark = "✓ " if label == current else ""
        kb.button(text=f"{mark}{label}", callback_data=f"ct:{code}")
    kb.button(text="Другой город ✍️", callback_data="ct_other")
    kb.adjust(2)
    return kb.as_markup()


def price_select(current: int | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for value in PRICE_PRESETS:
        mark = "✓ " if value == current else ""
        plus = "+" if value == PRICE_PRESETS[-1] else ""
        kb.button(text=f"{mark}от {fmt_short(value)}{plus}", callback_data=f"pr:{value}")
    kb.button(text="Ввести точно ✍️", callback_data="pr_exact")
    kb.adjust(3, 3, 1, 1)
    return kb.as_markup()


def phone_kb(current: str | None, can_skip: bool, back: bool) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=PHONE_SHARE, request_contact=True)]]
    extra = ([PHONE_KEEP] if current else []) + ([PHONE_SKIP] if can_skip else []) + ([BACK_TEXT] if back else [])
    if extra:
        rows.append([KeyboardButton(text=t) for t in extra])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True,
                               input_field_placeholder="+7 999 123-45-67")


def consent_intro_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Согласен, начать анкету", callback_data="cs:ok")
    kb.button(text="📄 Полный текст согласия", callback_data="cs:full")
    kb.button(text="Не сейчас", callback_data="cs:no")
    kb.adjust(1)
    return kb.as_markup()


def preview_kb(has_video: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_video:
        kb.button(text="✅ Отправить на модерацию", callback_data="pv:send")
    else:
        kb.button(text="💾 Сохранить, видео пришлю позже", callback_data="pv:send")
    kb.button(text="✏️ Исправить поле", callback_data="pv:fix")
    kb.button(text="Отмена", callback_data="pv:cancel")
    kb.adjust(1)
    return kb.as_markup()


def fields_kb(labels: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, label in enumerate(labels):
        kb.button(text=label, callback_data=f"fx:{i}")
    kb.adjust(2)
    return with_rows(kb.as_markup(), (BACK_TEXT, "fx_back"))


def delete_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Да, удалить всё", callback_data="del:yes")
    kb.button(text="Нет, оставить", callback_data="del:no")
    kb.adjust(1)
    return kb.as_markup()


def budget_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for value, label in BUDGET_OPTIONS:
        kb.button(text=label, callback_data=f"bud:{value}")
    kb.adjust(3, 2)
    return kb.as_markup()


def city_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in ("Москва", "Московская область", "Санкт-Петербург"):
        kb.button(text=city, callback_data=f"city:{city}")
    kb.adjust(1)
    return kb.as_markup()


def band_result_kb(band_id: int, req_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📞 Показать контакт", callback_data=f"lead:{band_id}:{req_id}")
    return kb.as_markup()


def results_nav_kb(has_more: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_more:
        kb.button(text="Ещё варианты", callback_data="srch:more")
    kb.button(text="✏️ Уточнить запрос", callback_data="srch:refine")
    kb.button(text="🔄 Новый поиск", callback_data="srch:new")
    kb.adjust(1)
    return kb.as_markup()


def recommend_kb(band_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Работал(а) с ними, рекомендую", callback_data=f"rec:{band_id}")
    return kb.as_markup()


def my_band_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Исправить поле", callback_data="band:fix")
    kb.button(text="✅ Цены актуальны", callback_data="band:confirm")
    kb.button(text="🔄 Пройти анкету заново", callback_data="band:edit")
    kb.button(text="💬 Поддержка", callback_data="support")
    kb.button(text="🗑 Удалить мои данные", callback_data="band:delete")
    kb.adjust(1)
    return kb.as_markup()


def video_reminder_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Добавить видео", callback_data="band:video")
    return kb.as_markup()


def price_reminder_kb(band_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Цены актуальны", callback_data=f"pc:{band_id}")
    kb.button(text="✏️ Поменять цены", callback_data="band:prices")
    kb.adjust(1)
    return kb.as_markup()


def moderation_kb(band_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"adm:ok:{band_id}")
    kb.button(text="❌ Видео не открывается", callback_data=f"adm:rej:{band_id}:video")
    kb.button(text="❌ Неполные данные", callback_data=f"adm:rej:{band_id}:data")
    kb.button(text="❌ Не кавер-группа", callback_data=f"adm:rej:{band_id}:scope")
    kb.adjust(1)
    return kb.as_markup()


def claim_kb(token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, это я — дозаполнить", callback_data=f"claim:yes:{token}")
    kb.button(text="Нет, не я", callback_data="claim:no")
    kb.adjust(1)
    return kb.as_markup()

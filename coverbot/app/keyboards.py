from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.dictionaries import BUDGET_OPTIONS


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Ищу кавер-группу", callback_data="role:search")
    kb.button(text="🎸 Я музыкант — добавить группу", callback_data="role:band")
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


def consent_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Согласен, отправить на модерацию", callback_data="consent:yes")
    kb.button(text="✏️ Заполнить заново", callback_data="consent:restart")
    kb.button(text="Отмена", callback_data="consent:cancel")
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
    kb.button(text="✏️ Обновить анкету", callback_data="band:edit")
    kb.button(text="✅ Цены актуальны", callback_data="band:confirm")
    kb.adjust(1)
    return kb.as_markup()


def price_reminder_kb(band_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Цены актуальны", callback_data=f"pc:{band_id}")
    kb.button(text="✏️ Обновить анкету", callback_data="band:edit")
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

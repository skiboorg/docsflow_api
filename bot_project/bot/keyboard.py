from telegram import ReplyKeyboardMarkup

def generate_keyboard(rows):
    if not rows:
        return None, None

    # Берём роль первой строки
    role_name = rows[0]['role_name']

    # Объединяем права (если несколько permission)
    can_view = any(r['can_view'] for r in rows)
    can_add = any(r['can_add'] for r in rows)
    can_edit = any(r['can_edit'] for r in rows)
    can_delete = any(r['can_delete'] for r in rows)

    buttons = []
    if can_view: buttons.append(["Список компаний"])
    if can_add: buttons.append(["➕ Добавить"])
    if can_add: buttons.append(["➕ Добавить файл"])
    if can_edit: buttons.append(["✏️ Редактировать"])
    if can_delete: buttons.append(["🗑 Удалить"])

    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True) if buttons else None
    return role_name, keyboard

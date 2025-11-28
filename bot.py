import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import sqlite3

# Настройки
BOT_TOKEN = "8245945626:AAFoGNoWP-JZTRUt9AdoYF9T891GCDXOGlo"
DEAN_USER_ID = 6224232118  # ID проректора в Telegram

# Состояния диалога
CATEGORY, NAME, FACULTY, CONTACT, TEACHER_SUBJECT, PARENT_STUDENT_NAME, CONTENT, DEAN_RESPONSE = range(8)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS complaints
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  category TEXT,
                  full_name TEXT,
                  faculty TEXT,
                  contact TEXT,
                  teacher_subject TEXT,
                  parent_student_name TEXT,
                  message_type TEXT,
                  content TEXT,
                  file_id TEXT,
                  dean_response TEXT)''')
    conn.commit()
    conn.close()

# Функция для очистки Markdown символов
def clean_markdown(text):
    if not text:
        return text
    # Экранируем специальные символы Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Команда старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем, это проректор или обычный пользователь
    if user_id == DEAN_USER_ID:
        # Это проректор - показываем только приветствие
        await update.message.reply_text(
            "👋 Assalomu Alaykum!\n\n"
            "Savollar va Takliflar hozircha yo'q, agar bo'lsa ular albatta sizga etib keladi📖."
        )
        return ConversationHandler.END
    else:
        # Это обычный пользователь - показываем выбор категории
        await show_category_selection(update, context)
        return CATEGORY

# Показ выбора категории
async def show_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👨‍🎓 Talaba", callback_data="student")],
        [InlineKeyboardButton("👩‍🏫 O'qituvchi", callback_data="teacher")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Ota-ona", callback_data="parent")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Murojaatlar tizimiga xush kelibsiz!\n\n"
        "Iltimos, ozingiz haqida malumotlarni to'ldiring:",
        reply_markup=reply_markup
    )

# Обработка выбора категории
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category = query.data
    context.user_data['category'] = category
    
    if category == "student":
        await query.edit_message_text(
            "👨‍🎓 Siz Talaba ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:"
        )
        return NAME
        
    elif category == "teacher":
        await query.edit_message_text(
            "👩‍🏫 Siz O'qituvchi ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:"
        )
        return NAME
        
    elif category == "parent":
        await query.edit_message_text(
            "👨‍👩‍👧‍👦 Siz Ota-ona ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:"
        )
        return NAME

# Получение ФИО
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    category = context.user_data['category']
    
    if category == "student":
        await update.message.reply_text("Fakultet va guruhingizni kiriting:")
        return FACULTY
    elif category == "teacher":
        await update.message.reply_text("Fan yoki mutaxassisligingizni kiriting:")
        return TEACHER_SUBJECT
    elif category == "parent":
        await update.message.reply_text("Farzandingiz (talaba) F.I.O sini kiriting:")
        return PARENT_STUDENT_NAME

# Получение предмета для преподавателя
async def get_teacher_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['teacher_subject'] = update.message.text
    await update.message.reply_text("Kontakt ma'lumotlaringizni kiriting (email yoki telefon):")
    return CONTACT

# Получение ФИО студента для родителя
async def get_parent_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['parent_student_name'] = update.message.text
    await update.message.reply_text("Farzandingizning fakultet va guruhini kiriting:")
    return FACULTY

# Получение факультета
async def get_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['faculty'] = update.message.text
    category = context.user_data['category']
    
    if category == "parent":
        await update.message.reply_text("Kontakt ma'lumotlaringizni kiriting (email yoki telefon):")
        return CONTACT
    elif category == "teacher":
        await update.message.reply_text("Kontakt ma'lumotlaringizni kiriting (email yoki telefon):")
        return CONTACT
    else:  # student - сразу переходим к контенту
        await update.message.reply_text(
            "✅ Ajoyib! Ma'lumotlar saqlandi.\n\n"
            "Endi murojaatingizni yuboring:\n"
            "Sizning barcha materiallaringiz yo'naltiriladi."
        )
        return CONTENT

# Получение контактов (только для преподавателей и родителей)
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contact'] = update.message.text
    
    category = context.user_data['category']
    category_name = get_category_name(category)
    
    await update.message.reply_text(
        f"✅ Ajoyib! Ma'lumotlar saqlandi.\n\n"
        f"Kategoriya: {category_name}\n\n"
        "Endi murojaatingizni yuboring:\n"
        "Sizning barcha materiallaringiz yo'naltiriladi."
    )
    return CONTENT

# Обработка контента
async def handle_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Ko'rsatilmagan"
    
    # Проверяем тип сообщения - разрешены только текст и фото
    if update.message.voice or update.message.audio or update.message.video:
        await update.message.reply_text(
            "❌ Kechirasiz, faqat matnli xabarlar va rasmlar qabul qilinadi.\n\n"
            "Iltimos, murojaatingizni matn shaklida yuboring yoki rasm jo'nating."
        )
        return CONTENT
    
    # Сохраняем обращение в базу данных
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    
    message_type = "text"
    content = ""
    file_id = ""
    
    if update.message.text:
        message_type = "text"
        content = update.message.text
    elif update.message.photo:
        message_type = "photo"
        file_id = update.message.photo[-1].file_id
        content = update.message.caption or "Rasm"
    elif update.message.document:
        # Проверяем, является ли документ изображением
        if update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
            message_type = "photo"
            file_id = update.message.document.file_id
            content = update.message.caption or "Rasm"
        else:
            await update.message.reply_text(
                "❌ Kechirasiz, faqat rasmlar qabul qilinadi. Boshqa turdagi fayllar qabul qilinmaydi.\n\n"
                "Iltimos, murojaatingizni matn shaklida yuboring yoki rasm jo'nating."
            )
            return CONTENT
    
    # Для студентов устанавливаем пустые контакты
    if user_data['category'] == "student":
        user_data['contact'] = "Ko'rsatilmagan"
    
    # Сохраняем все данные в базу
    c.execute('''INSERT INTO complaints 
                 (user_id, username, category, full_name, faculty, contact, teacher_subject, parent_student_name, message_type, content, file_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, 
               username,
               user_data['category'],
               user_data['full_name'], 
               user_data.get('faculty', ''), 
               user_data.get('contact', 'Ko\'rsatilmagan'),
               user_data.get('teacher_subject', ''),
               user_data.get('parent_student_name', ''),
               message_type, content, file_id))
    conn.commit()
    conn.close()
    
    # Отправляем обращение проректору (ВСЕ В ОДНОМ СООБЩЕНИИ)
    await send_to_dean(update, context, user_data, message_type, content, file_id, username)
    
    # Возвращаем к выбору категории
    await update.message.reply_text(
        "✅ Murojaatingiz muvaffaqiyatli yuborildi!\n"
        "Universitet rivojiga qo'shgan hissangiz uchun rahmat.\n\n"
        "Yangi murojaat yuborish uchun /start dan foydalaning."
    )
    
    return ConversationHandler.END

# Отправка обращения проректору (ВСЕ В ОДНОМ СООБЩЕНИИ)
async def send_to_dean(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, message_type, content, file_id, username):
    try:
        category = user_data['category']
        category_name = get_category_name(category)
        user_id = update.effective_user.id
        
        # Получаем ID последнего обращения для кнопки ответа
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute('SELECT id FROM complaints WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        last_complaint = c.fetchone()
        complaint_id = last_complaint[0] if last_complaint else None
        conn.close()
        
        # Очищаем все текстовые поля от Markdown символов
        clean_full_name = clean_markdown(user_data['full_name'])
        clean_username = clean_markdown(username)
        clean_teacher_subject = clean_markdown(user_data.get('teacher_subject', ''))
        clean_contact = clean_markdown(user_data.get('contact', ''))
        clean_parent_student_name = clean_markdown(user_data.get('parent_student_name', ''))
        clean_faculty = clean_markdown(user_data.get('faculty', ''))
        clean_content = clean_markdown(content)
        
        # Формируем полное сообщение с информацией и контентом
        full_message = (
            f"📨 **YANGI MUROJAAT**\n\n"
            f"**📋 Murojatchi turi:** {category_name}\n"
            f"**👤 F.I.O:** {clean_full_name}\n"
            f"**🔗 Telegram:** @{clean_username}\n"
        )
        
        if category == "teacher":
            full_message += f"**📚 Fan/Mutaxassislik:** {clean_teacher_subject}\n"
            full_message += f"**📞 Kontaktlar:** {clean_contact}\n"
        elif category == "parent":
            full_message += f"**👶 Talaba F.I.O:** {clean_parent_student_name}\n"
            full_message += f"**🎓 Fakultet/Guruh:** {clean_faculty}\n"
            full_message += f"**📞 Kontaktlar:** {clean_contact}\n"
        else:  # student
            full_message += f"**🎓 Fakultet/Guruh:** {clean_faculty}\n"
            # Для студентов не показываем контакты
        
        # Добавляем контент обращения
        if message_type == "text":
            full_message += f"**📝 MUROJAAT MATNI:**\n\n{clean_content}"
            
            # Создаем кнопку ответа
            keyboard = [
                [InlineKeyboardButton("📝 Javob yozish", callback_data=f"reply_{complaint_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем одно сообщение с текстом
            await context.bot.send_message(
                chat_id=DEAN_USER_ID,
                text=full_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif message_type == "photo":
            # Для фото - отправляем информацию и фото в одном сообщении
            keyboard = [
                [InlineKeyboardButton("📝 Javob yozish", callback_data=f"reply_{complaint_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            photo_caption = full_message + (f"\n\n**Tavsif:** {clean_content}" if content else "")
            
            await context.bot.send_photo(
                chat_id=DEAN_USER_ID,
                photo=file_id,
                caption=photo_caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"Yuborishda xatolik: {e}")

# Обработка кнопки "Ответить"
async def handle_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    complaint_id = query.data.split('_')[1]
    
    # Сохраняем ID обращения для ответа
    context.user_data['reply_complaint_id'] = complaint_id
    
    # Получаем информацию об обращении
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, username, full_name, category FROM complaints WHERE id = ?''', (complaint_id,))
    complaint = c.fetchone()
    conn.close()
    
    if complaint:
        user_id, username, full_name, category = complaint
        context.user_data['reply_user_id'] = user_id
        context.user_data['reply_username'] = username
        
        # Очищаем данные от Markdown
        clean_full_name = clean_markdown(full_name)
        clean_username = clean_markdown(username)
        clean_category = get_category_name(category)
        
        await query.edit_message_text(
            f"📝 **Javob yozish**\n\n"
            f"**Kimga:** {clean_full_name}\n"
            f"**Kategoriya:** {clean_category}\n"
            f"**Telegram:** @{clean_username}\n\n"
            f"Iltimos, javobingizni yuboring:",
            parse_mode='Markdown'
        )
        
        return DEAN_RESPONSE
    else:
        await query.edit_message_text("❌ Murojaat topilmadi!")
        return ConversationHandler.END

# Обработка ответа проректора
async def handle_dean_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    complaint_id = user_data.get('reply_complaint_id')
    target_user_id = user_data.get('reply_user_id')
    username = user_data.get('reply_username')
    
    if not complaint_id or not target_user_id:
        await update.message.reply_text("❌ Xatolik yuz berdi!")
        return ConversationHandler.END
    
    dean_response = update.message.text
    
    try:
        # Очищаем ответ от Markdown символов
        clean_dean_response = clean_markdown(dean_response)
        clean_username = clean_markdown(username)
        
        # Сохраняем ответ в базу данных
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute('''UPDATE complaints 
                     SET dean_response = ?
                     WHERE id = ?''', 
                  (dean_response, complaint_id))
        conn.commit()
        conn.close()
        
        # Отправляем ответ пользователю
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📬 **Sizga javob keldi!**\n\n"
                 f"**Prorektor:** {clean_dean_response}",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            f"✅ Javob muvaffaqiyatli yuborildi!\n"
            f"**Foydalanuvchi:** @{clean_username}\n"
            f"**Javob:** {clean_dean_response}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"Javob yuborishda xatolik: {e}")
        await update.message.reply_text("❌ Javob yuborishda xatolik yuz berdi!")
    
    return ConversationHandler.END

def get_category_name(category):
    if category == "student":
        return "👨‍🎓 Talaba"
    elif category == "teacher":
        return "👩‍🏫 O'qituvchi"
    elif category == "parent":
        return "👨‍👩‍👧‍👦 Ota-ona"
    return category

# Обработка кнопки "Читать обращения" для проректора
async def dean_read_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Получаем все обращения из базы данных
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM complaints ORDER BY id DESC''')
    all_complaints = c.fetchall()
    conn.close()
    
    if not all_complaints:
        await query.edit_message_text(
            "📭 Hozircha murojaatlar yo'q.",
        )
        return
    
    # Создаем счетчик для отслеживания текущей позиции
    if 'dean_current_index' not in context.user_data:
        context.user_data['dean_current_index'] = 0
        context.user_data['dean_complaints'] = all_complaints
    
    current_index = context.user_data['dean_current_index']
    complaints = context.user_data['dean_complaints']
    
    # Показываем обращения по 10 штук
    start_index = current_index
    end_index = min(current_index + 10, len(complaints))
    
    message_text = f"📨 Murojaatlar {start_index + 1}-{end_index} dan {len(complaints)}:\n\n"
    
    for i in range(start_index, end_index):
        complaint = complaints[i]
        
        # Очищаем текст от Markdown символов
        clean_category = get_category_name(complaint[3])
        clean_full_name = clean_markdown(complaint[4])
        clean_username = clean_markdown(complaint[2])
        clean_teacher_subject = clean_markdown(complaint[7])
        clean_contact = clean_markdown(complaint[6])
        clean_parent_student_name = clean_markdown(complaint[8])
        clean_faculty = clean_markdown(complaint[5])
        clean_content = clean_markdown(complaint[10])
        clean_response = clean_markdown(complaint[13]) if complaint[13] else None
        
        # Форматируем сообщение с большими пробелами для лучшей читаемости
        message_text += "═══════════════════════════\n"
        message_text += f"KATEGORIYA: {clean_category}\n\n"
        message_text += f"F.I.O: {clean_full_name}\n\n"
        message_text += f"Telegram: @{clean_username}\n\n"
        
        if complaint[3] == "teacher":
            message_text += f"Fan/Mutaxassislik: {clean_teacher_subject}\n\n"
            message_text += f"Kontaktlar: {clean_contact}\n\n"
        elif complaint[3] == "parent":
            message_text += f"Talaba F.I.O: {clean_parent_student_name}\n\n"
            message_text += f"Fakultet/Guruh: {clean_faculty}\n\n"
            message_text += f"Kontaktlar: {clean_contact}\n\n"
        else:  # student
            message_text += f"Fakultet/Guruh: {clean_faculty}\n\n"
            # Для студентов не показываем контакты
        
        message_text += f"Murojaat:\n{clean_content}\n\n"
        
        # Добавляем информацию об ответе если есть
        if clean_response:
            message_text += f"Javob: {clean_response}\n\n"
        
        message_text += "═══════════════════════════\n\n"
    
    # Создаем клавиатуру для навигации
    keyboard = []
    if end_index < len(complaints):
        keyboard.append([InlineKeyboardButton("➡️ Keyingi 10 ta", callback_data="dean_next_page")])
    
    if current_index > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Oldingi 10 ta", callback_data="dean_prev_page")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Отправляем без Markdown разметки
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup
    )

# Обработка навигации по страницам
async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "dean_next_page":
        context.user_data['dean_current_index'] += 10
    elif query.data == "dean_prev_page":
        context.user_data['dean_current_index'] = max(0, context.user_data['dean_current_index'] - 10)
    
    await dean_read_complaints(update, context)

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Murojaat bekor qilindi. Qayta boshlash uchun /start dan foydalaning."
    )
    return ConversationHandler.END

# Обработчик для кнопок проректора
async def dean_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "dean_read_complaints":
        await dean_read_complaints(update, context)
    elif query.data.startswith("reply_"):
        await handle_reply_button(update, context)
    elif query.data in ["dean_next_page", "dean_prev_page"]:
        await handle_page_navigation(update, context)

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Xatolik yuz berdi: {context.error}")

# Основная функция
def main():
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # ConversationHandler для обычных пользователей
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [CallbackQueryHandler(handle_category, pattern="^(student|teacher|parent)$")],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FACULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faculty)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            TEACHER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_teacher_subject)],
            PARENT_STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_parent_student_name)],
            CONTENT: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.IMAGE, handle_content)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    # ConversationHandler для ответов проректора
    dean_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_reply_button, pattern="^reply_")],
        states={
            DEAN_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dean_response)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    # Обработчики команд
    application.add_handler(conv_handler)
    application.add_handler(dean_conv_handler)
    
    # Обработчики callback кнопок для проректора
    application.add_handler(CallbackQueryHandler(dean_button_handler, pattern="^(dean_read_complaints|dean_next_page|dean_prev_page)$"))
    
    print("Bot ishga tushdi...")
    
    # Запускаем бота
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()

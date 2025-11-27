import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import sqlite3
from datetime import datetime

# Настройки
BOT_TOKEN = "8245945626:AAFoGNoWP-JZTRUt9AdoYF9T891GCDXOGlo"
DEAN_USER_ID = 6224232118  # ID проректора в Telegram

# Состояния диалога
CATEGORY, NAME, FACULTY, CONTACT, TEACHER_SUBJECT, PARENT_STUDENT_NAME, CONTENT = range(7)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS complaints
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  category TEXT,
                  full_name TEXT,
                  faculty TEXT,
                  contact TEXT,
                  teacher_subject TEXT,
                  parent_student_name TEXT,
                  message_type TEXT,
                  content TEXT,
                  file_id TEXT,
                  timestamp DATETIME)''')
    conn.commit()
    conn.close()

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
            "👨‍🎓 Siz **Talaba**ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:",
            parse_mode='Markdown'
        )
        return NAME
        
    elif category == "teacher":
        await query.edit_message_text(
            "👩‍🏫 Siz **O'qituvchi**ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:",
            parse_mode='Markdown'
        )
        return NAME
        
    elif category == "parent":
        await query.edit_message_text(
            "👨‍👩‍👧‍👦 Siz **Ota-ona**ni tanladingiz\n\n"
            "Iltimos, to'liq F.I.O ingizni kiriting:",
            parse_mode='Markdown'
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
            "✅ **Ajoyib! Ma'lumotlar saqlandi.**\n\n"
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
        f"✅ **Ajoyib! Ma'lumotlar saqlandi.**\n\n"
        f"**Kategoriya:** {category_name}\n\n"
        "Endi murojaatingizni yuboring:\n"
        "Sizning barcha materiallaringiz yo'naltiriladi."

    )
    return CONTENT

# Обработка контента
async def handle_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_id = update.effective_user.id
    timestamp = datetime.now()
    
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
                 (user_id, category, full_name, faculty, contact, teacher_subject, parent_student_name, message_type, content, file_id, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, 
               user_data['category'],
               user_data['full_name'], 
               user_data.get('faculty', ''), 
               user_data.get('contact', 'Ko\'rsatilmagan'),
               user_data.get('teacher_subject', ''),
               user_data.get('parent_student_name', ''),
               message_type, content, file_id, timestamp))
    conn.commit()
    conn.close()
    
    # Отправляем обращение проректору (ВСЕ В ОДНОМ СООБЩЕНИИ)
    await send_to_dean(update, context, user_data, message_type, content, file_id)
    
    # Возвращаем к выбору категории
    await update.message.reply_text(
        "✅ Murojaatingiz muvaffaqiyatli yuborildi!\n"
        "Universitet rivojiga qo'shgan hissangiz uchun rahmat.\n\n"
        "Yangi murojaat yuborish uchun /start dan foydalaning."
    )
    
    return ConversationHandler.END

# Отправка обращения проректору (ВСЕ В ОДНОМ СООБЩЕНИИ)
async def send_to_dean(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, message_type, content, file_id):
    try:
        category = user_data['category']
        category_name = get_category_name(category)
        
        # Формируем полное сообщение с информацией и контентом
        full_message = (
            
            f"📨 **YANGI MUROJAAT**\n\n"
            
            f"**📋 Murojatchi turi:** {category_name}\n"
            f"**👤 F.I.O:** {user_data['full_name']}\n"
        )
        
        if category == "teacher":
            full_message += f"**📚 Fan/Mutaxassislik:** {user_data.get('teacher_subject', '')}\n"
            full_message += f"**📞 Kontaktlar:** {user_data.get('contact', '')}\n"
        elif category == "parent":
            full_message += f"**👶 Talaba F.I.O:** {user_data.get('parent_student_name', '')}\n"
            full_message += f"**🎓 Fakultet/Guruh:** {user_data.get('faculty', '')}\n"
            full_message += f"**📞 Kontaktlar:** {user_data.get('contact', '')}\n\n"
        else:  # student
            full_message += f"**🎓 Fakultet/Guruh:** {user_data.get('faculty', '')}\n"
            # Для студентов не показываем контакты
        
        full_message += f"**⏰ Vaqt:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n\n"
        
        
        # Добавляем контент обращения
        if message_type == "text":
            full_message += f"**📝 MUROJAAT MATNI:**\n\n{content}"
            
            # Отправляем одно сообщение с текстом
            await context.bot.send_message(
                chat_id=DEAN_USER_ID,
                text=full_message,
                parse_mode='Markdown'
            )
            
        elif message_type == "photo":
            # Для фото - отправляем информацию и фото в одном сообщении
            await context.bot.send_photo(
                chat_id=DEAN_USER_ID,
                photo=file_id,
                caption=full_message + (f"\n\n**Tavsif:** {content}" if content else ""),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"Yuborishda xatolik: {e}")

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
    c.execute('''SELECT * FROM complaints ORDER BY timestamp DESC''')
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
    
    message_text = f"📨 **Murojaatlar {start_index + 1}-{end_index} dan {len(complaints)}:**\n\n"
    
    for i in range(start_index, end_index):
        complaint = complaints[i]
        
        # Форматируем сообщение с большими пробелами для лучшей читаемости
        message_text += "═══════════════════════════\n"
        message_text += f"**📋 KATEGORIYA:** {get_category_name(complaint[2])}\n\n"
        message_text += f"**👤 F.I.O:** {complaint[3]}\n\n"
        
        if complaint[2] == "teacher":
            message_text += f"**📚 Fan/Mutaxassislik:** {complaint[6]}\n\n"
            message_text += f"**📞 Kontaktlar:** {complaint[5]}\n\n"
        elif complaint[2] == "parent":
            message_text += f"**👶 Talaba F.I.O:** {complaint[7]}\n\n"
            message_text += f"**🎓 Fakultet/Guruh:** {complaint[4]}\n\n"
            message_text += f"**📞 Kontaktlar:** {complaint[5]}\n\n"
        else:  # student
            message_text += f"**🎓 Fakultet/Guruh:** {complaint[4]}\n\n"
            # Для студентов не показываем контакты
        
        message_text += f"**⏰ Vaqt:** {complaint[11][:16]}\n\n"
        message_text += f"**📝 Murojaat:**\n{complaint[9]}\n\n"
        message_text += "═══════════════════════════\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    
    if end_index < len(complaints):
        # Есть еще обращения для показа
        context.user_data['dean_current_index'] = end_index
    else:
        # Все обращения показаны, сбрасываем счетчик
        context.user_data['dean_current_index'] = 0
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Murojaat bekor qilindi. Qayta boshlash uchun /start dan foydalaning."
    )
    return ConversationHandler.END

# Обработчик для кнопки проректора
async def dean_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "dean_read_complaints":
        await dean_read_complaints(update, context)

# Основная функция
def main():
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
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
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Обработчики команд
    application.add_handler(conv_handler)
    
    # Обработчики callback кнопок для проректора
    application.add_handler(CallbackQueryHandler(dean_button_handler, pattern="^dean_read_complaints$"))
    
    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == '__main__':
    main()


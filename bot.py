from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
import random
import time
import re

# توکن ربات تلگرام
TOKEN = '7685970229:AAFhtHZqdQCpgkt7LDLij-vYJrMLyImGw5c'

# آیدی گروه تلگرامی
GROUP_ID = 7168209179  # آیدی عددی گروه

# دیکشنری برای ذخیره اطلاعات کاربران
user_data = {}
cooldown_users = {}

# مراحل گفتگو
SELECT_CATEGORY, GET_IMAGE, GET_LOCATION, GET_DESCRIPTION, GET_NAME, GET_CONTACT, CONFIRM_REPORT = range(7)

# معرفی ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    # جلوگیری از ارسال پیام مکرر
    if chat_id in cooldown_users and time.time() - cooldown_users[chat_id] < 300:
        await update.message.reply_text("شما به تازگی درخواست خود را ثبت کرده‌اید. لطفاً بعداً دوباره تلاش کنید.")
        return ConversationHandler.END

    user_data[chat_id] = {}

    buttons = [
        [KeyboardButton("گزارش مشکلات نظافتی شهری")],
        [KeyboardButton("گزارش مشکلات ساختمانی")],
        [KeyboardButton("سوالات متداول")],
        [KeyboardButton("پیگیری گزارشات قبلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "سلام! به سامانه هوشمند شهرداری منطقه ۲ مشهد خوش آمدید.\n"
        "من رباتی هستم که به شما کمک می‌کنم مشکلات شهری رو گزارش بدید.\n"
        "گزینه مناسب را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return SELECT_CATEGORY

# انتخاب دسته‌بندی
async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    chat_id = update.message.chat_id

    if category in ["گزارش مشکلات نظافتی شهری", "گزارش مشکلات ساختمانی"]:
        user_data[chat_id]['category'] = category
        await update.message.reply_text("لطفاً تصویر یا ویدیو گزارش را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
        return GET_IMAGE

# دریافت تصویر یا ویدیو
async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if update.message.photo:
        user_data[chat_id]['image'] = update.message.photo[-1].file_id
    elif update.message.video:
        user_data[chat_id]['video'] = update.message.video.file_id
    else:
        await update.message.reply_text("لطفاً یک تصویر یا ویدیو ارسال کنید.")
        return GET_IMAGE

    await update.message.reply_text("لطفاً موقعیت گزارش را از روی نقشه ارسال کنید یا آدرس دقیق را وارد کنید:")
    return GET_LOCATION

# دریافت موقعیت یا آدرس
async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if update.message.location:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        user_data[chat_id]['location'] = f"موقعیت جغرافیایی: ({latitude}, {longitude})"
    else:
        user_data[chat_id]['location'] = update.message.text

    await update.message.reply_text("لطفاً توضیحات گزارش را وارد کنید:")
    return GET_DESCRIPTION

# دریافت توضیحات
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data[chat_id]['description'] = update.message.text

    await update.message.reply_text("لطفاً نام و نام خانوادگی خود را وارد کنید:")
    return GET_NAME

# دریافت نام و نام خانوادگی
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data[chat_id]['name'] = update.message.text

    await update.message.reply_text("لطفاً شماره تماس خود را وارد کنید:")
    return GET_CONTACT

# بررسی شماره تماس و دریافت آن
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    contact = update.message.text

    # فرمت شماره تماس به‌طور خودکار اصلاح می‌شود
    contact = re.sub(r'\D', '', contact)  # حذف تمام کاراکترهای غیرعدد
    if len(contact) < 10 or len(contact) > 15:
        await update.message.reply_text("لطفاً یک شماره تماس معتبر وارد کنید.")
        return GET_CONTACT

    user_data[chat_id]['contact'] = contact

    buttons = [[KeyboardButton("بله")], [KeyboardButton("خیر")]]
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text("آیا درخواست دیگری دارید؟", reply_markup=reply_markup)
    return CONFIRM_REPORT

# تأیید گزارش و ارسال به گروه تلگرام
async def confirm_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    response = update.message.text

    if response == "بله":
        await start(update, context)
        return SELECT_CATEGORY

    elif response == "خیر":
        report_code = random.randint(10000, 99999)
        user_data[chat_id]['report_code'] = report_code

        report_message = (
            f"📌 **گزارش جدید ثبت شد**\n\n"
            f"✅ دسته‌بندی: {user_data[chat_id]['category']}\n"
            f"📍 موقعیت: {user_data[chat_id]['location']}\n"
            f"📝 توضیحات: {user_data[chat_id]['description']}\n"
            f"👤 نام: {user_data[chat_id]['name']}\n"
            f"📞 شماره تماس: {user_data[chat_id]['contact']}\n"
            f"🔢 **کد پیگیری:** {report_code}"
        )

        # ارسال گزارش به گروه تلگرام
        await context.bot.send_message(GROUP_ID, report_message)

        # ارسال پیام تایید به کاربر
        await update.message.reply_text(
            f"✅ گزارش شما با موفقیت ارسال شد.\n"
            f"📌 **کد پیگیری شما:** {report_code}"
        )

        cooldown_users[chat_id] = time.time()
        return ConversationHandler.END

# راه‌اندازی ربات
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_CATEGORY: [MessageHandler(filters.TEXT, select_category)],
            GET_IMAGE: [MessageHandler(filters.PHOTO | filters.VIDEO, get_image)],
            GET_LOCATION: [
                MessageHandler(filters.LOCATION, get_location),
                MessageHandler(filters.TEXT, get_location)
            ],
            GET_DESCRIPTION: [MessageHandler(filters.TEXT, get_description)],
            GET_NAME: [MessageHandler(filters.TEXT, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT, get_contact)],
            CONFIRM_REPORT: [MessageHandler(filters.TEXT, confirm_report)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)
    app.run_polling()

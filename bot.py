from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
import random
import time
import re
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# توکن ربات تلگرام
TOKEN = '7685970229:AAE8pUQxIR7_zT61UpR_SF6o7Q_SS8VwXHc'

# آیدی گروه تلگرامی
GROUP_ID = 7168209179  # آیدی عددی گروه

# دیکشنری برای ذخیره اطلاعات کاربران
user_data = {}
cooldown_users = {}

# ایمیل برای ارسال گزارشات
SENDER_EMAIL = "your_email@gmail.com"
RECEIVER_EMAIL = "shahrdarimashhad207@gmail.com"
EMAIL_PASSWORD = "your_email_password"

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

# تأیید گزارش و ارسال به ایمیل
async def confirm_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    response = update.message.text

    if response == "بله":
        if chat_id in cooldown_users and time.time() - cooldown_users[chat_id] < 300:
            await update.message.reply_text("شما به تازگی گزارش داده‌اید. لطفاً 5 دقیقه دیگر مجدد تلاش کنید.")
            return ConversationHandler.END
        else:
            await start(update, context)
            return SELECT_CATEGORY

    elif response == "خیر":
        report_code = random.randint(10000, 99999)
        user_data[chat_id]['report_code'] = report_code

        # ایجاد DataFrame برای ذخیره اطلاعات
        report_data = {
            'Category': user_data[chat_id]['category'],
            'Location': user_data[chat_id]['location'],
            'Description': user_data[chat_id]['description'],
            'Name': user_data[chat_id]['name'],
            'Contact': user_data[chat_id]['contact'],
            'Report Code': report_code
        }

        df = pd.DataFrame([report_data])

        # ذخیره فایل اکسل
        file_name = f"report_{report_code}.xlsx"
        df.to_excel(file_name, index=False)

        # ارسال فایل اکسل به ایمیل
        send_email(file_name)

        # ارسال پیام تایید به کاربر
        await update.message.reply_text(
            f"✅ گزارش شما با موفقیت ارسال شد.\n"
            f"📌 **کد پیگیری شما:** {report_code}"
        )

        cooldown_users[chat_id] = time.time()
        return ConversationHandler.END

# ارسال ایمیل با فایل اکسل
def send_email(file_name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = "گزارش جدید ثبت شده"

        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(file_name, "rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={file_name}")
        msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()

    except Exception as e:
        print(f"Error: {e}")

# راه‌اندازی ربات
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

   

import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# قراءة ملف البيانات
df = pd.read_excel(r"Stocks_read.xlsx", dtype={'الرمز': str})

# حفظ حالة المستخدمين
user_state = {}

# كيبورد رئيسي
main_keyboard = ReplyKeyboardMarkup(
    [["✅ التحقق من الشرعية", "📊 حاسبة التطهر"]],
    resize_keyboard=True
)

# كيبورد داخلي مع زر العودة
back_keyboard = ReplyKeyboardMarkup(
    [["🔙 العودة إلى القائمة الرئيسية"]],
    resize_keyboard=True
)

# رسالة البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " مرحبًا بك في بوت الأسهم الشرعية.\nاختر من الخيارات:",
        reply_markup=main_keyboard
    )

# التعامل مع الأزرار والنصوص
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    if text == "🔙 العودة إلى القائمة الرئيسية":
        user_state.pop(user_id, None)
        await update.message.reply_text(
            "⬅️ تم الرجوع إلى القائمة الرئيسية.",
            reply_markup=main_keyboard
        )
        return

    elif text == "✅ التحقق من الشرعية":
        user_state[user_id] = "awaiting_input"
        await update.message.reply_text("اكتب رمز أو اسم الشركة:", reply_markup=back_keyboard)
        return

    elif text == "📊 حاسبة التطهر":
        user_state[user_id] = "awaiting_tatheer_input"
        await update.message.reply_text(" اكتب رمز السهم وعدد الأسهم، مثال:\n\n1050 200", reply_markup=back_keyboard)
        return

    elif user_state.get(user_id) == "awaiting_input":
        keyword = text
        results = df[
            df['الرمز'].astype(str).str.contains(keyword, case=False) |
            df['اسم التداول'].astype(str).str.contains(keyword, case=False)
        ]

        if results.empty:
            await update.message.reply_text("❌ لم يتم الوصول إلى أي نتائج.")
        elif len(results) == 1:
            row = results.iloc[0]
            msg = (
                f"*الرمز:* {row['الرمز']}\n\n"
                f"*الاسم:* {row['اسم التداول']}\n"
                f"*اسم الشركة:* {row['اسم الشركة']}\n"
                f"*القطاع:* {row['القطاع']}\n\n"
                f"*شرعية الراجحي:* {row['شرعية الراجحي']}\n\n"
                f"*شرعية البلاد:* {row['شرعية البلاد']}\n\n"
                f"*شرعية المقاصد:* {row['شرعية المقاصد']}\n"
                f"*التطهير:* {row['تطهير المقاصد']}"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            keyboard = []
            for _, row in results.iterrows():
                button_text = f"{row['اسم التداول']} ({row['الرمز']})"
                callback_data = f"show_{row['الرمز']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            await update.message.reply_text("اختر السهم:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif user_state.get(user_id) == "awaiting_tatheer_input":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ تأكد من كتابة الرمز وعدد الأسهم بهذا الشكل: 1050 200")
            return

        code, shares = parts
        try:
            shares = float(shares)
        except ValueError:
            await update.message.reply_text("❌ عدد الأسهم غير صحيح.")
            return

        result = df[df['الرمز'].astype(str) == code]
        if result.empty:
            await update.message.reply_text("❌ لم يتم العثور على السهم.")
            return

        row = result.iloc[0]
        tatheer_value = str(row['تطهير المقاصد']).strip()

        if tatheer_value in ["لا يوجد", "0", "0.0", "0.00", "nan", "NaN"]:
            await update.message.reply_text("✅ هذا السهم لا يحتاج إلى تطهير.")
        else:
            try:
                rate = float(tatheer_value)
                amount = rate * shares
                await update.message.reply_text(
                    f"*الرمز:* {row['الرمز']}\n"
                    f"*الاسم:* {row['اسم التداول']}\n\n"
                    f"*نسبة التطهير:* {rate:.4f}\n"
                    f"*عدد الأسهم:* {shares:.0f}\n\n"
                    f"*المبلغ المطلوب تطهيره:* {amount:.2f} ريال", parse_mode='Markdown'
                )
            except Exception:
                await update.message.reply_text("⚠️ لم يتمكن البوت من حساب التطهير لهذا السهم.")
        return

    else:
        await update.message.reply_text(" استخدم الأزرار أو أرسل /start.", reply_markup=main_keyboard)

# عند الضغط على زر من القائمة (inline)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("show_"):
        code = data.replace("show_", "")
        result = df[df['الرمز'].astype(str) == code]
        if not result.empty:
            row = result.iloc[0]
            msg = (
                f"*الرمز:* {row['الرمز']}\n\n"
                f"*الاسم:* {row['اسم التداول']}\n"
                f"*اسم الشركة:* {row['اسم الشركة']}\n"
                f"*القطاع:* {row['القطاع']}\n\n"
                f"*شرعية الراجحي:* {row['شرعية الراجحي']}\n\n"
                f"*شرعية البلاد:* {row['شرعية البلاد']}\n\n"
                f"*شرعية المقاصد:* {row['شرعية المقاصد']}\n"
                f"*التطهير:* {row['تطهير المقاصد']}"
            )
            await query.edit_message_text(msg, parse_mode='Markdown')

# التشغيل
if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    from telegram.ext import CommandHandler

    nest_asyncio.apply()  # الحل السحري لمشكلة "Cannot close a running event loop"

    TOKEN = ("7861546442:AAEyTRxlMpiyA6D3c_-CeIUwZp9NPYDOuf0")

    async def main():
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT, message_handler))
        app.add_handler(CallbackQueryHandler(callback_handler))

        print("🤖 البوت يعمل الآن...")
        await app.run_polling()

    asyncio.get_event_loop().run_until_complete(main())


import pandas as pd
import asyncio
import nest_asyncio
import os

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import TimedOut

nest_asyncio.apply()

# تحميل بيانات الأسهم
df = pd.read_excel(r"Stocks_read.xlsx")

BOT_TOKEN = os.getenv("BOT_TOKEN") or "7861546442:AAEyTRxlMpiyA6D3c_-CeIUwZp9NPYDOuf0"

# قوائم الأزرار
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("✅ التحقق من الشرعية")],
        [KeyboardButton("📊 حاسبة التطهير")]
    ],
    resize_keyboard=True
)

back_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("🔙 العودة إلى القائمة الرئيسية")]],
    resize_keyboard=True
)

# حالات المستخدم
user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_chat.id] = "MAIN_MENU"
    await update.message.reply_text("مرحبًا!  اختر خيارًا:", reply_markup=main_menu)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # الرجوع للقائمة
    if text == "🔙 العودة إلى القائمة الرئيسية":
        user_state[chat_id] = "MAIN_MENU"
        await update.message.reply_text("رجعت للقائمة الرئيسية ✅", reply_markup=main_menu)
        return

    # التحقق من الشرعية
    if text == "✅ التحقق من الشرعية":
        user_state[chat_id] = "WAITING_FOR_SEARCH"
        await update.message.reply_text("اكتب اسم الشركة أو رمز السهم:", reply_markup=back_menu)
        return

    # حاسبة التطهير
    if text == "📊 حاسبة التطهير":
        user_state[chat_id] = "WAITING_FOR_PURGE_SYMBOL"
        await update.message.reply_text("أدخل *رمز السهم* الذي تريد حساب تطهيره:", parse_mode="Markdown", reply_markup=back_menu)
        return


    # البحث عن سهم
    if user_state.get(chat_id) == "WAITING_FOR_SEARCH":
        query = text.strip()
        results = df[df['اسم التداول'].str.contains(query, case=False, na=False) | df['الرمز'].astype(str).str.contains(query)]

        if results.empty:
            await update.message.reply_text("❌ لم يتم العثور على أي نتائج.")
        elif len(results) == 1:
            row = results.iloc[0]
            msg = (
                f" *الرمز:* {row['الرمز']}\n\n"
                f" *الاسم:* {row['اسم التداول']}\n"
                f" *اسم الشركة:* {row['اسم الشركة']}\n"
                f" *القطاع:* {row['القطاع']}\n\n"
                f" *شرعية الراجحي:* {row['شرعية الراجحي']}\n\n"
                f" *شرعية البلاد:* {row['شرعية البلاد']}\n\n"
                f" *شرعية المقاصد:* {row['شرعية المقاصد']}\n"
                f" *التطهير:* {row['تطهير المقاصد']}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            # عرض النتائج كـ inline keyboard
            buttons = []
            for _, row in results.iterrows():
                name = row["اسم التداول"]
                symbol = str(row["الرمز"])
                callback_data = f"show:{symbol}"
                buttons.append([InlineKeyboardButton(name, callback_data=callback_data)])

            keyboard = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(" تم العثور على عدة نتائج، اختر واحدة:", reply_markup=keyboard)

    elif user_state.get(chat_id) == "WAITING_FOR_PURGE_SYMBOL":
        symbol = text.strip()
        results = df[df["الرمز"].astype(str) == symbol]

        if results.empty:
            await update.message.reply_text("❌ لم يتم العثور على هذا الرمز. تأكد من كتابته بشكل صحيح.", reply_markup=back_menu)
        else:
            context.user_data["purge_symbol"] = symbol
            user_state[chat_id] = "WAITING_FOR_PURGE_AMOUNT"
            await update.message.reply_text("الآن، أدخل *عدد الأسهم* التي تملكها:", parse_mode="Markdown", reply_markup=back_menu)

    elif user_state.get(chat_id) == "WAITING_FOR_PURGE_AMOUNT":
        try:
            quantity = float(text.strip())
            symbol = context.user_data.get("purge_symbol")
            results = df[df["الرمز"].astype(str) == symbol]

            if results.empty:
                await update.message.reply_text("❌ حدث خطأ غير متوقع، لم يتم العثور على السهم.", reply_markup=main_menu)
                return

            row = results.iloc[0]
            try:
                rate = float(row["تطهير المقاصد"])
            except (ValueError, TypeError):
                await update.message.reply_text(
                    "❌ لا توجد نسبة تطهير لهذا السهم في البيانات المتوفرة.",
                    reply_markup=main_menu
                )
                user_state[chat_id] = "MAIN_MENU"
                return

            purification = quantity * rate


            msg = (
                f"*رمز السهم:* {symbol}\n"
                f" *الاسم:* {row['اسم التداول']}\n\n"
                f"*عدد الأسهم:* {quantity}\n\n"
                f"*نسبة التطهير:* {rate} ريال للسهم\n\n"
                f"*المبلغ الواجب تطهيره:* {purification:.2f} ريال"
            )
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu)
            user_state[chat_id] = "MAIN_MENU"

        except ValueError:
            await update.message.reply_text("❌ أدخل رقمًا صحيحًا لعدد الأسهم.", reply_markup=back_menu)

    else:
        await update.message.reply_text("يرجى اختيار خيار من القائمة أولًا.", reply_markup=main_menu)

# التعامل مع ضغط زر inline
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("show:"):
        symbol = query.data.split(":")[1]
        results = df[df['الرمز'].astype(str) == symbol]
        if not results.empty:
            row = results.iloc[0]
            msg = (
                f" *الرمز:* {row['الرمز']}\n\n"
                f" *الاسم:* {row['اسم التداول']}\n"
                f" *اسم الشركة:* {row['اسم الشركة']}\n"
                f" *القطاع:* {row['القطاع']}\n\n"
                f" *شرعية الراجحي:* {row['شرعية الراجحي']}\n\n"
                f" *شرعية البلاد:* {row['شرعية البلاد']}\n\n"
                f" *شرعية المقاصد:* {row['شرعية المقاصد']}\n"
                f" *التطهير:* {row['تطهير المقاصد']}"
            )
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=back_menu)

# تشغيل التطبيق مع الحماية من الأعطال
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    while True:
        try:
            print("✅ البوت يعمل...")
            await app.run_polling()
        except TimedOut:
            print("⏱ تم انتهاء المهلة، إعادة المحاولة بعد 5 ثوانٍ...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ حدث خطأ: {e}, إعادة المحاولة بعد 5 ثوانٍ...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())

import datetime
import logging
import random
import asyncio
 
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
 
import sheets
import schedule
 
 
API_TOKEN = 'PRODUCTION-SECRET'
G_TOKEN = 'PRODUCTION-SECRET'
CHECK_TIMEOUT = 60                  # In seconds
 
logging.basicConfig(level=logging.INFO)
 
# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
response_wait = dict()
 
cb = CallbackData("call", "action", "cid")
 
ch_id = -0000000000 # production-secret
 
order_message = """
⏰ %s %s - %s
🗿 %s
📞 Контактный номер: %s
⚡️ %s %s
💰 Оплата: %s руб (на карту по номеру +79103938818, либо наличными)
    %s
🎭 Ведущий: %s
"""
 
def get_correct_form(amount):
    if (not str(amount).isdecimal()) or int(amount) == 1 or int(amount) >= 5:
        return "человек"
    else:
        return "человека"
 
def get_text_params(date, time_beg, time_end, name, phone, amount, money, comment, assist, **kwargs):
    date = date[:-5]
    time_beg = time_beg[:-3]
    time_end = time_end[:-3]
    if comment != '':
        comment = "\n🤙Еще: " + comment + "\n"
    if assist == '':
        assist = '❌'
    else:
        assist += " ✅"
 
    return order_message % (date, time_beg, time_end, name, phone, amount,
                                get_correct_form(amount), money, comment, assist)
 
def get_keyboard(chat):
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Я беру ✅", callback_data=cb.new(action="accept", cid=chat))
        #types.InlineKeyboardButton("Точно не я ❌", callback_data=cb.new(action="accept", cid=chat))
    )
 
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    global ch_id
    ch_id = message.chat.id
    print(ch_id)
    print(message.chat.shifted_id)
    await message.reply("Работаю..")
 
async def write_announce(params):
    if ch_id == 0:
        return
    if params["assist"] == '':
        return await bot.send_message(ch_id, get_text_params(**params), reply_markup=get_keyboard(ch_id))
    else:
        return await bot.send_message(ch_id, get_text_params(**params))
 
def gen_schedule_desc(phone, assist, t_id):
    return "%s\n%s\n%s" % (phone, assist, t_id)
 
def write_to_schedule(date, start, en, title, desc):
    t_beg = schedule.get_datetime(date, start)
    t_en = schedule.get_datetime(date, en)
    return schedule.calendar_api.create_event(schedule.CALENDAR_ID,
                                              t_beg, t_en,
                                              summary=title,
                                              desc=desc)
 
def get_row_to_dict(params):
     return {
        "date": params[2],
        "time_beg": params[3],
        "time_end": params[4],
        "name": params[1],
        "phone": params[7],
        "amount": params[5],
        "money": params[6],
        "comment": params[10],
        "assist": params[11],
        "cal_id": params[13],
        "tg_m_id": params[14]
    }
 
def get_param_col(name):
    params = [i for i in range(1, 20)]
    return get_row_to_dict(params)[name]
 
async def process_new_call(cell, params):
    text_par = get_row_to_dict(params)
 
    tg_mes = await write_announce(text_par)
    mes_id = str(tg_mes.message_id)
    cal_id = write_to_schedule(text_par["date"], text_par["time_beg"], text_par["time_end"], text_par["name"],
                               gen_schedule_desc(text_par["phone"], '', mes_id))
    sheets.run_update_vals(cell,
                           {"O": mes_id, "N": cal_id})
 
def find_row_by_post(tg_m_id):
    try:
        return sheets.run_find_column(ord('O') - ord('A') + 1, str(tg_m_id))
    except ValueError:
        print("no message yet :(")
        return None
 
def register_assistant(tg_m_id, name):
    cell = find_row_by_post(tg_m_id)
    if cell is None:
        return
 
    sheets.run_update_vals(cell, {"L": name})
    info = get_row_to_dict(sheets.run_get_row_to_arr(cell))
    n_id = schedule.calendar_api.update_event(schedule.CALENDAR_ID, info["cal_id"],
                                       desc=gen_schedule_desc(info["phone"], info["assist"], info["tg_m_id"]))
    sheets.run_update_vals(cell, {"N":n_id})
 
async def update_vals_all(head, vals: dict):
    sheets.run_update_vals(head, vals)
    info = get_row_to_dict(sheets.run_get_row_to_arr(head))
    n_id = \
        schedule.calendar_api.update_event(schedule.CALENDAR_ID, info["cal_id"],
                                              desc=gen_schedule_desc(info["phone"], info["assist"], info["tg_m_id"]),
                                              summary=info["name"],
                                              start=schedule.get_datetime(info["date"], info["time_beg"]),
                                              end=schedule.get_datetime(info["date"], info["time_end"])
                                              )
    sheets.run_update_vals(head, {get_param_col("cal_id") : n_id})
    await refresh_post(info["tg_m_id"])
 
 
async def refresh_post(m_id):
    global ch_id
    head = find_row_by_post(m_id)
    info = get_row_to_dict(sheets.run_get_row_to_arr(head))
 
    kwargs = dict()
    if info["assist"] == '':
        kwargs["reply_markup"] = get_keyboard(ch_id)
    await bot.edit_message_text(get_text_params(**info), ch_id,
                                m_id, **kwargs)
 
@dp.message_handler(content_types=types.ContentType.TEXT)
async def echo_handle(message: types.Message):
    m_id = message.from_user.id
    print("echo")
    print(message.chat.id)
    if m_id in response_wait:
        await response_wait[m_id](message)
        response_wait.pop(m_id)
    else:
        pass
 
@dp.callback_query_handler(cb.filter(action="accept"))
async def callbacks_num(callback_query: types.CallbackQuery, callback_data: dict):
    await bot.answer_callback_query(callback_query.id)
    register_assistant(callback_query.message.message_id, callback_query.from_user.first_name)
    await refresh_post(callback_query.message.message_id)
 
async def periodic():
    while True:
        await asyncio.sleep(CHECK_TIMEOUT)
        logging.info("check")
        await sheets.run_check_calls(process_new_call)
 
async def on_startup(_):
    asyncio.create_task(periodic())
 
def bot_start():
    sheets.setup()
    schedule.setup()
    executor.start_polling(dp, skip_updates=True,on_startup=on_startup)
 
 
if __name__ == '__main__':
    print("running bot")
    random.seed(datetime.datetime.utcnow().microsecond)
    bot_start()

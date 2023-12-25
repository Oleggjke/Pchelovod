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
CHECK_TIMEOUT = 60
 
logging.basicConfig(level=logging.INFO)
 
# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
response_wait = dict()
 
cb = CallbackData("call", "action", "cid")
cb_e = CallbackData("edit", "m_id", "row")
cb_ed = CallbackData("edit_dt", "m_id", "row", "dt")
 
# id    -1001974579196
# sh_id  1974579196
#ch_id = -1001742818412
ch_id = -1001974579196 # official
 
order_message = """
⏰ %s %s - %s
🗿 %s
📞 Контактный номер: %s
⚡️ %s %s
💰 Оплата: %s руб (на карту по номеру +79103938818, либо наличными)
    %s
🎭 Ведущий: %s
"""
 
upcoming_message = """
🐝 Скоро пройдут:
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
    )
 
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    global ch_id
    ch_id = message.chat.id
    print(ch_id)
    print(message.chat.shifted_id)
 
    await message.reply("Работаю..")
 
 
@dp.message_handler(commands=['decide'])
async def decide_assistant(message: types.Message):
    #await bot.send_message(ch_id, '🎲')
    ms = await bot.send_dice(ch_id, emoji='🎲')
    res = ms.dice.value
    names = ["Санек", "Федос"]
    name = names[res % len(names)]
    await message.answer("Ой-ой, кажется этот заказ берет %s" % name)
 
 
@dp.message_handler(commands=['games'])
async def send_upcoming(message: types.Message):
    global ch_id
    now = datetime.datetime.utcnow().isoformat()
    events = schedule.calendar_api.get_events(schedule.CALENDAR_ID, now)
    show = events[:min(5, len(events))]
 
    keyboard = types.InlineKeyboardMarkup(row_width=1)
 
    for ev in show:
        when_d, when_t = schedule.parse_datetime_str(ev['start']['dateTime'])
        summary = ev.get('summary', '')
        desc = ev.get('description', '').split('\n')
 
        if len(desc) > 0:
            m_id = desc[-1]
            ins = '📍 %s %s %s\n\n' % (when_d[:-5], summary, when_t[:-3])
            link = 't.me/c/%s/%s' % (message.chat.shifted_id, m_id)
            keyboard.insert(
                types.InlineKeyboardButton(text=ins, url=link)
            )
 
    await message.answer(upcoming_message, reply_markup=keyboard)
 
 
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
 

def get_edit_main_keyboard(m_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Имя", callback_data=cb_e.new(m_id=m_id, row="name")),
        types.InlineKeyboardButton("Дата", callback_data=cb_e.new(m_id=m_id, row="date_menu")),
        types.InlineKeyboardButton("Время", callback_data=cb_e.new(m_id=m_id, row="time_menu"))
    )
    keyboard.row(
        types.InlineKeyboardButton("Цена", callback_data=cb_e.new(m_id=m_id, row="money")),
        types.InlineKeyboardButton("Ведущий", callback_data=cb_e.new(m_id=m_id, row="assist_reset"))
    )
    keyboard.row(
        types.InlineKeyboardButton("Число", callback_data=cb_e.new(m_id=m_id, row="amount")),
        types.InlineKeyboardButton("Закрыть", callback_data=cb_e.new(m_id=m_id, row="pass"))
    )
    return keyboard
 
def get_edit_date_keyboard(m_id, now):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("◀️", callback_data=cb_ed.new(m_id=m_id, row="dt_prev", dt=now)),
        types.InlineKeyboardButton("📅 %s" % now[:-5], callback_data=cb_ed.new(m_id=m_id, row="dt_chose", dt=now)),
        types.InlineKeyboardButton("▶️", callback_data=cb_ed.new(m_id=m_id, row="dt_next", dt=now))
    )
    keyboard.row(
        types.InlineKeyboardButton("Написать", callback_data=cb_e.new(m_id=m_id, row="date")),
        types.InlineKeyboardButton("Назад", callback_data=cb_e.new(m_id=m_id, row="back"))
    )
    return keyboard
 
def get_edit_time_keyboard(m_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Начало️", callback_data=cb_e.new(m_id=m_id, row="time_beg")),
        types.InlineKeyboardButton("Конец", callback_data=cb_e.new(m_id=m_id, row="time_end")),
    )
    keyboard.row(
        types.InlineKeyboardButton("Назад", callback_data=cb_e.new(m_id=m_id, row="back")),
    )
    return keyboard
 
 
async def edit_post_interface(m_id):
    global ch_id
    head = find_row_by_post(m_id)
    if head is None:
        await bot.send_message(ch_id, "Это не то..")
        return
    keyboard = get_edit_main_keyboard(m_id)
    await bot.send_message(ch_id, "Окей, что меняем?", reply_to_message_id=m_id, reply_markup=keyboard)
 
 
async def find_edit_post_from_message(message: types.Message):
    m_id = 0
    if message.reply_to_message is not None:
        m_id = message.reply_to_message.message_id
    elif message.forward_from_message_id is not None:
        m_id = message.forward_from_message_id
    else:
        await message.answer("А где...")
        return
 
    await edit_post_interface(m_id)
 
 
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
 
 
@dp.message_handler(commands=['stop'])
async def ask_edit_post(message: types.Message):
    response_wait.pop(message.from_user.id, None)
    await message.reply("Окей")
 
@dp.message_handler(commands=['edit'])
async def ask_edit_post(message: types.Message):
    if message.reply_to_message is not None:
        await edit_post_interface(message.reply_to_message.message_id)
    else:
        response_wait[message.from_user.id] = find_edit_post_from_message
        await message.answer("Скинь пост:")
 
 
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
 
 
def construct_edit_table(head, col, u_id):
    async def edit_table(message: types.Message):
        global ch_id
        await bot.send_message(ch_id, "Принято ✅", reply_to_message_id=message.message_id)
        await update_vals_all(head, {col: message.text})
    response_wait[u_id] = edit_table
 
 
@dp.callback_query_handler(cb_e.filter())
async def callback_edit_post(callback_query: types.CallbackQuery, callback_data: dict):
    global ch_id
    await bot.answer_callback_query(callback_query.id)
    cur_id = callback_query.message.message_id
    m_id = callback_data["m_id"]
    row = callback_data["row"]
    head = find_row_by_post(m_id)
 
    if row == "pass":
        response_wait.pop(callback_query.from_user.id, None)
        await bot.edit_message_text(callback_query.message.text, ch_id, cur_id)
    elif row == "back":
        await bot.edit_message_text(callback_query.message.text, ch_id, cur_id,
                                    reply_markup=get_edit_main_keyboard(m_id))
    elif row == "date_menu":
        info = get_row_to_dict(sheets.run_get_row_to_arr(head))
        await bot.edit_message_text(callback_query.message.text, ch_id, cur_id,
                                   reply_markup=get_edit_date_keyboard(m_id, info["date"]))
    elif row == "time_menu":
        await bot.edit_message_text(callback_query.message.text, ch_id, cur_id,
                                    reply_markup=get_edit_time_keyboard(m_id))
    elif row == "assist_reset":
        await bot.send_message(ch_id, "Принято ✅")
        await update_vals_all(head, {get_param_col("assist") : ''})
    else:
        col = get_param_col(row)
        construct_edit_table(head, col, callback_query.from_user.id)
        if row == "date":
            await bot.send_message(ch_id, "Важно!\nФормат такой: 01.12.2000")
        if row == "time_beg" or row == "time_end":
            await bot.send_message(ch_id, "Важно!\nФормат такой: 20:00:00")
        await bot.send_message(ch_id, "Новое значение:")
 
@dp.callback_query_handler(cb_ed.filter())
async def callback_edit_date_post(callback_query: types.CallbackQuery, callback_data: dict):
    global ch_id
    await bot.answer_callback_query(callback_query.id)
    m_id = callback_data["m_id"]
    cur_id = callback_query.message.message_id
    row = callback_data["row"]
    dt = callback_data["dt"]
 
    if row == "dt_chose":
        head = find_row_by_post(m_id)
        await bot.send_message(ch_id, "Принято ✅")
        await update_vals_all(head, {get_param_col("date") : dt})
        return
 
    day = datetime.timedelta(days=1)
    cur = datetime.datetime.strptime(dt, "%d.%m.%Y")
 
    if row == "dt_prev":
        cur -= day
    elif row == "dt_next":
        cur += day
    str_cur = cur.strftime("%d.%m.%Y")
 
    await bot.edit_message_text(callback_query.message.text, ch_id, cur_id,
                                reply_markup=get_edit_date_keyboard(m_id, now=str_cur))
 
async def periodic():
    while True:
        await asyncio.sleep(CHECK_TIMEOUT)
        logging.info("per")
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

import pygsheets
 
sh = None
 
def get_last_cell(wks: pygsheets.Worksheet):
    total = int(wks.get_value("S2"))
    return wks.cell("A" + str(total + 1))
 
 
def write_call(wks: pygsheets.Worksheet, params):
    cell = get_last_cell(wks)
    #inc_total(wks)
    cell.set_value(int(cell.neighbour('top').value) + 1)
    cell = cell.neighbour('right')
    prep = [[x for x in params]]
    prep[0].append("0")
    wks.update_values(cell.label, prep)
 
 
def sw_col(wks: pygsheets.Worksheet, cell, col):
    return wks.cell((cell.row, ord(col) - ord('A') + 1))
 
 
def process_date(s):
    return s[:-5]
 
 
def update_values(wks: pygsheets.Worksheet, head: pygsheets.Cell, vals: dict):
    for key, val in vals.items():
        nc = head
        if isinstance(key, str):
            nc = sw_col(wks, head, key)
        elif isinstance(key, int):
            nc = sw_col(wks, head, chr(ord('A') + key - 1))
        nc.set_value(val)
 
def run_update_vals(head: pygsheets.Cell, vals: dict):
    global sh
    wks = wks = sh.worksheet_by_title("Форма")
    update_values(wks, head, vals)
 
def get_row_to_arr(wks: pygsheets.Worksheet, head: pygsheets.Cell):
    nc_beg = sw_col(wks, head, 'A')
    nc_en = sw_col(wks, head, 'O')
 
    return wks.get_values(nc_beg.label, nc_en.label)[0]
 
def run_get_row_to_arr(head: pygsheets.Cell):
    global sh
    wks = sh.worksheet_by_title("Форма")
    return get_row_to_arr(wks, head)
 
async def check_calls(wks: pygsheets.Worksheet, callback):
    cell = sw_col(wks, get_last_cell(wks), 'I')
    while cell.row > 1 and cell.value != '1':
        arr = get_row_to_arr(wks, cell)
        await callback(cell, arr)
 
        cell.set_value('1')
        cell = cell.neighbour('top')
 
async def run_check_calls(callback):
    global sh
    # Update a cell with value (just to let him know values is updated ;) )
 
    wks = sh.worksheet_by_title("Форма")
    await check_calls(wks, callback)
 
def find_column(wks: pygsheets.Worksheet, col: chr, x):
    row = wks.get_col(col, include_tailing_empty=False).index(x) + 1
    return wks.cell((row, col))
 
def run_find_column(col: chr, x):
    global sh
    wks = sh.worksheet_by_title("Форма")
    return find_column(wks, col, x)
 
def run_get_cell(row, col):
    global sh
    wks = sh.worksheet_by_title("Форма")
    return wks.cell((row, col))
 
def setup():
    global sh
 
    gc = pygsheets.authorize()
    sh = gc.open_by_key('PRODUCTION-SECRET')
 
 
if __name__ == '__main__':
    print("running sheets")
    #run_check()

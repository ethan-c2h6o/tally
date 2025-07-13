from flask import Flask, request, session, redirect
import pyhtml as p
import json
import bcrypt
import os
from datetime import datetime as dt

WEBSITE_NAME = 'Tally'
DATA_FILE = 'data.json'

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        data = {
            "Ethan Ryoo": {
                "password": None,
                "dark_mode": False,
                "transactions": []
            }
        }
        json.dump(data, f)

def load_file(filename: str):
    with open(filename) as f:
        return json.load(f)

def write_file(filename: str, data) -> None:
    with open(filename, 'w') as f:
        json.dump(data, f)

def load_icon(icon_name: str) -> str:
    with open(f'static/icons/{icon_name}.svg') as f:
        return p.DangerousRawHtml(f.read())

def nav_bar_maker(page_name: str = None) -> list:
    PAGE_LIST = [
        'Home',
        'History',
        'Settings',
        'Log out'
    ]
    nav_items = []
    for page in PAGE_LIST:
        page_file_name = page.replace(' ', '_').lower()
        link_id = None
        if page == page_name:
            link_id='active_page'
        elif page == 'Log out':
            link_id='log_out_btn'
        nav_items.append(p.li(id=link_id)(
            p.a(href=f'/{page_file_name}')(
                load_icon(page_file_name),
                page
            )
        ))
    return [p.nav(
        p.a(href='/home')(p.img(src="/static/icons/tally.svg", id="tally_logo", alt="Tally")),
        p.input(type='checkbox', _class='nav_toggle', id='nav_toggle'),
        p.label(_for='nav_toggle', _class='burger')(
            [p.div() for _ in range(3)]
        ),
        p.ul(nav_items),
        p.label(_for='nav_toggle', _class='shader')()
    )]

def head_maker(page_name: str, special_css: bool = False) -> list:
    head = [
        p.meta(charset='UTF-8'),
        p.meta(name='viewport', content='width=device-width, initial-scale=1.0'),
        p.meta(name='description', content='A lightweight debt tracker for friends.'),
        p.meta(name='author', content='Ethan Ryoo'),
        p.title(f'{WEBSITE_NAME} | {page_name}'),
        p.link(rel='icon', href='/static/icons/tally.svg', type='image/svg+xml'),
        p.link(rel='stylesheet', href='/static/styles/main.css')
    ]
    if page_name == 'Edit':
        head.append(p.link(rel='stylesheet', href='/static/styles/history.css'))
    if special_css:
        head.append(p.link(rel='stylesheet', href=f'/static/styles/{page_name.lower()}.css'))
    head.append(p.script(src='/static/main.js'))
    return head

def select_options_maker(selected_name: str = None) -> list:
    data = load_file(DATA_FILE)
    return [
        p.option(value="", disabled=True, selected=not(selected_name))(
            '-- Select a name --'),
        [p.option(value=name, selected=(selected_name==name))(name) for name in data]
    ]

def change_pw_form_maker(old_pw_exists: bool, old_pw_fill: str = '') -> list:
    FIELDS = [
        'old_password',
        'new_password',
        'confirm_new_password'
    ]
    password_form = []
    for field in FIELDS:
        if field == 'old_password':
            if old_pw_exists:
                password_form.extend([
                    p.label(for_=field)(f'{field.replace('_', ' ').capitalize()}:'),
                    p.input(
                        type='password', id=field, name=field,
                        required=True, value=old_pw_fill
                    )
                ])
            else:
                password_form.extend([
                    p.p(_class='label')(f'{field.replace('_', ' ').capitalize()}:'),
                    p.div(id='old_password_div')
                ])
        else:
            password_form.extend([
                p.label(for_=field, _class='mobile_gap')(
                    f'{field.replace('_', ' ').capitalize()}:'),
                p.input(type='password', id=field, name=field, required=True)
            ])
    return password_form

def remove_pw_form_maker(old_pw_exists: bool) -> list:
    if old_pw_exists:
        name = 'remove_pw'
        return [
            p.h2('Remove your password'),
            p.div(_class='grid_container')(
                p.label(for_=name)('Password:'),
                p.input(type='password', id=name, name=name, required=True)
            ),
            p.input(type='submit', name='remove_pw_submit', value='Remove')
        ]
    return []

def insert_transaction(transactions: list[dict], new_txn: dict) -> None:
    new_txn_date = dt.strptime(new_txn['date'], '%Y-%m-%d')
    for i, txn in enumerate(transactions):
        if new_txn_date >= dt.strptime(txn['date'], '%Y-%m-%d'):
            transactions.insert(i, new_txn)
            return
    transactions.append(new_txn)

def txn_rows_maker(txns: list, interactive: bool = False, user: str = None) -> list:
    totals = []
    total = 0
    if interactive:
        rows = [p.p('Select a transaction below to edit.')]
    else:
        rows = []
    rows.extend([
        p.input(type='text', id='search_input', placeholder='Filter by description...'),
        p.button(type='button', id='clear_button')('Clear'),
        p.div(_class='grid_container header', id='txn_header')(
            p.p('Date'),
            p.p('Amount'),
            p.p('Description'),
            p.p('Total owing')
        ),
        p.p(id='no_match_msg', _class='hidden')('No matching transactions found.')
    ])
    for entry in reversed(txns):
        if entry['type'] == 'debt':
            total += float(entry['amount'])
        else:
            total -= float(entry['amount'])
        totals.append(round(total, 2))
    
    for i, entry in enumerate(txns):
        date_str = dt.strptime(entry['date'], '%Y-%m-%d').strftime('%a %d/%m/%y')
        amount_prefix = '–' if entry['type'] == 'repayment' else ''
        amount_str = f'{amount_prefix}${float(entry['amount']):.2f}'
        balance = totals[len(totals)-i-1]
        balance_str = f'{'–' if balance < 0 else ''}${abs(balance):.2f}'
        desc = entry['desc']
        css_class = f'grid_container {entry['type']}'
        content = [
            p.p(_class='date')(date_str),
            p.p(_class='amount')(amount_str),
            p.p(_class='desc')(desc),
            p.p(_class='total')(
                p.span(_class='total_owing_desc')('Total owing: '),
                balance_str
            )
        ]
        if interactive:
            rows.append(p.button(
                _class=css_class, formaction=f'/edit/{user}/transaction_{i}',
                **{'data-desc': desc.lower()})(content))
        else:
            rows.append(p.div(_class=css_class, **{'data-desc': desc.lower()})(content))
    return rows

def compute_total_owing() -> float:
    data = load_file(DATA_FILE)
    total = 0
    for entry in data[session['name']]['transactions']:
        if entry['type'] == 'debt':
            total += float(entry['amount'])
        else:
            total -= float(entry['amount'])
    return round(total, 2)

def txn_form_contents_maker(user: str = None, txn_index: int = None) -> list:
    txn_form_contents = []
    if user:
        txn = load_file(DATA_FILE)[user]['transactions'][int(txn_index)]
    else:
        txn_form_contents.extend([
            p.label(for_='user')('User:'),
            p.select(id='user', name='user', required=True)(select_options_maker()),
        ])
    txn_form_contents.extend([
        p.label(for_='type', _class='mobile_gap')('Transaction type:'),
        p.select(id='type', name='type')(
            p.option(
                value='debt',
                selected=(user and txn['type']=='debt')
            )('Debt'),
            p.option(
                value='repayment',
                selected=(user and txn['type']=='repayment')
            )('Repayment')
        ),
        p.label(for_='amount', _class='mobile_gap')('Amount ($):'),
        p.input(
            type='number', min=0, step=0.01, id='amount',
            name='amount', required=True, value=txn['amount'] if user else '' 
        ),
        p.label(for_='date', _class='mobile_gap')('Date:'),
        p.input(
            type='date', id='date', name='date', max=dt.now().strftime('%Y-%m-%d'),
            required=True, value=txn['date'] if user else '' 
        ),
        p.label(for_='desc', _class='mobile_gap')('Description:'),
        p.textarea(id='desc', name='desc', rows=3)(txn['desc'] if user else '')
    ])
    return txn_form_contents

@app.route('/', methods=['GET', 'POST'])
def redirect_page():
    # Signed-in users accidentally returning to this page
    if 'name' in session:
        if session['name'] == 'Ethan Ryoo':
            return redirect('/master')
        return redirect('/home')
    
    # Signed-out users (GET)
    if not request.form:
        return redirect('/login')
    
    # Validating login credentials
    data = load_file(DATA_FILE)
    stored_pw = data[request.form['name']]['password']
    if (
        stored_pw is None
        or bcrypt.checkpw(request.form['password'].encode(), stored_pw.encode())
    ):
        session['name'] = request.form['name']
    else:
        session['wrong_password'] = request.form['name']

    # Redirecting login attempts
    if 'name' in session:
        if session['name'] == 'Ethan Ryoo':
            return redirect('/master')
        return redirect('/home')
    return redirect('/login')

@app.route('/login')
def login():
    PAGE_NAME = 'Login'
    head = head_maker(page_name=PAGE_NAME, special_css=True)
    message = p.p(class_='tooltip')('Leave blank if you haven\'t set a password')
    
    if session.get('wrong_password'):
        message = p.p(class_='error tooltip')('Incorrect password')
        select_options = select_options_maker(session['wrong_password'])
    else:
        select_options = select_options_maker()
    
    response = p.html(
        p.head(head),
        p.body(
            p.form(action='/')(
                p.h1('Sign in'),
                p.div(_class='grid_container')(
                    p.label(for_='name')('Name:'),
                    p.select(id='name', name='name', required=True)(select_options),
                    p.label(for_='password', _class='mobile_gap')('Password:'),
                    p.input(type='password', id='password', name='password')
                ),
                message,
                p.input(type='submit', value='Sign in')
            )
        )
    )
    return str(response)

@app.route('/home')
def home():
    if 'name' not in session:
        return redirect('/login')
    
    PAGE_NAME = 'Home'
    total = compute_total_owing()
    description = 'owing'
    
    if total < 0:
        total = abs(total)
        description = 'in credit'
    
    head = head_maker(page_name=PAGE_NAME)
    nav_bar = nav_bar_maker(PAGE_NAME)
    data = load_file(DATA_FILE)
    response = p.html(
        p.head(head),
        p.body(class_='dark' if data[session['name']]['dark_mode'] else '')(
            nav_bar,
            p.div(id='main')(
                p.h1(f'Welcome, {session['name'].split()[0]}!'),
                p.p('Your current balance is:'),
                p.h2(f'${total:.2f} {description}')
            )
        )
    )
    return str(response)

@app.route('/history')
def history():
    if 'name' not in session:
        return redirect('/login')
    
    PAGE_NAME = 'History'
    data = load_file(DATA_FILE)
    
    if data[session['name']]['transactions']:
        history_list = txn_rows_maker(
            data[session['name']]['transactions'], interactive=False
        )
    else:
        history_list = p.p('You have no transaction history.')
    head = head_maker(page_name=PAGE_NAME, special_css=True)
    nav_bar = nav_bar_maker(PAGE_NAME)
    
    response = p.html(
        p.head(head),
        p.body(class_='dark' if data[session['name']]['dark_mode'] else '')(
            nav_bar,
            p.div(id='main')(
                p.h2('Transaction history'),
                history_list
            )
        )
    )
    return str(response)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'name' not in session:
        return redirect('/login')

    PAGE_NAME = 'Settings'
    head = head_maker(PAGE_NAME, special_css=True)
    nav_bar = nav_bar_maker(PAGE_NAME)
    data = load_file(DATA_FILE)
    old_password = ''
    incorrect_pw = ''
    pw_mismatch = ''
    pw_change_success = ''
    incorrect_remove_pw = ''
    pw_remove_success = ''
    stored_pw = data[session['name']]['password']
    dark_mode = data[session['name']]['dark_mode']

    if 'password_reset' in request.form:
        if stored_pw and not bcrypt.checkpw(
            request.form['old_password'].encode(), stored_pw.encode()):
            incorrect_pw = p.p(_class='error tooltip', id='incorrect_pw')(
                'Incorrect password')
        elif request.form['new_password'] != request.form['confirm_new_password']:
            pw_mismatch = p.p(_class='error tooltip', id='pw_mismatch')(
                'New passwords do not match')
            old_password = request.form.get('old_password')
        else:
            pw_change_success = p.p(
                _class='success tooltip', id='pw_change_success'
                )('Your password has been changed')
            hashed_new_pw = bcrypt.hashpw(
                request.form['new_password'].encode(), bcrypt.gensalt()).decode()
            data[session['name']]['password'] = hashed_new_pw
            write_file(DATA_FILE, data)
    
    elif 'remove_pw_submit' in request.form:
        if bcrypt.checkpw(request.form['remove_pw'].encode(), stored_pw.encode()):
            pw_remove_success = p.p(
                _class='success tooltip', id='pw_remove_success'
                )('Your password has been removed')
            data[session['name']]['password'] = None
            write_file(DATA_FILE, data)
        else:
            incorrect_remove_pw = p.p(
                _class='error tooltip', id='incorrect_remove_pw'
                )('Incorrect password')
    
    old_pw_exists=bool(data[session['name']]['password'])
    change_pw_form = change_pw_form_maker(old_pw_exists, old_password)
    remove_pw_form = remove_pw_form_maker(old_pw_exists)
    
    response = p.html(
        p.head(head),
        p.body(class_='dark' if dark_mode else '')(
            nav_bar,
            p.div(id='main')(
                p.form(action='/settings')(
                    p.h2('Change your password'),
                    p.div(_class='grid_container')(
                        change_pw_form,
                        incorrect_pw, pw_mismatch, pw_change_success
                    ),
                    p.input(type='submit', name='password_reset')
                ),
                p.form(action='/settings')(
                    remove_pw_form,
                    pw_remove_success, incorrect_remove_pw,
                ),
                p.h2('Toggle dark mode'),
                p.label(class_='toggle')(
                    p.input(
                        type='checkbox', name='dark_mode_toggle',
                        id='dark_mode_toggle', checked=dark_mode
                    ),
                    p.span(class_='slider')
                )
            )
        )
    )
    return str(response)

@app.route('/master', methods=['GET', 'POST'])
def master():
    if 'name' not in session:
        return redirect('/login')
    elif session['name'] != 'Ethan Ryoo':
        return redirect('/')
    
    PAGE_NAME = 'Master'
    user_alr_exists = ''
    nav_bar = nav_bar_maker()
    head = head_maker(PAGE_NAME, special_css=True)
    txn_form = txn_form_contents_maker()
    data  = load_file(DATA_FILE)

    if 'transaction_submit' in request.form:
        new_txn = {
            field: request.form[field]
            for field in ['type', 'date', 'amount']
        }
        if request.form['desc']:
            new_txn['desc'] = request.form['desc']
        else:
            new_txn['desc'] = request.form['type'].capitalize()
        insert_transaction(data[request.form['user']]['transactions'], new_txn)
        write_file(DATA_FILE, data)
    
    elif 'edit_user_submit' in request.form:
        return redirect(f'/edit/{request.form['edit_user']}')
    
    elif 'new_user_submit' in request.form:
        name = (
            request.form['first_name'].strip().lower().title()
            + ' '
            + request.form['last_name'].strip().lower().title()
        )
        if name in data:
            user_alr_exists = p.p(
                class_='error tooltip', id='user_alr_exists'
                )('The user', p.em(name), 'already exists')
        else:
            if request.form['password']:
                password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()
            else:
                password = None
            data[name] = {
                'password': password,
                'dark_mode': False,
                'transactions': []
            }
            write_file(DATA_FILE, data)
    
    elif 'data_file_submit' in request.form:
        file = request.files.get('data_file')
        if not file.filename.endswith('.json'):
            return 'Invalid file type', 400
        try:
            write_file(DATA_FILE, json.load(file))
        except Exception as e:
            return f'Upload failed: {e}', 400
    
    response = p.html(
        p.head(head),
        p.body(class_='dark' if data[session['name']]['dark_mode'] else '')(
            nav_bar,
            p.div(id='main')(
                p.form(action='/master')(
                    p.h2('Add a transaction'),
                    p.div(id='transaction', _class='grid_container')(txn_form),
                    p.input(type='submit', id='transaction_submit', name='transaction_submit', value='Add')
                ),
                p.form(action='/master')(
                    p.h2('Edit a transaction'),
                    p.div(id='edit', _class='grid_container')(
                        p.label(for_='edit_user')('Select a user:'),
                        p.select(id='edit_user', name='edit_user', required=True)(select_options_maker()),
                    ),
                    p.input(type='submit', id='edit_user_submit', name='edit_user_submit', value='Select')
                ),
                p.form(action='/master')(
                    p.h2('Add a new user'),
                    p.div(id='new_user', _class='grid_container')(
                        p.label(for_='first_name')('First name:'),
                        p.input(type='text', id='first_name', name='first_name', required=True),
                        p.label(for_='last_name', _class='mobile_gap')('Last name:'),
                        p.input(type='text', id='last_name', name='last_name', required=True),
                        p.label(for_='password', _class='mobile_gap')('Set a password:'),
                        p.input(type='text', id='password', name='password')
                    ),
                    p.p(class_='tooltip')('This field may be left blank'),
                    p.input(type='submit', id='new_user_submit', name='new_user_submit', value='Add'),
                    user_alr_exists
                ),
                p.form(action='/master')(
                    p.h2('Replace server data'),
                    p.input(type='file', name='data_file', accept='.json', required=True),
                    p.input(
                        type='submit', name='data_file_submit', value='Upload',
                        onclick='return confirm("This will replace all server data. Continue?");'
                    )
                )
            )
        )
    )
    return str(response)

@app.route('/edit/<user>', methods=['GET', 'POST'])
def edit(user):
    if 'name' not in session:
        return redirect('/login')
    elif session['name'] != 'Ethan Ryoo':
        return redirect('/')
    
    PAGE_NAME = 'Edit'

    if request.method == 'POST':
        data = load_file(DATA_FILE)
        index = int(request.form.get('txn_index'))
        if 'txn_edit_submit' in request.form:
            new_txn = {
                field: request.form[field]
                for field in ['type', 'date', 'amount']
            }
            if request.form['desc']:
                new_txn['desc'] = request.form['desc']
            else:
                new_txn['desc'] = request.form['type'].capitalize()
            if request.form['date'] == data[user]['transactions'][index]['date']:
                data[user]['transactions'][index] = new_txn
            else:
                data[user]['transactions'].pop(index)
                insert_transaction(data[user]['transactions'], new_txn)
        elif 'txn_delete' in request.form:
            data[user]['transactions'].pop(index)
        write_file(DATA_FILE, data)

    # Loading the (potentially) updated database
    data = load_file(DATA_FILE)
    if data[user]['transactions']:
        edit_form = p.form(txn_rows_maker(data[user]['transactions'], interactive=True, user=user))
    else:
        edit_form = p.p('No records found')
    nav_bar = nav_bar_maker()
    head = head_maker(PAGE_NAME, special_css=True)
    
    response = p.html(
        p.head(head),
        p.body(class_='dark' if data[session['name']]['dark_mode'] else '')(
            nav_bar,
            p.div(id='main')(
                p.h2(f'{user}\'s transaction history'),
                edit_form
            )
        )
    )
    return str(response)

@app.route('/edit/<user>/transaction_<i>', methods=['GET', 'POST'])
def edit_transaction(user, i):
    if 'name' not in session:
        return redirect('/login')
    elif session['name'] != 'Ethan Ryoo':
        return redirect('/')
    PAGE_NAME = 'Edit transaction'
    nav_bar = nav_bar_maker()
    head = head_maker(PAGE_NAME)
    txn_form = txn_form_contents_maker(user=user, txn_index=i)
    data = load_file(DATA_FILE)
    response = p.html(
        p.head(
            head,
            p.link(rel='stylesheet', href='/static/styles/master.css')
        ),
        p.body(class_='dark' if data[session['name']]['dark_mode'] else '')(
            nav_bar,
            p.div(id='main')(
                p.form(action=f'/edit/{user}')(
                    p.h2(f'Editing a transaction for {user}'),
                    p.div(id='transaction', _class='grid_container')(txn_form),
                    p.input(type='hidden', name='txn_index', value=i),
                    p.input(type='submit', id='txn_edit_submit', name='txn_edit_submit'),
                    p.input(
                        type='submit', id='txn_delete', name='txn_delete', value='Delete transaction',
                        onclick='return confirm("Are you sure? Deleting cannot be undone.");'
                    )
                )
            )
        )
    )
    return str(response)

@app.route('/toggle_dark_mode', methods=['POST'])
def toggle_dark_mode():
    if 'name' not in session:
        return 'Not logged in', 403
    data = load_file(DATA_FILE)
    data[session['name']]['dark_mode'] = not data[session['name']]['dark_mode']
    write_file(DATA_FILE, data)
    return 'Success', 200

@app.route('/log_out')
def log_out():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run()

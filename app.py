from flask import Flask, jsonify, request, render_template, session
from database import get_db_connection
import datetime
import requests

app = Flask(__name__)
app.secret_key = 'super_secret_casino_key' # In production, use a secure random key

DAILY_BONUS_AMOUNT = 500
BROKE_BONUS_AMOUNT = 100

def get_btc_price():
    # Simple mock or fetch to CoinDesk API for real-time price
    try:
        response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
        data = response.json()
        return data['bpi']['USD']['rate_float']
    except:
        return 60000.0 # Fallback mock price

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Username required'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        # Create new user
        conn.execute('INSERT INTO users (username) VALUES (?)', (username,))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    conn.close()

    session['username'] = username
    session['user_id'] = user['id']

    return jsonify({
        'message': 'Logged in successfully',
        'user': dict(user)
    })

@app.route('/api/balance', methods=['GET'])
def get_balance():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()

    return jsonify({'balance': user['balance']})

@app.route('/api/claim_daily', methods=['POST'])
def claim_daily():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    now = datetime.datetime.now()
    last_claim = user['last_daily_claim']

    if last_claim:
        last_claim_date = datetime.datetime.strptime(last_claim, '%Y-%m-%d %H:%M:%S.%f')
        if (now - last_claim_date).days < 1:
            conn.close()
            return jsonify({'error': 'Daily bonus already claimed today.'}), 400

    new_balance = user['balance'] + DAILY_BONUS_AMOUNT
    conn.execute('UPDATE users SET balance = ?, last_daily_claim = ? WHERE id = ?',
                 (new_balance, now, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'message': f'Claimed {DAILY_BONUS_AMOUNT} daily coins!', 'new_balance': new_balance})

@app.route('/api/claim_broke', methods=['POST'])
def claim_broke():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if user['balance'] > 0:
        conn.close()
        return jsonify({'error': 'You are not broke yet!'}), 400

    new_balance = BROKE_BONUS_AMOUNT
    conn.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'message': f'Claimed {BROKE_BONUS_AMOUNT} broke coins!', 'new_balance': new_balance})

@app.route('/api/withdraw_btc', methods=['POST'])
def withdraw_btc():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    amount_ingame = data.get('amount')
    btc_address = data.get('btc_address')

    if not amount_ingame or not btc_address:
        return jsonify({'error': 'Missing withdrawal details'}), 400

    try:
        amount_ingame = int(amount_ingame)
    except ValueError:
         return jsonify({'error': 'Invalid amount'}), 400

    if amount_ingame <= 0:
        return jsonify({'error': 'Withdrawal amount must be greater than zero'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if user['balance'] < amount_ingame:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400

    # Calculate conversion (Mock: 10,000 in-game = $1 USD worth of BTC for example)
    btc_price_usd = get_btc_price()
    usd_value = amount_ingame / 10000.0
    btc_amount = usd_value / btc_price_usd

    # Deduct balance
    new_balance = user['balance'] - amount_ingame
    conn.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))

    # Record pending withdrawal
    conn.execute('''
        INSERT INTO withdrawals (user_id, amount_ingame, btc_address, btc_amount)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], amount_ingame, btc_address, btc_amount))

    conn.commit()
    conn.close()

    return jsonify({
        'message': 'Withdrawal request submitted and is pending manual approval.',
        'btc_amount': btc_amount,
        'new_balance': new_balance
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

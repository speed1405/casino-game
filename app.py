from flask import Flask, jsonify, request, render_template, session
from database import get_db_connection
import datetime
import requests
import random
import os
from deck import create_deck, calculate_hand_blackjack, calculate_hand_baccarat

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

DAILY_BONUS_AMOUNT = 500
BROKE_BONUS_AMOUNT = 100

# In-memory game states
active_games = {}

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

# --- Blackjack Routes ---

@app.route('/api/blackjack/start', methods=['POST'])
def blackjack_start():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    bet = int(data.get('bet', 0))
    user_id = session['user_id']

    if bet <= 0: return jsonify({'error': 'Invalid bet'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
    if user['balance'] < bet:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400

    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet, user_id))
    conn.commit()
    conn.close()

    deck = create_deck(6)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    active_games[user_id] = {
        'game': 'blackjack',
        'deck': deck,
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'bet': bet,
        'status': 'playing'
    }

    p_val = calculate_hand_blackjack(player_hand)
    if p_val == 21:
        return resolve_blackjack_dealer(user_id)

    return jsonify({
        'player_hand': player_hand,
        'dealer_upcard': dealer_hand[0],
        'player_value': p_val,
        'status': 'playing'
    })

@app.route('/api/blackjack/hit', methods=['POST'])
def blackjack_hit():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401
    user_id = session['user_id']
    game = active_games.get(user_id)

    if not game or game['game'] != 'blackjack' or game['status'] != 'playing':
        return jsonify({'error': 'No active blackjack game'}), 400

    game['player_hand'].append(game['deck'].pop())
    p_val = calculate_hand_blackjack(game['player_hand'])

    if p_val > 21:
        game['status'] = 'bust'
        del active_games[user_id]
        return jsonify({
            'player_hand': game['player_hand'],
            'dealer_hand': game['dealer_hand'],
            'player_value': p_val,
            'dealer_value': calculate_hand_blackjack(game['dealer_hand']),
            'status': 'bust',
            'message': 'You busted!'
        })

    return jsonify({
        'player_hand': game['player_hand'],
        'dealer_upcard': game['dealer_hand'][0],
        'player_value': p_val,
        'status': 'playing'
    })

@app.route('/api/blackjack/stand', methods=['POST'])
def blackjack_stand():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401
    return resolve_blackjack_dealer(session['user_id'])

def resolve_blackjack_dealer(user_id):
    game = active_games.get(user_id)
    if not game or game['game'] != 'blackjack': return jsonify({'error': 'No active game'}), 400

    p_val = calculate_hand_blackjack(game['player_hand'])
    d_val = calculate_hand_blackjack(game['dealer_hand'])

    # Dealer hits on soft 17
    while True:
        d_val = calculate_hand_blackjack(game['dealer_hand'])
        if d_val < 17:
            game['dealer_hand'].append(game['deck'].pop())
        elif d_val == 17:
            # Check if it's a *soft* 17 (contains an Ace valued at 11)
            raw_val = sum(card_value_blackjack(c) for c in game['dealer_hand'])
            aces = sum(1 for c in game['dealer_hand'] if c['rank'] == 'A')
            # If subtracting 10 for every Ace but one leaves us at 6, then we have an Ace valued at 11
            is_soft = aces > 0 and (raw_val - (aces - 1) * 10) == 17
            if is_soft:
                game['dealer_hand'].append(game['deck'].pop())
            else:
                break
        else:
            break

    status = 'push'
    winnings = 0
    message = 'Push!'

    is_player_bj = p_val == 21 and len(game['player_hand']) == 2
    is_dealer_bj = d_val == 21 and len(game['dealer_hand']) == 2

    if is_player_bj and not is_dealer_bj:
        status = 'win'
        winnings = int(game['bet'] * 2.5) # 3:2 payout + original bet
        message = 'Blackjack!'
    elif d_val > 21 or p_val > d_val:
        status = 'win'
        winnings = game['bet'] * 2
        message = 'You win!'
    elif d_val > p_val:
        status = 'lose'
        message = 'Dealer wins!'
    elif p_val == d_val:
        if is_dealer_bj and not is_player_bj:
            status = 'lose'
            message = 'Dealer Blackjack!'
        else:
            status = 'push'
            winnings = game['bet']

    if winnings > 0:
        conn = get_db_connection()
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, user_id))
        conn.commit()
        conn.close()

    del active_games[user_id]

    return jsonify({
        'player_hand': game['player_hand'],
        'dealer_hand': game['dealer_hand'],
        'player_value': p_val,
        'dealer_value': d_val,
        'status': status,
        'message': message,
        'winnings': winnings
    })

# --- Texas Hold'em Routes ---
from treys import Card, Evaluator

def encode_treys_card(card_dict):
    """Converts our dict format to treys format (e.g. 'Ah', 'Tc')"""
    rank = card_dict['rank']
    if rank == '10': rank = 'T'
    suit_map = {'♠': 's', '♥': 'h', '♦': 'd', '♣': 'c'}
    return Card.new(rank + suit_map[card_dict['suit']])

@app.route('/api/poker/start', methods=['POST'])
def poker_start():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    buy_in = int(data.get('buy_in', 100))
    user_id = session['user_id']

    if buy_in < 10: return jsonify({'error': 'Minimum buy-in is 10'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
    if user['balance'] < buy_in:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400

    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (buy_in, user_id))
    conn.commit()
    conn.close()

    deck = create_deck()

    # 0 is player, 1-5 are AI
    players = {}
    for i in range(6):
        players[str(i)] = {
            'hand': [deck.pop(), deck.pop()],
            'chips': buy_in if i == 0 else random.randint(100, 500),
            'current_bet': 0,
            'folded': False,
            'is_all_in': False
        }

    active_games[user_id] = {
        'game': 'poker',
        'deck': deck,
        'players': players,
        'community_cards': [],
        'pot': 0,
        'current_bet': 0,
        'phase': 'pre-flop', # pre-flop, flop, turn, river, showdown
        'turn': '0' # Player acts first for simplicity in Phase 1
    }

    game = active_games[user_id]

    return jsonify(get_poker_state(user_id))

def get_poker_state(user_id):
    game = active_games.get(user_id)
    if not game: return {'error': 'No active game'}

    # Hide AI cards from player unless showdown
    state = {
        'phase': game['phase'],
        'pot': game['pot'],
        'community_cards': game['community_cards'],
        'current_bet': game['current_bet'],
        'turn': game['turn'],
        'players': {}
    }

    for pid, pdata in game['players'].items():
        state['players'][pid] = {
            'chips': pdata['chips'],
            'current_bet': pdata['current_bet'],
            'folded': pdata['folded']
        }
        if pid == '0' or game['phase'] == 'showdown':
            state['players'][pid]['hand'] = pdata['hand']

    return state

@app.route('/api/poker/action', methods=['POST'])
def poker_action():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401
    user_id = session['user_id']
    game = active_games.get(user_id)

    if not game or game['game'] != 'poker': return jsonify({'error': 'No active game'}), 400
    if game['turn'] != '0': return jsonify({'error': 'Not your turn'}), 400
    if game['phase'] == 'showdown': return jsonify({'error': 'Game over'}), 400

    data = request.json
    action = data.get('action') # fold, call, raise
    amount = int(data.get('amount', 0))

    player = game['players']['0']

    if action == 'fold':
        player['folded'] = True
    elif action == 'call':
        call_amount = game['current_bet'] - player['current_bet']
        if call_amount > player['chips']: call_amount = player['chips'] # All in
        player['chips'] -= call_amount
        player['current_bet'] += call_amount
        game['pot'] += call_amount
    elif action == 'raise':
        if amount <= 0: return jsonify({'error': 'Raise amount must be positive'}), 400
        total_bet = game['current_bet'] + amount
        if total_bet - player['current_bet'] > player['chips']: return jsonify({'error': 'Not enough chips'}), 400
        raise_amount = total_bet - player['current_bet']
        player['chips'] -= raise_amount
        player['current_bet'] += raise_amount
        game['pot'] += raise_amount
        game['current_bet'] = total_bet
    else:
        return jsonify({'error': 'Invalid action'}), 400

    # Process AI turns automatically
    process_ai_turns(game)
    advance_poker_phase(user_id, game)

    return jsonify(get_poker_state(user_id))

def process_ai_turns(game):
    # Very rudimentary AI for Phase 1
    for pid in range(1, 6):
        pid = str(pid)
        ai = game['players'][pid]
        if ai['folded'] or ai['chips'] == 0: continue

        call_amount = game['current_bet'] - ai['current_bet']

        # Simple logic: If call is too big, fold. Otherwise call.
        if call_amount > ai['chips'] * 0.5:
            if random.random() < 0.8: # 80% chance to fold to big bets
                ai['folded'] = True
                continue

        # Call
        actual_call = min(call_amount, ai['chips'])
        ai['chips'] -= actual_call
        ai['current_bet'] += actual_call
        game['pot'] += actual_call

def advance_poker_phase(user_id, game):
    active_players = sum(1 for p in game['players'].values() if not p['folded'])

    if active_players <= 1:
        game['phase'] = 'showdown'
        resolve_poker(user_id, game)
        return

    # Fast forward if the human player has folded but multiple AIs remain
    if game['players']['0']['folded'] and game['phase'] != 'showdown':
        # Fast-forward community cards to river
        while len(game['community_cards']) < 5:
            if len(game['community_cards']) == 0:
                game['community_cards'].extend([game['deck'].pop() for _ in range(3)])
            else:
                game['community_cards'].append(game['deck'].pop())
        game['phase'] = 'showdown'
        resolve_poker(user_id, game)
        return

    # Reset current bets for new phase
    for p in game['players'].values(): p['current_bet'] = 0
    game['current_bet'] = 0
    game['turn'] = '0' # Always player for simplicity

    if game['phase'] == 'pre-flop':
        game['phase'] = 'flop'
        game['community_cards'].extend([game['deck'].pop() for _ in range(3)])
    elif game['phase'] == 'flop':
        game['phase'] = 'turn'
        game['community_cards'].append(game['deck'].pop())
    elif game['phase'] == 'turn':
        game['phase'] = 'river'
        game['community_cards'].append(game['deck'].pop())
    elif game['phase'] == 'river':
        game['phase'] = 'showdown'
        resolve_poker(user_id, game)

def resolve_poker(user_id, game):
    evaluator = Evaluator()
    board = [encode_treys_card(c) for c in game['community_cards']]

    best_score = 9999
    winner_id = None

    active_pids = [pid for pid, p in game['players'].items() if not p['folded']]

    if len(active_pids) == 1:
        winner_id = active_pids[0]
    else:
        for pid in active_pids:
            hand = [encode_treys_card(c) for c in game['players'][pid]['hand']]
            score = evaluator.evaluate(board, hand)
            if score < best_score:
                best_score = score
                winner_id = pid

    game['players'][winner_id]['chips'] += game['pot']
    game['winner'] = winner_id

    # If player is winner or cashes out (simplified: player takes their remaining chips back to balance)
    player_final_chips = game['players']['0']['chips']
    if player_final_chips > 0:
        conn = get_db_connection()
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (player_final_chips, user_id))
        conn.commit()
        conn.close()

    game['pot'] = 0

# --- Slot Machine Routes ---

THEMES = {
    'scifi': {'symbols': ['🚀', '🛸', '👽', '🛰️', '🌠', 'WILD', 'SCATTER'], 'mechanic': 'cascading'},
    'egypt': {'symbols': ['👁️', '☥', '🪲', '🏺', '🐫', 'WILD', 'SCATTER'], 'mechanic': 'expanding_wilds'},
    'cyberpunk': {'symbols': ['🦾', '💾', '🌐', '🕶️', '💊', 'WILD', 'SCATTER'], 'mechanic': 'multipliers'}
}

def evaluate_slots(grid, theme_id, bet):
    winnings = 0
    lines_won = []
    multiplier = 1

    # Pre-process: Expanding Wilds (Egypt)
    if theme_id == 'egypt':
        for col in range(5):
            has_wild = any(grid[row][col] == 'WILD' for row in range(3))
            if has_wild:
                for row in range(3):
                    grid[row][col] = 'WILD'

    # Check horizontal lines for 3+ matches (accounting for WILDs)
    def check_line(row, start, end):
        first_symbol = None
        for i in range(start, end):
            if row[i] != 'WILD':
                if first_symbol is None:
                    first_symbol = row[i]
                elif row[i] != first_symbol:
                    return False
        return True

    def calculate_base_wins(current_grid):
        win = 0
        lines = []
        for i, row in enumerate(current_grid):
            # 5-match
            if check_line(row, 0, 5):
                win += bet * 10
                lines.append(i)
            # 3-match
            elif check_line(row, 0, 3) or check_line(row, 1, 4) or check_line(row, 2, 5):
                win += bet * 2
                if i not in lines: lines.append(i)
        return win, lines

    base_win, current_lines = calculate_base_wins(grid)
    winnings += base_win
    lines_won.extend(current_lines)

    # Post-process: Multipliers (Cyberpunk)
    if theme_id == 'cyberpunk' and len(current_lines) > 0:
        multiplier = 1 + len(current_lines) # Multiplier scales with number of winning lines
        winnings *= multiplier

    # Post-process: Cascading (Sci-Fi)
    if theme_id == 'scifi' and len(current_lines) > 0:
        # Simplified cascade: if a line wins, add a flat bonus to simulate the cascade falling into place
        # In a real front-end, we would return multiple grids to animate the fall
        winnings += bet * 3

    # Count Scatters
    scatters = sum(row.count('SCATTER') for row in grid)
    free_spins_won = 5 if scatters >= 3 else 0

    return winnings, lines_won, free_spins_won

@app.route('/api/slots/spin', methods=['POST'])
def slots_spin():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    bet = int(data.get('bet', 0))
    theme_id = data.get('theme', 'scifi')
    user_id = session['user_id']

    if theme_id not in THEMES: return jsonify({'error': 'Invalid theme'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    # Simple free spin tracking in session for MVP
    free_spins = session.get('free_spins', 0)

    if free_spins > 0:
        bet = session.get('last_bet', bet) # Use last bet amount for free spins
        session['free_spins'] -= 1
    else:
        if bet <= 0: return jsonify({'error': 'Invalid bet'}), 400
        if user['balance'] < bet:
            conn.close()
            return jsonify({'error': 'Insufficient balance'}), 400
        conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet, user_id))
        session['last_bet'] = bet

    symbols = THEMES[theme_id]['symbols']
    grid = [[random.choice(symbols) for _ in range(5)] for _ in range(3)]

    winnings, lines, spins_won = evaluate_slots(grid, theme_id, bet)

    if spins_won > 0:
        session['free_spins'] = session.get('free_spins', 0) + spins_won

    if winnings > 0:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, user_id))

    conn.commit()
    new_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()['balance']
    conn.close()

    return jsonify({
        'grid': grid,
        'winnings': winnings,
        'lines_won': lines,
        'free_spins_won': spins_won,
        'free_spins_remaining': session.get('free_spins', 0),
        'new_balance': new_balance
    })

# --- Baccarat Routes ---

@app.route('/api/baccarat/play', methods=['POST'])
def baccarat_play():
    if 'username' not in session: return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    bet_amount = int(data.get('bet', 0))
    bet_choice = data.get('choice') # 'player', 'banker', 'tie'
    user_id = session['user_id']

    if bet_amount <= 0 or bet_choice not in ['player', 'banker', 'tie']:
        return jsonify({'error': 'Invalid bet or choice'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
    if user['balance'] < bet_amount:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400

    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user_id))
    conn.commit()

    deck = create_deck(8)
    p_hand = [deck.pop(), deck.pop()]
    b_hand = [deck.pop(), deck.pop()]

    p_val = calculate_hand_baccarat(p_hand)
    b_val = calculate_hand_baccarat(b_hand)

    # Third card rules
    if p_val < 8 and b_val < 8:
        p_third = None
        if p_val <= 5:
            p_third = deck.pop()
            p_hand.append(p_third)
            p_val = calculate_hand_baccarat(p_hand)

        b_draws = False
        if b_val <= 2: b_draws = True
        elif b_val == 3 and (not p_third or p_third['rank'] != '8'): b_draws = True
        elif b_val == 4 and p_third and card_value_baccarat(p_third) in [2,3,4,5,6,7]: b_draws = True
        elif b_val == 5 and p_third and card_value_baccarat(p_third) in [4,5,6,7]: b_draws = True
        elif b_val == 6 and p_third and card_value_baccarat(p_third) in [6,7]: b_draws = True
        elif not p_third and b_val <= 5: b_draws = True

        if b_draws:
            b_hand.append(deck.pop())
            b_val = calculate_hand_baccarat(b_hand)

    winner = 'tie'
    if p_val > b_val: winner = 'player'
    elif b_val > p_val: winner = 'banker'

    winnings = 0
    if bet_choice == winner:
        if winner == 'player': winnings = bet_amount * 2
        elif winner == 'banker': winnings = int(bet_amount * 1.95) # 5% commission
        elif winner == 'tie': winnings = (bet_amount * 8) + bet_amount
    elif winner == 'tie' and bet_choice in ['player', 'banker']:
        winnings = bet_amount # Push on tie

    if winnings > 0:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, user_id))
        conn.commit()

    conn.close()

    return jsonify({
        'player_hand': p_hand,
        'banker_hand': b_hand,
        'player_value': p_val,
        'banker_value': b_val,
        'winner': winner,
        'winnings': winnings
    })

if __name__ == '__main__':
    from database import init_db
    init_db()
    app.run(debug=True, port=5000)

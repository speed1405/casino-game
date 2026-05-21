document.addEventListener('DOMContentLoaded', () => {

    // UI Elements
    const loginScreen = document.getElementById('login-screen');
    const appScreen = document.getElementById('app-screen');
    const lobbyArea = document.getElementById('lobby-area');
    const gameArea = document.getElementById('game-area');
    const withdrawModal = document.getElementById('withdraw-modal');

    const loginBtn = document.getElementById('login-btn');
    const usernameInput = document.getElementById('username-input');
    const loginError = document.getElementById('login-error');

    const playerNameDisplay = document.getElementById('player-name');
    const balanceDisplay = document.getElementById('balance');
    const claimDailyBtn = document.getElementById('claim-daily-btn');
    const claimBrokeBtn = document.getElementById('claim-broke-btn');
    const withdrawBtn = document.getElementById('withdraw-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const backToLobbyBtn = document.getElementById('back-to-lobby-btn');
    const gameCards = document.querySelectorAll('.game-card');
    const currentGameTitle = document.getElementById('current-game-title');

    const closeWithdrawBtn = document.querySelector('.close-btn');
    const submitWithdrawBtn = document.getElementById('submit-withdraw-btn');
    const withdrawAmount = document.getElementById('withdraw-amount');
    const withdrawAddress = document.getElementById('withdraw-address');
    const withdrawMsg = document.getElementById('withdraw-msg');

    let currentBalance = 0;

    // --- Authentication ---

    loginBtn.addEventListener('click', async () => {
        const username = usernameInput.value.trim();
        if (!username) {
            loginError.textContent = "Please enter a username.";
            return;
        }

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username })
            });
            const data = await res.json();

            if (res.ok) {
                playerNameDisplay.textContent = data.user.username;
                loginScreen.classList.remove('active');
                appScreen.classList.add('active');
                updateBalance();
            } else {
                loginError.textContent = data.error;
            }
        } catch (err) {
            loginError.textContent = "Server error. Try again later.";
        }
    });

    logoutBtn.addEventListener('click', () => {
        // Simple client-side logout for phase 1
        usernameInput.value = '';
        appScreen.classList.remove('active');
        loginScreen.classList.add('active');
    });

    // --- Economy ---

    async function updateBalance() {
        try {
            const res = await fetch('/api/balance');
            if (res.ok) {
                const data = await res.json();
                currentBalance = data.balance;
                balanceDisplay.textContent = currentBalance;

                if (currentBalance === 0) {
                    claimBrokeBtn.style.display = 'inline-block';
                } else {
                    claimBrokeBtn.style.display = 'none';
                }
            }
        } catch (err) {
            console.error("Failed to fetch balance", err);
        }
    }

    claimDailyBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/claim_daily', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                alert(data.message);
                updateBalance();
            } else {
                alert(data.error);
            }
        } catch (err) {
            console.error("Failed to claim daily", err);
        }
    });

    claimBrokeBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/claim_broke', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                alert(data.message);
                updateBalance();
            } else {
                alert(data.error);
            }
        } catch (err) {
            console.error("Failed to claim broke bonus", err);
        }
    });

    // --- Withdrawals ---

    withdrawBtn.addEventListener('click', () => {
        withdrawModal.style.display = 'block';
        withdrawMsg.textContent = '';
        withdrawMsg.style.color = 'var(--text-main)';
    });

    closeWithdrawBtn.addEventListener('click', () => {
        withdrawModal.style.display = 'none';
    });

    submitWithdrawBtn.addEventListener('click', async () => {
        const amount = withdrawAmount.value;
        const address = withdrawAddress.value.trim();

        if (!amount || amount < 1000) {
            withdrawMsg.style.color = 'var(--warning)';
            withdrawMsg.textContent = "Minimum withdrawal is 1000 coins.";
            return;
        }
        if (!address) {
            withdrawMsg.style.color = 'var(--warning)';
            withdrawMsg.textContent = "Please provide a BTC address.";
            return;
        }

        withdrawMsg.style.color = 'var(--text-main)';
        withdrawMsg.textContent = "Processing...";

        try {
            const res = await fetch('/api/withdraw_btc', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount, btc_address: address })
            });
            const data = await res.json();

            if (res.ok) {
                withdrawMsg.style.color = 'var(--secondary)';
                withdrawMsg.textContent = `${data.message} Est: ${data.btc_amount.toFixed(8)} BTC`;
                updateBalance();
                setTimeout(() => {
                    withdrawModal.style.display = 'none';
                    withdrawAmount.value = '';
                    withdrawAddress.value = '';
                }, 3000);
            } else {
                withdrawMsg.style.color = 'var(--warning)';
                withdrawMsg.textContent = data.error;
            }
        } catch (err) {
            withdrawMsg.style.color = 'var(--warning)';
            withdrawMsg.textContent = "Server error. Try again later.";
        }
    });

    // --- Navigation (Lobby to Games) ---

    const gameUIs = {
        'slots': document.getElementById('slots-ui'), // For later
        'blackjack': document.getElementById('blackjack-ui'),
        'baccarat': document.getElementById('baccarat-ui'),
        'poker': document.getElementById('poker-ui') // For later
    };

    gameCards.forEach(card => {
        card.addEventListener('click', () => {
            const gameName = card.querySelector('h3').textContent;
            const gameType = card.dataset.game;

            currentGameTitle.textContent = gameName;

            // Hide all UIs, show the right one
            Object.values(gameUIs).forEach(ui => { if(ui) ui.style.display = 'none'; });
            if (gameUIs[gameType]) gameUIs[gameType].style.display = 'block';

            // Reset states
            if(gameType === 'blackjack') resetBlackjackUI();
            if(gameType === 'baccarat') resetBaccaratUI();
            if(gameType === 'slots') resetSlotsUI();
            if(gameType === 'poker') resetPokerUI();

            lobbyArea.classList.remove('active');
            gameArea.classList.add('active');
        });
    });

    backToLobbyBtn.addEventListener('click', () => {
        gameArea.classList.remove('active');
        lobbyArea.classList.add('active');
        updateBalance();
    });

    // Close modal if clicked outside
    window.addEventListener('click', (event) => {
        if (event.target == withdrawModal) {
            withdrawModal.style.display = "none";
        }
    });

    // --- Poker Logic ---
    const pokerBuyinInput = document.getElementById('poker-buyin-input');
    const pokerStartBtn = document.getElementById('poker-start-btn');
    const pokerStartControls = document.getElementById('poker-start-controls');
    const pokerPlayControls = document.getElementById('poker-play-controls');
    const pokerMessage = document.getElementById('poker-message');
    const pokerFoldBtn = document.getElementById('poker-fold-btn');
    const pokerCallBtn = document.getElementById('poker-call-btn');
    const pokerRaiseBtn = document.getElementById('poker-raise-btn');
    const pokerRaiseInput = document.getElementById('poker-raise-input');

    function resetPokerUI() {
        pokerMessage.textContent = '';
        document.getElementById('poker-community-cards').innerHTML = '';
        document.getElementById('poker-pot').textContent = '0';
        document.getElementById('poker-ai-players').innerHTML = '';
        document.getElementById('poker-player-cards').innerHTML = '';
        document.getElementById('poker-player-chips').textContent = '0';

        pokerStartControls.style.display = 'block';
        pokerPlayControls.style.display = 'none';
    }

    pokerStartBtn.addEventListener('click', async () => {
        const buy_in = pokerBuyinInput.value;
        if (!buy_in || buy_in < 10) return alert("Minimum buy-in is 10");

        try {
            const res = await fetch('/api/poker/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({buy_in})
            });
            const data = await res.json();
            if(!res.ok) return alert(data.error);

            updateBalance();
            pokerStartControls.style.display = 'none';
            renderPokerState(data);
        } catch(e) { console.error(e); }
    });

    async function sendPokerAction(action, amount=0) {
        try {
            const res = await fetch('/api/poker/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action, amount})
            });
            const data = await res.json();
            if(!res.ok) return alert(data.error);
            renderPokerState(data);
        } catch(e) { console.error(e); }
    }

    pokerFoldBtn.addEventListener('click', () => sendPokerAction('fold'));
    pokerCallBtn.addEventListener('click', () => sendPokerAction('call'));
    pokerRaiseBtn.addEventListener('click', () => {
        const amt = pokerRaiseInput.value;
        if(!amt || amt <= 0) return alert("Enter valid raise");
        sendPokerAction('raise', amt);
    });

    function renderPokerState(data) {
        if(data.error) return alert(data.error);

        // Phase & Pot
        document.getElementById('poker-pot').textContent = data.pot;
        pokerMessage.textContent = `Phase: ${data.phase.toUpperCase()}`;

        // Community Cards
        document.getElementById('poker-community-cards').innerHTML =
            data.community_cards.map(c => renderCard(c)).join('');

        // Player
        const player = data.players['0'];
        document.getElementById('poker-player-chips').textContent = player.chips;
        document.getElementById('poker-player-cards').innerHTML =
            player.hand ? player.hand.map(c => renderCard(c)).join('') : '';

        // AI Players
        let aiHtml = '';
        for(let i=1; i<=5; i++) {
            const ai = data.players[i.toString()];
            const isFolded = ai.folded ? 'folded' : '';

            let cardsHtml = '';
            if (ai.hand) {
                cardsHtml = ai.hand.map(c => renderCard(c)).join(''); // Showdown
            } else if (!ai.folded) {
                cardsHtml = renderCard(null, true) + renderCard(null, true); // Hidden
            }

            aiHtml += `
                <div class="poker-ai ${isFolded}">
                    <div style="font-size:0.8rem">AI ${i}</div>
                    <div style="font-size:0.8rem">🪙 ${ai.chips}</div>
                    <div class="card-container">${cardsHtml}</div>
                </div>
            `;
        }
        document.getElementById('poker-ai-players').innerHTML = aiHtml;

        // Controls
        if (data.phase === 'showdown' || player.folded) {
            pokerPlayControls.style.display = 'none';
            pokerStartControls.style.display = 'block';
            pokerStartBtn.textContent = "Play Again";
            if (data.phase === 'showdown') {
                updateBalance(); // Player gets chips back
            }
        } else if (player.chips === 0 && data.phase !== 'showdown') {
             // Player is all in, cannot bet, but needs to advance game
             pokerPlayControls.style.display = 'block';
             pokerStartControls.style.display = 'none';
             pokerFoldBtn.style.display = 'none';
             pokerRaiseBtn.style.display = 'none';
             pokerRaiseInput.style.display = 'none';
             pokerCallBtn.textContent = "Next Phase (All-In)";
        } else {
            pokerPlayControls.style.display = 'block';
            pokerStartControls.style.display = 'none';
            pokerFoldBtn.style.display = 'inline-block';
            pokerRaiseBtn.style.display = 'inline-block';
            pokerRaiseInput.style.display = 'inline-block';
            pokerCallBtn.textContent = "Call / Check";
        }
    }

    // --- Slots Logic ---
    const slotsThemeSelect = document.getElementById('slots-theme');
    const slotsBetInput = document.getElementById('slots-bet-input');
    const slotsSpinBtn = document.getElementById('slots-spin-btn');
    const slotsGridContainer = document.getElementById('slots-grid');
    const slotsMessage = document.getElementById('slots-message');
    const freeSpinsBadge = document.getElementById('slots-free-spins-badge');

    function resetSlotsUI() {
        slotsMessage.textContent = '';
        slotsGridContainer.innerHTML = '';
        freeSpinsBadge.style.display = 'none';

        // Initial empty grid
        for(let i=0; i<3; i++){
            let rowHtml = '<div class="slots-row">';
            for(let j=0; j<5; j++) rowHtml += `<div class="slot-symbol">❓</div>`;
            rowHtml += '</div>';
            slotsGridContainer.innerHTML += rowHtml;
        }
    }

    slotsSpinBtn.addEventListener('click', async () => {
        const bet = slotsBetInput.value;
        const theme = slotsThemeSelect.value;

        // Disable spin during animation
        slotsSpinBtn.disabled = true;

        try {
            const res = await fetch('/api/slots/spin', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({bet, theme})
            });
            const data = await res.json();
            if(!res.ok) {
                alert(data.error);
                slotsSpinBtn.disabled = false;
                return;
            }

            // Render result
            let gridHtml = '';
            data.grid.forEach((row, rowIndex) => {
                gridHtml += '<div class="slots-row">';
                row.forEach(symbol => {
                    const isWinLine = data.lines_won.includes(rowIndex);
                    gridHtml += `<div class="slot-symbol ${isWinLine ? 'winning' : ''}">${symbol}</div>`;
                });
                gridHtml += '</div>';
            });
            slotsGridContainer.innerHTML = gridHtml;

            let msg = '';
            if (data.winnings > 0) msg += `You won ${data.winnings} coins! `;
            if (data.free_spins_won > 0) msg += `🎉 You won ${data.free_spins_won} FREE SPINS! `;
            slotsMessage.textContent = msg;

            if (data.free_spins_remaining > 0) {
                freeSpinsBadge.style.display = 'inline-block';
                freeSpinsBadge.textContent = `Free Spins: ${data.free_spins_remaining}`;
                slotsBetInput.disabled = true; // Lock bet during free spins
            } else {
                freeSpinsBadge.style.display = 'none';
                slotsBetInput.disabled = false;
            }

            updateBalance();

        } catch(e) {
            console.error(e);
        } finally {
            slotsSpinBtn.disabled = false;
        }
    });

    // --- Card Rendering Utils ---
    function renderCard(cardData, hidden=false) {
        if (hidden) return `<div class="playing-card hidden"></div>`;
        const color = (cardData.suit === '♥' || cardData.suit === '♦') ? 'red' : 'black';
        return `<div class="playing-card ${color}">
            <div class="val">${cardData.rank}</div>
            <div class="suit">${cardData.suit}</div>
        </div>`;
    }

    // --- Blackjack Logic ---
    const bjBetInput = document.getElementById('bj-bet-input');
    const bjDealBtn = document.getElementById('bj-deal-btn');
    const bjHitBtn = document.getElementById('bj-hit-btn');
    const bjStandBtn = document.getElementById('bj-stand-btn');
    const bjMessage = document.getElementById('bj-message');

    function resetBlackjackUI() {
        document.getElementById('bj-dealer-cards').innerHTML = '';
        document.getElementById('bj-player-cards').innerHTML = '';
        document.getElementById('bj-dealer-val').textContent = '';
        document.getElementById('bj-player-val').textContent = '';
        bjMessage.textContent = '';
        document.getElementById('bj-bet-controls').style.display = 'block';
        document.getElementById('bj-play-controls').style.display = 'none';
    }

    bjDealBtn.addEventListener('click', async () => {
        const bet = bjBetInput.value;
        if (!bet || bet <= 0) return alert("Enter a valid bet");

        try {
            const res = await fetch('/api/blackjack/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({bet})
            });
            const data = await res.json();
            if(!res.ok) return alert(data.error);

            updateBalance();
            document.getElementById('bj-bet-controls').style.display = 'none';

            renderBlackjackState(data);
        } catch(e) { console.error(e); }
    });

    bjHitBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/blackjack/hit', {method: 'POST'});
            const data = await res.json();
            renderBlackjackState(data);
        } catch(e) { console.error(e); }
    });

    bjStandBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/blackjack/stand', {method: 'POST'});
            const data = await res.json();
            renderBlackjackState(data);
        } catch(e) { console.error(e); }
    });

    function renderBlackjackState(data) {
        let pCardsHtml = data.player_hand.map(c => renderCard(c)).join('');
        document.getElementById('bj-player-cards').innerHTML = pCardsHtml;
        document.getElementById('bj-player-val').textContent = data.player_value;

        if (data.status === 'playing') {
            document.getElementById('bj-play-controls').style.display = 'block';
            document.getElementById('bj-dealer-cards').innerHTML = renderCard(data.dealer_upcard) + renderCard(null, true);
            document.getElementById('bj-dealer-val').textContent = '?';
            bjMessage.textContent = "Hit or Stand?";
        } else {
            document.getElementById('bj-play-controls').style.display = 'none';
            document.getElementById('bj-bet-controls').style.display = 'block';
            let dCardsHtml = data.dealer_hand.map(c => renderCard(c)).join('');
            document.getElementById('bj-dealer-cards').innerHTML = dCardsHtml;
            document.getElementById('bj-dealer-val').textContent = data.dealer_value;
            bjMessage.textContent = `${data.message} ${data.winnings ? '(+$' + data.winnings + ')' : ''}`;
            updateBalance();
        }
    }

    // --- Baccarat Logic ---
    const bacBetInput = document.getElementById('bac-bet-input');
    const bacMessage = document.getElementById('bac-message');

    function resetBaccaratUI() {
        document.getElementById('bac-player-cards').innerHTML = '';
        document.getElementById('bac-banker-cards').innerHTML = '';
        document.getElementById('bac-player-val').textContent = '';
        document.getElementById('bac-banker-val').textContent = '';
        bacMessage.textContent = '';
    }

    window.playBaccarat = async function(choice) {
        const bet = bacBetInput.value;
        if (!bet || bet <= 0) return alert("Enter a valid bet");

        try {
            const res = await fetch('/api/baccarat/play', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({bet, choice})
            });
            const data = await res.json();
            if(!res.ok) return alert(data.error);

            document.getElementById('bac-player-cards').innerHTML = data.player_hand.map(c => renderCard(c)).join('');
            document.getElementById('bac-banker-cards').innerHTML = data.banker_hand.map(c => renderCard(c)).join('');
            document.getElementById('bac-player-val').textContent = data.player_value;
            document.getElementById('bac-banker-val').textContent = data.banker_value;

            bacMessage.textContent = `Winner: ${data.winner.toUpperCase()}! ${data.winnings ? 'You won ' + data.winnings : 'You lost.'}`;
            updateBalance();
        } catch(e) { console.error(e); }
    };

});

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

    gameCards.forEach(card => {
        card.addEventListener('click', () => {
            const gameName = card.querySelector('h3').textContent;
            currentGameTitle.textContent = `Loading ${gameName}...`;

            lobbyArea.classList.remove('active');
            gameArea.classList.add('active');
        });
    });

    backToLobbyBtn.addEventListener('click', () => {
        gameArea.classList.remove('active');
        lobbyArea.classList.add('active');
        updateBalance(); // Refresh balance in case they spent money in game
    });

    // Close modal if clicked outside
    window.addEventListener('click', (event) => {
        if (event.target == withdrawModal) {
            withdrawModal.style.display = "none";
        }
    });

});

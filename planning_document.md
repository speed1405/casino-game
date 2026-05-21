# Casino Web Application Planning Document

## 1. Overview
The Casino Web Application is a full-stack project featuring a web-based user interface and a robust backend to handle game logic and virtual economy. The application will feature a lobby and four distinct casino games: a modern 5-reel Slot Machine, Blackjack, Baccarat, and Texas Hold'em Poker played against 5 AI opponents.

## 2. Technology Stack
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript. Simple visual elements will be built using CSS and Unicode characters (e.g., card suits ♠️♥️♦️♣️, slot symbols 🍒🔔💎) instead of heavy image assets.
*   **Backend:** Python with Flask (or FastAPI).
*   **Database:** SQLite to store user profiles, balances, and timestamp of daily coin claims.

## 3. Core Features & Economy
*   **User System:** A simple login system (username based) allowing multiple users to have independent tracked balances.
*   **Virtual Economy:**
    *   Players wager using an in-game currency.
    *   **Daily Bonus:** Players can claim a daily coin reward.
    *   **Broke Bonus:** A fallback button to claim a small amount of coins if the player goes bankrupt, ensuring they can keep playing.
*   **Lobby/Dashboard:** The main landing page post-login. Displays the player's current balance, provides buttons to claim daily/free coins, and features navigation links to the four games.

## 4. Games Specification

### 4.1. Slot Machine
*   **Style:** Modern 5-reel video slot.
*   **Mechanics:** Players select their bet amount and spin. The backend will randomly generate a 5x3 grid of symbols.
*   **Payouts:** Specific paylines will be checked (e.g., horizontal lines, V-shapes). Payouts are based on the rarity and sequence of the matching symbols.

### 4.2. Blackjack
*   **Rules:** Standard rules. Blackjack pays 3:2. The dealer must hit on soft 17 (or stand on all 17s, depending on configuration).
*   **Actions:** Hit, Stand, Double Down. (Split can be added in later iterations to simplify initial development).
*   **Flow:** Player places bet -> Cards dealt -> Player turns -> Dealer turn -> Payout calculation.

### 4.3. Baccarat
*   **Rules:** Standard Baccarat rules.
*   **Betting Options:** Player (1:1), Banker (1:1 minus 5% commission, or standard adjusted payouts), Tie (8:1).
*   **Flow:** Player places bet on a selection -> Cards are dealt according to the strict drawing rules -> Winner is determined and payouts processed.

### 4.4. Texas Hold'em Poker
*   **Format:** Single-player vs. 5 AI opponents.
*   **Flow:**
    *   **Pre-flop, Flop, Turn, River:** Standard betting rounds.
    *   **Player Actions:** Fold, Check, Call, Raise.
    *   **AI:** The 5 AI opponents will have rudimentary logic to evaluate their hand strength and pot odds to make decisions.
*   **UI:** A turn-based interface that halts and waits for the human player's input when it is their turn, while automatically processing AI turns with a slight delay for visual pacing.

## 5. Architecture & Data Flow
1.  **Client-Side (Browser):** Renders the UI and handles user inputs. Sends asynchronous HTTP requests (AJAX/Fetch) or uses WebSockets (for poker pacing if necessary) to communicate with the backend.
2.  **Server-Side (Python Backend):**
    *   Receives actions from the client.
    *   Validates moves (e.g., checking if the player has enough balance).
    *   Executes game logic (RNG for shuffles and spins).
    *   Updates the SQLite database with the new balance.
    *   Returns the updated game state to the client.

## 6. Implementation Phases
*   **Phase 1: Setup & Economy.** Initialize backend, database, and simple login. Create the lobby and the daily coin collection system.
*   **Phase 2: Single Player Games.** Implement Blackjack and Baccarat (Frontend UI and Backend logic).
*   **Phase 3: Slot Machine.** Develop the 5-reel generation logic and payline calculation.
*   **Phase 4: Texas Hold'em.** Build the poker engine, hand evaluator, AI opponent logic, and complex turn-based UI.
*   **Phase 5: Polish & Testing.** Refine UI/UX, verify rules, and ensure economy balance.

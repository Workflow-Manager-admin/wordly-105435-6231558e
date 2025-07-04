import random
import string
from typing import List, Dict, Optional

# --- Static 5-letter words as the word bank ---
WORD_LIST = [
    "apple", "brave", "cabin", "delta", "eager", "fancy", "giant", "honey", "input", 
    "joker", "karma", "lemon", "mango", "noble", "ocean", "pride", "quiet", "raven",
    "salad", "table", "umbra", "vivid", "whale", "xenon", "yacht", "zebra"
]

MAX_ATTEMPTS = 6

class GameState:
    """
    Stores state for a user's game session.
    """
    def __init__(self, answer: str):
        self.answer = answer
        self.guesses: List[str] = []
        self.feedback: List[List[str]] = []  # Holds history of feedback as color codes (green, yellow, gray)
        self.solved = False
        self.failed = False

# PUBLIC_INTERFACE
def select_random_word() -> str:
    """
    Returns a random 5-letter word from the static word list.
    """
    return random.choice(WORD_LIST)

# Color codes (could be used as strings for frontend compatibility)
COLOR_CORRECT = "green"   # Correct letter, correct position
COLOR_PRESENT = "yellow"  # Correct letter, wrong position
COLOR_ABSENT = "gray"     # Letter not in word

# PUBLIC_INTERFACE
def validate_guess(guess: str, answer: str) -> List[str]:
    """
    Given a guess and the answer, returns color feedback per letter.
    Each position returns: COLOR_CORRECT, COLOR_PRESENT, or COLOR_ABSENT.

    Args:
        guess: The guessed 5-letter word
        answer: The actual answer word

    Returns:
        List of 5 strings with color feedback
    """
    guess = guess.lower()
    answer = answer.lower()

    feedback = [COLOR_ABSENT] * 5
    answer_chars = list(answer)
    guess_chars = list(guess)

    # Track matched positions to avoid extra yellows for duplicates
    answer_used = [False] * 5

    # First pass: correct (green)
    for i in range(5):
        if guess_chars[i] == answer_chars[i]:
            feedback[i] = COLOR_CORRECT
            answer_used[i] = True

    # Second pass: present (yellow)
    for i in range(5):
        if feedback[i] == COLOR_CORRECT:
            continue
        for j in range(5):
            if not answer_used[j] and guess_chars[i] == answer_chars[j]:
                feedback[i] = COLOR_PRESENT
                answer_used[j] = True
                break
    # Gray is left by default
    return feedback

# PUBLIC_INTERFACE
def is_valid_word(word: str) -> bool:
    """
    Validates that the word is a 5-letter, lowercase, and in the word list.
    """
    return word.isalpha() and len(word) == 5 and word.lower() in WORD_LIST

# --- Simple in-memory user "session" storage. In production, use Redis or a DB ---
_sessions: Dict[str, GameState] = {}

# PUBLIC_INTERFACE
def new_game_for_user(user_id: str) -> GameState:
    """
    Creates a new game for the given user, stores it in memory, and returns the GameState.

    Args:
        user_id: Unique identifier for user/session (e.g. uuid or session token)

    Returns:
        GameState
    """
    answer = select_random_word()
    state = GameState(answer)
    _sessions[user_id] = state
    return state

# PUBLIC_INTERFACE
def get_game_state(user_id: str) -> Optional[GameState]:
    """
    Retrieves game state for the user, or None if not found.
    """
    return _sessions.get(user_id)

# PUBLIC_INTERFACE
def handle_guess(user_id: str, guess: str) -> Dict:
    """
    Registers a guess for the user, validates it, and updates the game state.

    Args:
        user_id: Unique identifier for user/session
        guess: The guessed word

    Returns:
        Dictionary with keys:
          - valid (bool)
          - feedback (List[str])
          - solved (bool)
          - failed (bool)
          - guesses (List[str])
          - attempts_left (int)
          - message (str)
    """
    gs = get_game_state(user_id)
    if not gs:
        return {"valid": False, "message": "Game session not found."}
    if gs.solved or gs.failed:
        return {"valid": False, "message": "Game already completed."}

    guess = guess.lower()
    if not is_valid_word(guess):
        return {"valid": False, "message": "Not a valid 5-letter word."}
    if guess in gs.guesses:
        return {"valid": False, "message": "Word already guessed."}

    feedback = validate_guess(guess, gs.answer)
    gs.guesses.append(guess)
    gs.feedback.append(feedback)

    solved = guess == gs.answer
    failed = not solved and len(gs.guesses) >= MAX_ATTEMPTS

    gs.solved = solved
    gs.failed = failed

    if solved:
        msg = "Congratulations! You've guessed the word."
    elif failed:
        msg = f"Game over! The word was {gs.answer}."
    else:
        msg = "Guess registered."

    return {
        "valid": True,
        "feedback": feedback,
        "solved": solved,
        "failed": failed,
        "guesses": gs.guesses,
        "attempts_left": MAX_ATTEMPTS - len(gs.guesses),
        "message": msg
    }

# PUBLIC_INTERFACE
def reset_game(user_id: str) -> GameState:
    """
    Resets the game session for the user.
    """
    return new_game_for_user(user_id)

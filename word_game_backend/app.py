from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

import uuid

import game_logic
import leaderboard

app = FastAPI(
    title="Word Guessing Game Backend",
    description="Backend for 5-letter word guessing game. Handles game logic, feedback, and state.",
    version="0.1.0",
    openapi_tags=[
        {"name": "game", "description": "Word guessing game endpoints"},
        {"name": "leaderboard", "description": "Leaderboard endpoints and score submission"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NewGameResponse(BaseModel):
    user_id: str = Field(..., description="Session/user id for this game")
    guesses: List[str] = Field(..., description="Past guesses")
    solved: bool = Field(..., description="Game is solved")
    failed: bool = Field(..., description="Game is failed")
    attempts_left: int = Field(..., description="Attempts remaining")

class GuessRequest(BaseModel):
    guess: str = Field(..., description="The guess (must be a 5-letter word)")

class GuessResponse(BaseModel):
    valid: bool = Field(..., description="Is the guess valid and processed")
    feedback: List[str] = Field(..., description="'green', 'yellow', or 'gray' per letter")
    solved: bool = Field(..., description="Is game solved (True if just won)")
    failed: bool = Field(..., description="Is game failed (out of attempts)")
    guesses: List[str] = Field(..., description="Guess history")
    attempts_left: int = Field(..., description="Attempts remaining")
    message: str = Field(..., description="Result message (info or error)")

class StateResponse(BaseModel):
    guesses: List[str]
    feedback: List[List[str]]
    solved: bool
    failed: bool
    attempts_left: int

class SubmitScoreRequest(BaseModel):
    user_id: str = Field(..., description="Your game user_id")
    username: str = Field(..., description="Display name or player name")
    attempts: int = Field(..., description="Number of attempts taken to solve the game")
    solved: bool = Field(..., description="Whether the game was solved (True) or not (False)")

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    attempts: int
    timestamp: str

class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]

# PUBLIC_INTERFACE
@app.post(
    "/game/new",
    response_model=NewGameResponse,
    tags=["game"],
    summary="Start a new game session"
)
@app.post(
    "/api/new-game",
    response_model=NewGameResponse,
    tags=["game", "api"],
    summary="[API alias] Start a new game session (returns new user_id and initial game state)"
)
def new_game(user_id: Optional[str] = Query(None, description="Provide a user_id to continue; otherwise, a random id is generated.")):
    """Start a new game and return session info. Returns a new user_id if not provided.

    This endpoint is also available at /api/new-game for RESTful aliasing.
    ---
    - Returns session state and user_id to be used in subsequent requests.
    """
    if not user_id:
        user_id = str(uuid.uuid4())
    gs = game_logic.new_game_for_user(user_id)
    return NewGameResponse(
        user_id=user_id,
        guesses=gs.guesses,
        solved=gs.solved,
        failed=gs.failed,
        attempts_left=game_logic.MAX_ATTEMPTS
    )

# PUBLIC_INTERFACE
@app.post(
    "/game/guess",
    response_model=GuessResponse,
    tags=["game"],
    summary="Submit a guess for the current game"
)
@app.post(
    "/api/guess",
    response_model=GuessResponse,
    tags=["game", "api"],
    summary="[API alias] Submit a guess for the current game (returns feedback, state)"
)
def make_guess(user_id: str = Query(..., description="Your game user_id"), req: GuessRequest = ...):
    """Submit a 5-letter guess, receive feedback and update the game session. Returns color feedback per letter.

    This endpoint is also available as /api/guess for easier REST integration.
    """
    result = game_logic.handle_guess(user_id, req.guess)
    if not result.get("valid"):
        # On errors, always send 400 error with informative message
        return JSONResponse(status_code=400, content=result)
    # Success
    return GuessResponse(
        valid=result["valid"],
        feedback=result["feedback"],
        solved=result["solved"],
        failed=result["failed"],
        guesses=result["guesses"],
        attempts_left=result["attempts_left"],
        message=result["message"]
    )

# PUBLIC_INTERFACE
@app.post(
    "/game/reset",
    response_model=NewGameResponse,
    tags=["game"],
    summary="Reset game session for this user_id"
)
def reset_game(user_id: str = Query(..., description="Your game user_id")):
    """Reset the game session for this user (starts over with a new word)."""
    gs = game_logic.reset_game(user_id)
    return NewGameResponse(
        user_id=user_id,
        guesses=gs.guesses,
        solved=gs.solved,
        failed=gs.failed,
        attempts_left=game_logic.MAX_ATTEMPTS
    )

# PUBLIC_INTERFACE
@app.get(
    "/game/state",
    response_model=StateResponse,
    tags=["game"],
    summary="Get game state for this user_id"
)
def get_state(user_id: str = Query(..., description="Your game user_id")):
    """Returns the entire game state for the current session."""
    gs = game_logic.get_game_state(user_id)
    if not gs:
        return JSONResponse(status_code=404, content={"message": "Game session not found"})
    return StateResponse(
        guesses=gs.guesses,
        feedback=gs.feedback,
        solved=gs.solved,
        failed=gs.failed,
        attempts_left=game_logic.MAX_ATTEMPTS - len(gs.guesses)
    )

# PUBLIC_INTERFACE
@app.post(
    "/leaderboard/submit",
    tags=["leaderboard"],
    summary="Submit completed game to the leaderboard"
)
@app.post(
    "/api/submit-score",
    tags=["leaderboard", "api"],
    summary="[API alias] Submit completed game to the leaderboard and persist score"
)
def submit_score(req: SubmitScoreRequest):
    """
    Submit a completed game to the leaderboard.
    - user_id: Session/player id
    - username: Display/player name for leaderboard
    - attempts: Number of attempts taken
    - solved: If True, treated as valid leaderboard entry; otherwise ignored

    This endpoint is also available as /api/submit-score for REST integration.
    """
    if not req.solved:
        return JSONResponse(status_code=400, content={"message": "Score is only recorded for solved games."})
    if not req.username or len(req.username.strip()) == 0:
        return JSONResponse(status_code=400, content={"message": "Username required for leaderboard entry."})
    leaderboard.save_completed_game(req.user_id, req.username.strip(), req.attempts, solved=True)
    return {"message": "Score submitted."}

# PUBLIC_INTERFACE
@app.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    tags=["leaderboard"],
    summary="Get the leaderboard"
)
@app.get(
    "/api/leaderboard",
    response_model=LeaderboardResponse,
    tags=["leaderboard", "api"],
    summary="[API alias] Retrieve leaderboard data (top users by fewest attempts)"
)
def get_leaderboard():
    """
    Returns current leaderboard: best (lowest attempts) first, ties by timestamp. Top 20 players.

    This endpoint is also available as /api/leaderboard for REST consumption.
    """
    entries = leaderboard.get_leaderboard(limit=20)
    return LeaderboardResponse(leaderboard=[
        LeaderboardEntry(**entry) for entry in entries
    ])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

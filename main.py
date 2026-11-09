import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

# 目前 client 是桌面程式，不受瀏覽器 CORS 限制。若日後改成網頁，
# 再把 allow_origins 限定為實際前端網址。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 記憶體儲存遊戲狀態
games_db: Dict[str, dict] = {}

# 【任務三】後端勝率統計全域變數
total_games = 0
total_wins = 0

# 【任務四】允許接收可選參數 hard_mode
class NewGameRequest(BaseModel):
    hard_mode: bool = False

class GuessRequest(BaseModel):
    game_id: str
    guess: str

def get_stats():
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0
    return {
        "total": total_games,
        "wins": total_wins,
        "win_rate": round(win_rate, 1)
    }

@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = NewGameRequest()):
    """ 建立新一局遊戲，回傳 game_id """
    global total_games
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    
    total_games += 1
    
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": req.hard_mode,
        "green_hints": [None] * 5,  # 記錄已確定的綠色字母
        "won_counted": False
    }
    return {
        "game_id": game_id, 
        "message": "New game started!",
        "stats": get_stats()
    }

@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 接收玩家猜測，比對答案並回傳顏色結果 """
    global total_wins
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 【任務二】字典庫驗證
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    game_session = games_db[game_id]
    target = game_session["target"]
    
    # 【任務四】Hard Mode 邏輯驗證
    if game_session["hard_mode"]:
        for i in range(5):
            hint = game_session["green_hints"][i]
            if hint is not None and guess[i] != hint:
                raise HTTPException(status_code=400, detail="Hard Mode: Must use revealed hint at green position")

    feedback = ["absent"] * 5  # 預設灰色 absent
    target_letter_counts = {}

    # 1. 先計算目標單字的各字母數量
    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 2. 標記綠色 correct
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            # 記錄綠色提示供下次 Hard Mode 檢查
            game_session["green_hints"][i] = guess[i]

    # 3. 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    game_session["attempts"] += 1
    is_correct = (guess == target)
    
    if is_correct and not game_session["won_counted"]:
        game_session["status"] = "WON"
        total_wins += 1
        game_session["won_counted"] = True

    is_game_over = is_correct or game_session["attempts"] >= 6

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        # 【任務一】猜對或猜滿6次結束時傳回目標單字
        "target_word": target if is_game_over else None,
        "stats": get_stats()
    }

# 【任務三】新增 API 回傳勝率數據
@app.get("/api/stats")
def get_game_stats():
    return get_stats()

if __name__ == "__main__":
    import uvicorn
    # Render 會透過 PORT 環境變數指定服務埠；本機則預設使用 8000。
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
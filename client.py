import sys
import os
import pygame
import requests

# 桌面 client 在本機執行，透過這個網址呼叫雲端 FastAPI server。
#API_BASE_URL = "https://wordle-server-a076.onrender.com"
API_BASE_URL = "http://127.0.0.1:8000"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
# 【任務三】擴充 Pygame 視窗寬度至 700
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, R to restart"
        
        # 新增屬性：Hard Mode、統計數據、歷史猜測
        self.hard_mode = False
        self.stats = {"total": 0, "wins": 0, "win_rate": 0.0}
        self.history = []
        
        self.start_new_game()

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局 """
        try:
            # 傳遞 hard_mode 參數
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                if "stats" in data:
                    self.stats = data["stats"]
                    
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history = []  # 重置歷史紀錄
                self.message = "New game started!"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                # 更新統計數據並將單字加入歷史面板
                if "stats" in data:
                    self.stats = data["stats"]
                self.history.append(guess_word)
                
                # 依據後端回傳更新格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        # 【任務一】失敗時顯示正確答案
                        target = data.get("target_word", "UNKNOWN")
                        self.message = f"Game Over! The word was {target}. Press R to restart."
                        self.game_over = True
                    else:
                        # 【任務一】每次猜測後顯示剩餘次數
                        self.message = f"Keep guessing! ({6 - self.row} tries left)"
                        
            elif res.status_code == 400:
                detail = res.json().get("detail", "Error")
                # 【任務二】前端攔截字典錯誤：修改訊息、不消耗次數
                if "dictionary" in detail.lower():
                    self.message = "Not in word list!"
                else:
                    # 攔截並顯示 Hard Mode 的錯誤提示
                    self.message = detail
            else:
                self.message = res.json().get("detail", "Error processing guess")
                
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
            # 1. 遊戲結束時：直接按 R 或 H 來重新開始或切換模式
            if self.game_over:
                if event.key == pygame.K_r:
                    self.start_new_game()
                elif event.key == pygame.K_h:
                    self.hard_mode = not self.hard_mode
                    self.start_new_game()
                return

            # 2. 遊戲進行中：若需要強制重新開始或切換模式，改為使用 Ctrl + R 或 Ctrl + H
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_r:
                    self.start_new_game()
                    return
                elif event.key == pygame.K_h:
                    self.hard_mode = not self.hard_mode
                    self.start_new_game()
                    return

            # 3. 正常打字邏輯（此時單按 R 或 H 都會被當作一般字母輸入）
            if event.key == pygame.K_BACKSPACE:
                if self.col > 0:
                    self.col -= 1
                    self.grid[self.row][self.col] = ""
            elif event.key == pygame.K_RETURN:
                self.submit_guess()
            elif event.unicode.isalpha() and len(event.unicode) == 1:
                if self.col < 5:
                    self.grid[self.row][self.col] = event.unicode.upper()
                    self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # 繪製 6x5 網格 (置於左側)
        margin_x, margin_y = 75, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                # 畫背景框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                # 畫字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 1. 畫固定操作提示 (放在主訊息上方，用稍暗的灰色字體以免太搶眼)
        hint_text = "Ctrl+R: Restart | Ctrl+H: Mode | Backspace: Delete"
        hint_surface = small_font.render(hint_text, True, (180, 180, 180))
        hint_rect = hint_surface.get_rect(center=(250, HEIGHT - 70))
        surface.blit(hint_surface, hint_rect)

        # 2. 畫遊戲狀態主訊息 (如 New game started! 等)
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(250, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)
        
        # ==========================================
        # 【任務三 & 任務四】繪製右側側邊欄歷史紀錄與狀態
        # ==========================================

        sidebar_x = 500
        # 1. 分隔線
        pygame.draw.line(surface, (100, 100, 100), (sidebar_x, 0), (sidebar_x, HEIGHT), 2)
        
        # 將文字稍微貼近線一點點
        text_margin_x = sidebar_x + 10 
        
        # 2. 勝率統計 (為了不超出寬度且符合座標規定，將其拆成兩行顯示)
        stats_text_1 = f"Total: {self.stats.get('total', 0)} | Wins: {self.stats.get('wins', 0)}"
        stats_text_2 = f"Win Rate: {self.stats.get('win_rate', 0.0)}%"
        
        surface.blit(small_font.render(stats_text_1, True, COLOR_TEXT), (text_margin_x, 20))
        surface.blit(small_font.render(stats_text_2, True, COLOR_TEXT), (text_margin_x, 45))
        
        # 3. 顯示目前模式 (配合文字拆行往下移動)
        mode_text = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_color = (255, 100, 100) if self.hard_mode else (150, 255, 150)
        mode_surf = small_font.render(mode_text, True, mode_color)
        surface.blit(mode_surf, (text_margin_x, 75))
        
        # 4. 歷史猜測單字清單 (配合往下移動)
        hist_title = small_font.render("Guess History:", True, (200, 200, 200))
        surface.blit(hist_title, (text_margin_x, 115))
        for idx, word in enumerate(self.history):
            word_surf = small_font.render(f"{idx + 1}. {word}", True, COLOR_TEXT)
            surface.blit(word_surf, (text_margin_x, 145 + idx * 30))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
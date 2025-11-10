# server.py
import socket
import threading
import json
import time
import queue
import tkinter as tk
from tkinter import scrolledtext
from pymongo import MongoClient # Cần 'pip install pymongo'
from sudoku import Sudoku # cần pip install sudoku

# Đặt lớp này sau phần import, BÊN NGOÀI lớp ServerGUI
# Đảm bảo bạn có 'import time' ở đầu file

class GameSession(threading.Thread):
    def __init__(self, server_instance, game_id, p1_conn, p1_name, p2_conn, p2_name, puzzle_board, solution_board, total_time=300):
        super().__init__(daemon=True)
        self.server = server_instance
        self.game_id = game_id
        self.solution = solution_board
        
        self.player1 = {
            "name": p1_name, 
            "conn": p1_conn, 
            "time": total_time, 
            "board": [row[:] for row in puzzle_board], # Board CỦA RIÊNG P1
            "finished": False,
            "finish_time_remaining": 0 # Thời gian còn lại khi hoàn thành
        }
        self.player2 = {
            "name": p2_name, 
            "conn": p2_conn, 
            "time": total_time, 
            "board": [row[:] for row in puzzle_board], # Board CỦA RIÊNG P2
            "finished": False,
            "finish_time_remaining": 0
        }
        
        # Đề bài gốc, không thay đổi
        self.puzzle_board = puzzle_board
        
        self.running = True
        self.lock = threading.Lock()
        self.log(f"GameSession {game_id} (RACE MODE) created between {p1_name} and {p2_name}.")

    def log(self, message):
        self.server.log(message)

    # Vòng lặp chính của timer
    def run(self):
        while self.running:
            time.sleep(1)
            
            with self.lock:
                if not self.running:
                    break
                
                # Trừ thời gian của P1 nếu chưa xong
                if not self.player1["finished"]:
                    self.player1["time"] -= 1
                
                # Trừ thời gian của P2 nếu chưa xong
                if not self.player2["finished"]:
                    self.player2["time"] -= 1

                # Gửi cập nhật timer
                self.broadcast_timer()
                
                # Kiểm tra P1 hết giờ
                if not self.player1["finished"] and self.player1["time"] <= 0:
                    self.player1["finished"] = True # Hết giờ = tính là xong (thua)
                    self.log(f"Game {self.game_id}: {self.player1['name']} timed out.")
                    self.server.send_to_client(self.player2["conn"], {"action": "opponent_finished", "name": self.player1['name']})

                # Kiểm tra P2 hết giờ
                if not self.player2["finished"] and self.player2["time"] <= 0:
                    self.player2["finished"] = True # Hết giờ = tính là xong (thua)
                    self.log(f"Game {self.game_id}: {self.player2['name']} timed out.")
                    self.server.send_to_client(self.player1["conn"], {"action": "opponent_finished", "name": self.player2['name']})

                # Nếu cả 2 đều đã xong (hoặc hết giờ) -> kết thúc game
                if self.player1["finished"] and self.player2["finished"]:
                    self.running = False
                    self.determine_winner()

    def broadcast_timer(self):
        # Tin nhắn cho P1
        msg1 = {"action": "timer_update", "my_time": self.player1["time"], "opponent_time": self.player2["time"]}
        self.server.send_to_client(self.player1["conn"], msg1)
        
        # Tin nhắn cho P2
        msg2 = {"action": "timer_update", "my_time": self.player2["time"], "opponent_time": self.player1["time"]}
        self.server.send_to_client(self.player2["conn"], msg2)

    def determine_winner(self):
        winner = "Draw" # Mặc định là hòa
        
        p1_time = self.player1["finish_time_remaining"]
        p2_time = self.player2["finish_time_remaining"]

        if p1_time > p2_time:
            winner = self.player1["name"]
        elif p2_time > p1_time:
            winner = self.player2["name"]
        elif p1_time == 0 and p2_time == 0:
             winner = "Draw (Timeout)"

        self.log(f"Game {self.game_id} finished. P1 Time: {p1_time}, P2 Time: {p2_time}. Winner: {winner}")
        self.server.end_game(self.game_id, winner)

    # Xử lý khi có client gửi nước đi
    def handle_move(self, player_name, move_data):
        with self.lock:
            # Xác định player và đối thủ
            if player_name == self.player1["name"]:
                player = self.player1
                opponent = self.player2
            else:
                player = self.player2
                opponent = self.player1
            
            # Nếu đã xong rồi thì không nhận nước đi nữa
            if player["finished"]:
                return

            try:
                cell = move_data.get("cell") # [row, col]
                value = int(move_data.get("value")) # num
                row, col = cell
                if not (0 <= row <= 8 and 0 <= col <= 8 and 1 <= value <= 9):
                    raise ValueError("Invalid coordinates or value")
            except Exception as e:
                self.log(f"Game {self.game_id}: Invalid move data: {e}")
                return

            # Kiểm tra ô gốc
            if self.puzzle_board[row][col] is not None:
                return
            
            # Kiểm tra luật Sudoku
            if not self.is_valid_move(player["board"], row, col, value):
                # (Tùy chọn: bạn có thể gửi tin nhắn lỗi về client)
                # Hoặc chỉ đơn giản là bỏ qua nước đi sai
                self.log(f"Game {self.game_id}: {player_name} made an invalid move.")
                # Tạm thời chúng ta cho phép đi sai để người chơi tự sửa
                # return # Bỏ comment nếu muốn CHẶN nước đi sai
            
            # Cập nhật BẢNG CỜ RIÊNG của người chơi
            player["board"][row][col] = value

            # CHÚNG TA KHÔNG CHUYỂN TIẾP NƯỚC ĐI CHO ĐỐI THỦ
            # (self.server.send_to_client(opponent_conn, fwd_msg) -> BỊ XÓA)

            # Kiểm tra thắng
            if self.is_board_full(player["board"]):
                if player["board"] == self.solution:
                    # THẮNG
                    player["finished"] = True
                    player["finish_time_remaining"] = player["time"] # Lưu lại thời gian còn lại
                    self.log(f"Game {self.game_id}: {player_name} has solved the puzzle!")
                    
                    # Gửi thông báo cho chính người chơi
                    self.server.send_to_client(player["conn"], {"action": "game_finish", "status": "completed", "time": player["time"]})
                    # Gửi thông báo cho đối thủ
                    self.server.send_to_client(opponent["conn"], {"action": "opponent_finished", "name": player["name"]})

                else:
                    # Bàn cờ đầy nhưng sai -> Gửi lỗi (Tùy chọn)
                    self.log(f"Game {self.game_id}: {player_name} filled board incorrectly.")
                    # (Gửi tin nhắn {"action": "error", "message": "Board incorrect"})

            # Kiểm tra xem cả 2 đã xong chưa (để kết thúc game sớm)
            if self.player1["finished"] and self.player2["finished"]:
                if self.running: # Đảm bảo chỉ gọi 1 lần
                    self.running = False
                    self.determine_winner()

    # (Các hàm is_valid_move và is_board_full giữ nguyên như cũ)
    # Hàm helper kiểm tra xem nước đi có hợp lệ không
    def is_valid_move(self, board, row, col, num):
        # 1. Kiểm tra hàng
        for c in range(9):
            if board[row][c] == num and c != col:
                return False
        # 2. Kiểm tra cột
        for r in range(9):
            if board[r][col] == num and r != row:
                return False
        # 3. Kiểm tra ô 3x3
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for r in range(start_row, start_row + 3):
            for c in range(start_col, start_col + 3):
                if board[r][c] == num and (r, c) != (row, col):
                    return False
        return True

    # Hàm helper kiểm tra xem bàn cờ đã đầy chưa
    def is_board_full(self, board):
        for r in range(9):
            for c in range(9):
                if board[r][c] is None:
                    return False
        return True

class ServerGUI:
    def __init__(self, host='127.0.0.1', port=65432):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # Danh sách client: {username: conn_socket}
        self.clients = {} 
        # Danh sách game đang chạy: {game_id: GameSession}
        self.active_games = {} 

        self.log_queue = queue.Queue()
        # Kết nối MongoDB
        try:
            self.mongo_client = MongoClient("mongodb://localhost:27017/")
            self.db = self.mongo_client["sudoku_game"]
            self.history_collection = self.db["match_history"]
            print("Connected to MongoDB.")
        except Exception as e:
            print(f"Could not connect to MongoDB: {e}")
            # Có thể thoát hoặc chạy mà không có DB

        # Setup GUI
        self.window = tk.Tk()
        self.window.title("Sudoku Server")

        self.btn_start = tk.Button(self.window, text="Start Server", command=self.start_server)
        self.btn_start.pack()

        self.btn_stop = tk.Button(self.window, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop.pack()

        self.log_area = scrolledtext.ScrolledText(self.window, state=tk.DISABLED)
        self.log_area.pack(padx=10, pady=10)

        # Quản lý client (ví dụ: Listbox)
        self.client_list_label = tk.Label(self.window, text="Connected Clients:")
        self.client_list_label.pack()
        self.client_listbox = tk.Listbox(self.window)
        self.client_listbox.pack(fill=tk.BOTH, expand=True)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.poll_log_queue()
        self.window.mainloop()

    def log(self, message):
        print(message) # Giữ lại để debug trên console
        self.log_queue.put(message) # Đưa tin nhắn vào queue
    
    # THÊM HÀM MỚI NÀY (bên trong lớp ServerGUI)
    def poll_log_queue(self):
        try:
            # Lấy tất cả tin nhắn đang chờ trong queue
            while True:
                message = self.log_queue.get_nowait()
                
                # Cập nhật GUI một cách an toàn
                self.log_area.config(state=tk.NORMAL)
                self.log_area.insert(tk.END, message + "\n")
                self.log_area.see(tk.END)
                self.log_area.config(state=tk.DISABLED)
                
        except queue.Empty:
            pass # Hết tin nhắn, không làm gì cả
        finally:
            # Lên lịch để tự gọi lại chính nó sau 100ms
            self.window.after(100, self.poll_log_queue)

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running = True

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log(f"Server started on {self.host}:{self.port}")

        # Tạo 1 luồng riêng để chấp nhận kết nối mới
        self.accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
        self.accept_thread.start()

    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Đóng tất cả kết nối client
        for conn in self.clients.values():
            conn.close()

        self.clients.clear()
        self.active_games.clear()
        
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log("Server stopped.")

    def on_closing(self):
        self.stop_server()
        self.window.destroy()

    def accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                if not self.running:
                    break
                self.log(f"New connection from {addr}")
                # Tạo 1 luồng riêng để xử lý client này
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
            except OSError:
                break # Socket đã đóng

    def handle_client(self, conn, addr):
        username = None
        try:
            while self.running:
                data = conn.recv(1024)
                if not data:
                    break # Client ngắt kết nối
                
                message = json.loads(data.decode('utf-8'))
                self.log(f"Received from {addr}: {message}")

                action = message.get("action")

                if action == "connect":
                    username = message.get("username")
                    if username in self.clients:
                        # Gửi lỗi: Tên đã tồn tại
                        pass 
                    else:
                        self.clients[username] = conn
                        self.update_client_listbox()
                        self.broadcast_user_list()

                elif action == "challenge":
                    opponent_name = message.get("opponent")
                    opponent_conn = self.clients.get(opponent_name)
                    if opponent_conn:
                        # Gửi lời mời thách đấu cho đối thủ
                        fwd_msg = {"action": "challenge_request", "from": username}
                        self.send_to_client(opponent_conn, fwd_msg)
                    
                # ... bên trong hàm handle_client ...
                
                elif action == "challenge_response":
                    opponent_name = message.get("opponent")
                    opponent_conn = self.clients.get(opponent_name)
                    accept = message.get("accept")

                    if accept and opponent_conn:
                        game_id = f"game_{username}_{opponent_name}"
                        
                        try:
                            # 1. Tạo puzzle
                            puzzle_object = Sudoku(3, 3).difficulty(0.5) 
                            # 2. Giải nó để có lời giải
                            solution_object = puzzle_object.solve()
                        
                        except Exception as e:
                            self.log(f"Failed to generate/solve Sudoku puzzle: {e}")
                            continue

                        # 3. Lấy ma trận đề bài (để gửi client)
                        puzzle_data = puzzle_object.board 
                        # 4. Lấy ma trận lời giải (để gửi GameSession)
                        solution_data = solution_object.board
                        
                        self.log(f"Generated puzzle and solution for game {game_id}")

                        # Gửi thông báo bắt đầu game cho cả 2 (chỉ gửi đề bài)
                        msg1 = {"action": "game_start", "game_id": game_id, "opponent": opponent_name, "puzzle": puzzle_data}
                        msg2 = {"action": "game_start", "game_id": game_id, "opponent": username, "puzzle": puzzle_data}
                        
                        self.send_to_client(conn, msg1)
                        self.send_to_client(opponent_conn, msg2)

                        # 5. Khởi tạo GameSession (RACE MODE) với 2 ma trận
                        game_session = GameSession(
                            server_instance=self, 
                            game_id=game_id,
                            p1_conn=conn, 
                            p1_name=username,
                            p2_conn=opponent_conn,
                            p2_name=opponent_name,
                            puzzle_board=puzzle_data,     # <--- Dùng cái này
                            solution_board=solution_data  # <--- Dùng cái này
                        )
                        
                        self.active_games[game_id] = game_session
                        game_session.start()

                # ... bên trong hàm handle_client ...

                elif action == "move":
                    game_id = message.get("game_id")
                    game = self.active_games.get(game_id)
                    
                    if game:
                        game.handle_move(username, message) # Chuyển cho GameSession xử lý
                    else:
                        self.log(f"Received move for non-existent game {game_id}")

                elif action == "chat":
                    game_id = message.get("game_id")
                    game = self.active_games.get(game_id)
                    
                    if game:
                        # GameSession không quản lý chat, server tự chuyển tiếp
                        opponent_conn = game.player2["conn"] if username == game.player1["name"] else game.player1["conn"]
                        fwd_msg = {"action": "chat_message", "from": username, "message": message.get("message")}
                        self.send_to_client(opponent_conn, fwd_msg)

        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
        # ... bên trong hàm handle_client ...
        finally:
            if username and username in self.clients:
                del self.clients[username]
                self.update_client_listbox()
                self.broadcast_user_list()
                
                # [LOGIC: Dọn dẹp game nếu client thoát]
                game_to_remove = None
                for game_id, game in self.active_games.items():
                    if game.player1["name"] == username or game.player2["name"] == username:
                        opponent_name = game.player2["name"] if game.player1["name"] == username else game.player1["name"]
                        self.end_game(game_id, winner=opponent_name) # Đối thủ thắng
                        break

            conn.close()
            self.log(f"Connection from {addr} (User: {username}) closed.")

    # Thêm hàm này vào BÊN TRONG lớp ServerGUI
    def end_game(self, game_id, winner):
        self.log(f"Ending game {game_id}. Winner: {winner}")
        
        # Lấy game ra khỏi danh sách active
        game = self.active_games.pop(game_id, None)
        
        if game:
            # Dừng luồng timer của game đó
            game.stop()
            
            # Chuẩn bị dữ liệu để lưu vào MongoDB
            game_data = {
                "game_id": game_id,
                "player1": game.player1["name"],
                "player2": game.player2["name"],
                "winner": winner,
                "end_time": time.time(),
                "duration": (game.player1["time"] + game.player2["time"]) # Cần tính toán lại logic này, ví dụ: (TotalTime * 2) - (p1.time + p2.time)
            }
            # Lưu vào DB
            self.save_match_to_db(game_data)
            
            # Thông báo cho 2 người chơi là game đã kết thúc
            msg = {"action": "game_over", "winner": winner}
            self.send_to_client(game.player1["conn"], msg)
            self.send_to_client(game.player2["conn"], msg)

    def send_to_client(self, conn, message):
        try:
            conn.sendall(json.dumps(message).encode('utf-8'))
        except Exception as e:
            self.log(f"Failed to send message: {e}")

    def broadcast_user_list(self):
        user_list = list(self.clients.keys())
        message = {"action": "user_list", "users": user_list}
        for conn in self.clients.values():
            self.send_to_client(conn, message)

    def update_client_listbox(self):
        self.client_listbox.delete(0, tk.END)
        for user in self.clients.keys():
            self.client_listbox.insert(tk.END, user)
            
    def save_match_to_db(self, game_data):
        # Hàm này sẽ được gọi khi game kết thúc
        try:
            self.history_collection.insert_one(game_data)
            self.log("Match history saved to MongoDB.")
        except Exception as e:
            self.log(f"Failed to save match history: {e}")


if __name__ == "__main__":
    ServerGUI()
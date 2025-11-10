# server.py
import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext
from pymongo import MongoClient # Cần 'pip install pymongo'

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
        self.window.mainloop()

    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)
        print(message)

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
                    
                elif action == "challenge_response":
                    opponent_name = message.get("opponent")
                    opponent_conn = self.clients.get(opponent_name)
                    accept = message.get("accept")

                    if accept and opponent_conn:
                        # Tạo game mới
                        game_id = f"game_{username}_{opponent_name}"
                        # [LOGIC: Tạo bàn cờ Sudoku ở đây]
                        puzzle = "..." # Một chuỗi/list đại diện bàn cờ

                        # Gửi thông báo bắt đầu game cho cả 2
                        msg1 = {"action": "game_start", "game_id": game_id, "opponent": opponent_name, "puzzle": puzzle}
                        msg2 = {"action": "game_start", "game_id": game_id, "opponent": username, "puzzle": puzzle}
                        
                        self.send_to_client(conn, msg1)
                        self.send_to_client(opponent_conn, msg2)

                        # [LOGIC: Khởi tạo GameSession và bộ đếm timer]
                        # self.active_games[game_id] = ...

                elif action == "move":
                    # [LOGIC: Xác thực nước đi, chuyển tiếp cho đối thủ, quản lý timer]
                    pass
                
                elif action == "chat":
                    # [LOGIC: Chuyển tiếp tin nhắn chat cho đối thủ]
                    pass

        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
        finally:
            if username and username in self.clients:
                del self.clients[username]
                self.update_client_listbox()
                self.broadcast_user_list()
            conn.close()
            self.log(f"Connection from {addr} (User: {username}) closed.")

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
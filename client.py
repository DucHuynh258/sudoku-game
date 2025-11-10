# client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

class ClientGUI:
    def __init__(self, host='127.0.0.1', port=65432):
        self.host = host
        self.port = port
        self.sock = None
        self.username = None
        self.connected = False
        self.listen_thread = None
        self.current_game_id = None
        self.opponent = None

        # Setup GUI
        self.window = tk.Tk()
        self.window.title("Sudoku Client")

        # Frame kết nối
        connect_frame = tk.Frame(self.window)
        self.entry_ip = tk.Entry(connect_frame)
        self.entry_ip.insert(0, self.host)
        self.entry_ip.pack(side=tk.LEFT)
        self.entry_port = tk.Entry(connect_frame)
        self.entry_port.insert(0, str(self.port))
        self.entry_port.pack(side=tk.LEFT)
        self.btn_connect = tk.Button(connect_frame, text="Connect", command=self.connect_to_server)
        self.btn_connect.pack(side=tk.LEFT)
        self.btn_disconnect = tk.Button(connect_frame, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT)
        connect_frame.pack(pady=5)

        # Frame danh sách người dùng và thách đấu
        user_frame = tk.Frame(self.window)
        self.user_listbox = tk.Listbox(user_frame)
        self.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.btn_challenge = tk.Button(user_frame, text="Challenge", command=self.challenge_player, state=tk.DISABLED)
        self.btn_challenge.pack(side=tk.RIGHT)
        user_frame.pack(pady=5, fill=tk.X)

        # [KHUNG SUDOKU 9x9 SẼ Ở ĐÂY]
        # (Đây là phần phức tạp nhất, bạn cần tự implement logic 
        #  dùng Canvas hoặc Frame/Entry)
        self.game_frame = tk.Frame(self.window, relief="sunken", borderwidth=2, height=300, width=300)
        tk.Label(self.game_frame, text="Sudoku Grid 9x9").pack()
        self.game_frame.pack(pady=10)

        # [KHUNG CHAT VÀ TIMER]
        self.chat_area = scrolledtext.ScrolledText(self.window, height=8, state=tk.DISABLED)
        self.chat_area.pack(pady=5, fill=tk.X)
        self.chat_entry = tk.Entry(self.window)
        self.chat_entry.pack(fill=tk.X)
        self.btn_send_chat = tk.Button(self.window, text="Send", command=self.send_chat)
        self.btn_send_chat.pack()
        
        self.timer_label = tk.Label(self.window, text="My Time: 0:00 | Opponent: 0:00")
        self.timer_label.pack()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def connect_to_server(self):
        self.username = simpledialog.askstring("Username", "Enter your username:")
        if not self.username:
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.entry_ip.get(), int(self.entry_port.get())))
            self.connected = True
            
            # Gửi thông điệp connect
            msg = {"action": "connect", "username": self.username}
            self.send_message(msg)

            # Bắt đầu luồng lắng nghe server
            self.listen_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.listen_thread.start()

            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            self.btn_challenge.config(state=tk.NORMAL)
            self.show_chat(f"Connected as {self.username}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")

    def disconnect(self):
        if self.sock:
            self.sock.close()
        self.connected = False
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.btn_challenge.config(state=tk.DISABLED)
        self.user_listbox.delete(0, tk.END)
        self.show_chat("Disconnected.")

    def on_closing(self):
        self.disconnect()
        self.window.destroy()

    def send_message(self, message):
        if self.connected and self.sock:
            try:
                self.sock.sendall(json.dumps(message).encode('utf-8'))
            except Exception as e:
                self.show_chat(f"Error sending message: {e}")
                self.disconnect()

    def listen_to_server(self):
        while self.connected:
            try:
                data = self.sock.recv(1024)
                if not data:
                    self.disconnect()
                    break
                
                message = json.loads(data.decode('utf-8'))
                self.handle_server_message(message)

            except Exception as e:
                if self.connected:
                    self.show_chat(f"Connection lost: {e}")
                break
        
        # Đảm bảo GUI được cập nhật về trạng thái disconnect
        self.window.after(0, self.disconnect)

    def handle_server_message(self, message):
        action = message.get("action")

        if action == "user_list":
            users = message.get("users", [])
            self.user_listbox.delete(0, tk.END)
            for user in users:
                if user != self.username:
                    self.user_listbox.insert(tk.END, user)
        
        elif action == "challenge_request":
            challenger = message.get("from")
            response = messagebox.askyesno("Challenge", f"{challenger} challenges you! Accept?")
            
            resp_msg = {
                "action": "challenge_response",
                "opponent": challenger,
                "accept": response
            }
            self.send_message(resp_msg)

        elif action == "game_start":
            self.current_game_id = message.get("game_id")
            self.opponent = message.get("opponent")
            puzzle = message.get("puzzle")
            self.show_chat(f"Game started with {self.opponent} (ID: {self.current_game_id})")
            # [LOGIC: Vẽ bàn cờ Sudoku (puzzle) lên game_frame]

        elif action == "opponent_move":
            cell = message.get("cell")
            value = message.get("value")
            # [LOGIC: Cập nhật nước đi của đối thủ lên bàn cờ]
            self.show_chat(f"Opponent played {value} at {cell}")

        elif action == "chat_message":
            self.show_chat(f"[{message.get('from')}]: {message.get('message')}")
        
        elif action == "timer_update":
            # [LOGIC: Cập nhật self.timer_label]
            pass

        elif action == "game_over":
            winner = message.get("winner")
            messagebox.showinfo("Game Over", f"Winner: {winner}")
            self.current_game_id = None
            self.opponent = None
            
    def challenge_player(self):
        selected_indices = self.user_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Challenge", "Select a user to challenge.")
            return
        
        opponent_name = self.user_listbox.get(selected_indices[0])
        msg = {"action": "challenge", "opponent": opponent_name}
        self.send_message(msg)
        self.show_chat(f"Sent challenge to {opponent_name}")

    def send_chat(self):
        message_text = self.chat_entry.get()
        if message_text and self.current_game_id:
            msg = {
                "action": "chat",
                "game_id": self.current_game_id,
                "message": message_text
            }
            self.send_message(msg)
            self.show_chat(f"[Me]: {message_text}")
            self.chat_entry.delete(0, tk.END)
        elif not self.current_game_id:
            self.show_chat("You must be in a game to chat.")

    def show_chat(self, message):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

if __name__ == "__main__":
    ClientGUI()
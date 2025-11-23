import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext


# =====================================================
# LỚP GIAO DIỆN SUDOKU 
# =====================================================
class SudokuUI:
    def __init__(self, window, client):
        self.window = window
        self.client = client
        self.cells = [[None for _ in range(9)] for _ in range(9)]
        self.cell_name_to_coord = {}
        self.build_ui()

    def build_ui(self):
        # ===============================================
        # DÙNG PANEDWINDOW 
        # ===============================================
        
        main_pane = tk.PanedWindow(
            self.window, 
            orient=tk.HORIZONTAL, 
            bg="#f4ede4", 
            sashrelief=tk.RIDGE, 
            sashwidth=5
        )
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # 2. Frame bên trái (Game)
        left_frame = tk.Frame(main_pane, bg="#f4ede4")
        main_pane.add(left_frame, minsize=550) 

        # 3. Frame bên phải (User List + Chat)
        right_panel = tk.Frame(main_pane, bg="#f4ede4")
        main_pane.add(right_panel, minsize=300)

        # ===============================================
        # WIDGETS TRONG left_frame (GAME)
        # ===============================================

        title = tk.Label(
            left_frame, 
            text="Sudoku Multiplayer",
            font=("Arial", 24, "bold"), bg="#f4ede4", fg="#5a3825"
        )
        title.pack(pady=(10, 5))

        self.game_frame = tk.Frame(left_frame, bg="#8B5A2B", bd=8, relief="ridge")
        self.game_frame.pack(pady=10)

        vcmd = (self.window.register(self.validate_entry), '%P', '%W')

        for big_r in range(3):
            for big_c in range(3):
                block = tk.Frame(
                    self.game_frame, bg="#b97a57", bd=3, relief="ridge"
                )
                block.grid(row=big_r, column=big_c, padx=2, pady=2)
                for r in range(3):
                    for c in range(3):
                        gr, gc = big_r * 3 + r, big_c * 3 + c
                        cell = tk.Entry(
                            block, width=2, font=('Arial', 22, 'bold'),
                            justify='center', bg="#f8e9d2", relief="flat",
                            disabledforeground="black", validate="key",
                            validatecommand=vcmd, highlightthickness=1,
                            highlightbackground="#d2b48c",
                            highlightcolor="#c0392b"
                        )
                        cell.grid(row=r, column=c, padx=2, pady=2, ipadx=2, ipady=2)
                        cell.bind("<Key>", self.handle_keypress)
                        self.cells[gr][gc] = cell
                        self.cell_name_to_coord[str(cell)] = (gr, gc)

        button_frame = tk.Frame(left_frame, bg="#f4ede4") 
        button_frame.pack(pady=(0, 10)) 

        self.client.btn_submit = tk.Button(
            button_frame, 
            text="Hoàn thành", 
            bg="#28a745", 
            fg="white",
            font=("Arial", 12, "bold"), 
            command=self.client.submit_solution, 
            state=tk.DISABLED,
            width=15
        )
        self.client.btn_submit.pack()

        self.timer_label = tk.Label(
            left_frame, 
            text="My Time: 0:00 | Opponent: 0:00",
            font=("Arial", 12), bg="#f4ede4", fg="#5a3825"
        )
        self.timer_label.pack(pady=5)


        # ===============================================
        # WIDGETS TRONG right_panel (USER LIST + CHAT)
        # ===============================================

        # --- 1. KHUNG USER LIST (Ở trên) ---
        user_frame = tk.Frame(right_panel, bg="#f4ede4")
        user_frame.pack(side=tk.TOP, fill=tk.X, pady=(5, 0), padx=5)

        self.client.user_listbox = tk.Listbox(user_frame, height=5)
        self.client.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.client.btn_challenge = tk.Button(user_frame, text="Thách đấu", bg="#b97a57", fg="white",
                                             command=self.client.challenge_player, state=tk.DISABLED)
        self.client.btn_challenge.pack(side=tk.RIGHT, padx=5)
        
        self.client.btn_history = tk.Button(user_frame, text="Lịch sử", bg="#6c757d", fg="white",
                                           command=self.client.request_history, state=tk.DISABLED)
        self.client.btn_history.pack(side=tk.RIGHT, padx=5)

        # --- 2. KHUNG CHAT (Ở dưới) ---
        chat_container = tk.Frame(right_panel, bg="#f4ede4")
        chat_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=(5,0))
        
        chat_label = tk.Label(
            chat_container, 
            text="Chat", 
            font=("Arial", 14, "bold"), bg="#f4ede4", fg="#5a3825"
        )
        # 1. Pack Label lên TOP
        chat_label.pack(side=tk.TOP, pady=(5, 0)) 
        
        
        # 🌟🌟🌟 START SỬA CODE TẠI ĐÂY (Thêm nút Gửi) 🌟🌟🌟
        
        # --- FRAME BAO Ô NHẬP CHAT (Bao gồm Entry và Button) ---
        entry_container = tk.Frame(chat_container, bg="#f4ede4")
        entry_container.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 12), padx=15)

        # --- Ô NHẬP CHAT ---
        self.chat_entry = tk.Entry(
            entry_container,
            font=('Arial', 12),
            bg="#f8e9d2",
            relief="solid",
            borderwidth=2,
        )
        # Đặt Entry sang bên trái, cho phép giãn nở để chiếm không gian
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=25, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.client.send_chat())

        # --- NÚT GỬI ---
        btn_send = tk.Button(
            entry_container,
            text="Gửi",
            font=("Arial", 12, "bold"),
            bg="#9C8057", 
            fg="white",
            command=self.client.send_chat, # Gọi hàm gửi chat
            width=5,
            height=2 # Chiều cao tương đối với ipady=8 của Entry
        )
        btn_send.pack(side=tk.RIGHT)

        # TẠO VÀ PACK Ô HIỂN THỊ CHAT VÀO GIỮA SAU
        self.chat_area = scrolledtext.ScrolledText(
            chat_container, 
            state=tk.DISABLED,
            bg="#fff9f4", fg="#2c2c2c", wrap="word", relief="solid"
        )
        # 3. Pack ô chat vào phần CÒN LẠI (ở giữa)
        # Nó sẽ fill vào không gian giữa label và entry_container
        self.chat_area.pack(side=tk.TOP, pady=5, fill=tk.BOTH, expand=True) 
        # 🌟🌟🌟 KẾT THÚC SỬA CODE TẠI ĐÂY 🌟🌟🌟
        
    def handle_keypress(self, event):
        """Xử lý di chuyển mũi tên và tự động xóa số cũ khi nhập số mới"""
        widget = event.widget
        
        # 1. XỬ LÝ DI CHUYỂN (Mũi tên)
        if event.keysym in ('Up', 'Down', 'Left', 'Right'):
            try:
                r, c = self.cell_name_to_coord[str(widget)]
                
                if event.keysym == 'Up':
                    r = (r - 1) % 9 
                elif event.keysym == 'Down':
                    r = (r + 1) % 9
                elif event.keysym == 'Left':
                    c = (c - 1) % 9
                elif event.keysym == 'Right':
                    c = (c + 1) % 9
                
                target_cell = self.cells[r][c]
                target_cell.focus_set()
                target_cell.icursor(tk.END)
                
                return "break" 
            except KeyError:
                pass

        # 2. XỬ LÝ GHI ĐÈ (Nhập số)
        if event.char in "123456789" and widget.cget('state') == 'normal':
            widget.delete(0, tk.END)

    def check_board_full(self):
        """Kiểm tra xem tất cả ô có thể điền đã được điền chưa"""
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                if cell.cget('state') != 'readonly' and not cell.get():
                    return False 
        return True 

    def delayed_check_full(self):
        """
        Kiểm tra sau 1ms để đảm bảo tkinter đã cập nhật giá trị.
        Hàm này sẽ Bật hoặc Tắt nút 'Hoàn thành'
        """
        if self.client.btn_submit:
            if self.check_board_full():
                self.client.btn_submit.config(state=tk.NORMAL)
            else:
                self.client.btn_submit.config(state=tk.DISABLED)

    # ------------------- Sudoku logic -------------------
    def validate_entry(self, value, widget_name):
        """Chỉ cho phép nhập số 1-9"""
        self.window.after(1, self.delayed_check_full)

        if not (value == "" or (len(value) == 1 and value in "123456789")):
            return False

        if not self.client.current_game_id:
            return True

        try:
            r, c = self.cell_name_to_coord[widget_name]
        except KeyError:
            return True 

        if value == "":
            try:
                self.client.send_move(r, c, 0)
            except KeyError:
                pass 
            return True
        
        try:
            r, c = self.cell_name_to_coord[widget_name]
            self.client.send_move(r, c, int(value))
            self.cells[r][c].config(fg="#555555")
        except KeyError:
            pass 

        return True

    def display_puzzle(self, puzzle):
        """Hiển thị đề bài Sudoku"""
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                cell.config(state="normal")
                cell.delete(0, tk.END)
                cell.config(bg="#f8e9d2", disabledbackground="#f8e9d2", readonlybackground="#f8e9d2")
                num = puzzle[r][c]
                if num:
                    cell.insert(0, str(num))
                    cell.config(state="readonly", fg="blue", readonlybackground="#f8e9d2")
                else:
                    cell.config(state="normal", fg="black")

    def update_cell(self, cell, value):
        """Cập nhật nước đi đối thủ"""
        try:
            r, c = cell
            widget = self.cells[r][c]
            # Chỉ cập nhật ô nếu nó không phải là ô cố định
            # Logic này đã đúng, chỉ cần đảm bảo nó không thay đổi ô cố định của mình
            if widget.cget('state') != 'readonly' and widget.get() not in "123456789":
                widget.config(state="normal")
                widget.delete(0, tk.END)
                if value != 0:
                     widget.insert(0, str(value))
                     widget.config(state="readonly", fg="red", readonlybackground=widget.cget('bg'))
                else:
                    # Nếu giá trị là 0, tức là xóa
                    widget.config(state="normal", fg="black")
                    
        except Exception as e:
            self.add_chat_message(f"Lỗi cập nhật ô: {e}")

    def disable_all(self):
        for r in range(9):
            for c in range(9):
                self.cells[r][c].config(state=tk.DISABLED)

    def highlight_errors(self, error_list):
        """Nhận 1 list tọa độ [[r, c], ...] và tô màu các ô đó"""
        error_color = "#FC665C" 
        
        self.log(f"Highlighting {len(error_list)} errors.") 
        
        for coord in error_list:
            try:
                r, c = coord
                cell_widget = self.cells[r][c]
                
                cell_widget.config(
                    bg=error_color, 
                    disabledbackground=error_color, 
                    readonlybackground=error_color
                )
            except Exception as e:
                self.log(f"Error highlighting cell {coord}: {e}") 

    def log(self, message):
        self.add_chat_message(f"[Debug]: {message}")

    # ------------------- Chat -------------------
    def add_chat_message(self, msg):
        if hasattr(self, 'chat_area'):
            self.chat_area.config(state=tk.NORMAL)
            self.chat_area.insert(tk.END, msg + "\n")
            self.chat_area.see(tk.END)
            self.chat_area.config(state=tk.DISABLED)


# =====================================================
# LỚP CLIENT
# =====================================================
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
        self.buffer = ""
        self.challenge_pending = False

        self.window = tk.Tk()
        self.window.title("Sudoku Multiplayer") 
        self.window.geometry("900x700") 
        self.window.configure(bg="#f4ede4")

        self.user_listbox = None
        self.btn_challenge = None
        self.btn_history = None
        self.btn_submit = None

        connect_frame = tk.Frame(self.window, bg="#f4ede4")
        tk.Label(connect_frame, text="IP:", bg="#f4ede4").pack(side=tk.LEFT)
        self.entry_ip = tk.Entry(connect_frame, width=12)
        self.entry_ip.insert(0, self.host)
        self.entry_ip.pack(side=tk.LEFT, padx=2)
        tk.Label(connect_frame, text="Port:", bg="#f4ede4").pack(side=tk.LEFT)
        self.entry_port = tk.Entry(connect_frame, width=6)
        self.entry_port.insert(0, str(self.port))
        self.entry_port.pack(side=tk.LEFT, padx=2)
        self.btn_connect = tk.Button(connect_frame, text="Kết nối", bg="#8B5A2B", fg="white",
                                     command=self.connect_to_server)
        self.btn_connect.pack(side=tk.LEFT, padx=3)
        self.btn_disconnect = tk.Button(connect_frame, text="Ngắt", bg="#b97a57", fg="white",
                                        command=self.disconnect, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT)
        connect_frame.pack(side=tk.TOP, pady=5, fill=tk.X, padx=10)

        self.ui = SudokuUI(self.window, self)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    # ------------------- Socket Logic -------------------
    def connect_to_server(self):
        self.username = simpledialog.askstring("Username", "Nhập tên người chơi:")
        if not self.username:
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.entry_ip.get(), int(self.entry_port.get())))
            self.connected = True
            msg = {"action": "connect", "username": self.username}
            self.send_message(msg)
            self.listen_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.listen_thread.start()
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            
            if self.btn_challenge:
                self.btn_challenge.config(state=tk.NORMAL)
            if self.btn_history:
                self.btn_history.config(state=tk.NORMAL)

            self.ui.add_chat_message(f" Kết nối thành công với tên: {self.username}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối: {e}")

    def disconnect(self):
        if not self.connected: 
            return 
        
        self.connected = False 

        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        
        if self.btn_challenge:
            self.btn_challenge.config(state=tk.DISABLED)
        if self.btn_history:
            self.btn_history.config(state=tk.DISABLED)
        if self.user_listbox:
            self.user_listbox.delete(0, tk.END)
            
        self.current_game_id = None 
        self.challenge_pending = False
        self.opponent = None
        self.ui.add_chat_message("🔌 Đã ngắt kết nối.")

    def send_message(self, message):
        if self.connected and self.sock:
            try:
                self.sock.sendall(json.dumps(message).encode('utf-8'))
            except Exception as e:
                self.ui.add_chat_message(f"Lỗi gửi dữ liệu: {e}")
                self.disconnect()

    def listen_to_server(self):
        decoder = json.JSONDecoder()
        
        while self.connected:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break 
                
                self.buffer += data
                
                while self.buffer:
                    try:
                        msg, idx = decoder.raw_decode(self.buffer)
                        self.window.after(0, self.handle_server_message, msg)
                        self.buffer = self.buffer[idx:].lstrip()
                        
                    except json.JSONDecodeError:
                        break
            
            except Exception as e:
                if self.connected: 
                    self.ui.add_chat_message(f"Lỗi kết nối: {e}")
                break
                
        self.disconnect()

    def handle_server_message(self, message):
        action = message.get("action")
        
        if action == "user_list" and self.user_listbox:
            self.user_listbox.delete(0, tk.END)
            for u in message.get("users", []):
                if u != self.username:
                    self.user_listbox.insert(tk.END, u)

        elif action == "challenge_request":
            challenger = message.get("from")
            # Nếu mình đang chơi game mà vẫn nhận được request (do lỗi nào đó), tự động từ chối
            if self.current_game_id:
                self.send_message({"action": "challenge_response", "opponent": challenger, "accept": False})
                return
            accept = messagebox.askyesno("Thách đấu", f"{challenger} thách đấu bạn! Chấp nhận?")
            resp = {"action": "challenge_response", "opponent": challenger, "accept": accept}
            self.send_message(resp)
            if accept and self.btn_challenge:
                self.btn_challenge.config(state=tk.DISABLED)
                self.challenge_pending = False

        elif action == "game_start":
            self.current_game_id = message.get("game_id")
            self.opponent = message.get("opponent")
            puzzle = message.get("puzzle")
            self.ui.display_puzzle(puzzle)
            self.ui.add_chat_message(f" Game bắt đầu với {self.opponent}")
            if self.btn_challenge:
                self.btn_challenge.config(state=tk.DISABLED)
            self.challenge_pending = False

        elif action == "move":
            cell = message.get("cell")
            val = message.get("value")
            self.ui.update_cell(cell, val)

        elif action == "chat_message":
            self.ui.add_chat_message(f"[{message.get('from')}]: {message.get('message')}")

        elif action == "history_data":
            data = message.get("data", [])
            self.show_history_popup(data)

        elif action == "timer_update":
            my_t = message.get("my_time", 0)
            op_t = message.get("opponent_time", 0)
            my_str = f"{my_t // 60}:{my_t % 60:02d}"
            op_str = f"{op_t // 60}:{op_t % 60:02d}"
            self.ui.timer_label.config(text=f"My Time: {my_str} | Opponent: {op_str}")

        elif action == "game_over":
            winner = message.get("winner")
            error_list = message.get("errors", []) 

            if error_list:
                self.ui.highlight_errors(error_list)

            self.window.update_idletasks()

            messagebox.showinfo("Kết thúc", f"Người thắng: {winner}")
            self.ui.disable_all()

            self.current_game_id = None
            self.opponent = None
            if self.connected and self.btn_challenge:
                self.btn_challenge.config(state=tk.NORMAL)
            self.challenge_pending = False

        elif action == "challenge_declined":
            decliner = message.get("opponent")
            self.ui.add_chat_message(f"❌ {decliner} đã từ chối lời thách đấu.")
            if self.connected and not self.current_game_id and self.btn_challenge:
                self.btn_challenge.config(state=tk.NORMAL)
            self.challenge_pending = False

        elif action == "game_finish":
            time_remaining = message.get("time")
            should_wait = message.get("wait", True)
            
            self.ui.disable_all() 
            
            if should_wait:
                if time_remaining <= 0:
                    messagebox.showwarning("Hết giờ!", "Bạn đã hết thời gian! Bài làm đã được thu tự động.")
                else:
                    messagebox.showinfo("Đã nộp!", f"Bạn đã nộp bài! Đang chờ đối thủ...")
            
            if self.btn_submit:
                self.btn_submit.config(state=tk.DISABLED)

        elif action == "opponent_finished":
            self.ui.add_chat_message(f" {message.get('name')} đã hoàn thành Sudoku!")

    def request_history(self):
        """Gửi yêu cầu lấy lịch sử đấu"""
        if self.connected:
            self.send_message({"action": "get_history"})

    def show_history_popup(self, history_data):
        """Hiển thị cửa sổ popup chứa bảng lịch sử"""
        import time 
        
        top = tk.Toplevel(self.window)
        top.title(f"Lịch sử đấu của {self.username}")
        top.geometry("600x400")
        top.configure(bg="#f4ede4")

        from tkinter import ttk
        columns = ("time", "opponent", "result", "duration")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=15)
        
        tree.heading("time", text="Thời gian")
        tree.heading("opponent", text="Đối thủ")
        tree.heading("result", text="Kết quả")
        tree.heading("duration", text="Thời lượng")
        
        tree.column("time", width=150, anchor="center")
        tree.column("opponent", width=100, anchor="center")
        tree.column("result", width=100, anchor="center")
        tree.column("duration", width=100, anchor="center")
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for match in history_data:
            end_time = match.get("end_time", 0)
            date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(end_time))
            
            p1 = match.get("player1")
            p2 = match.get("player2")
            winner = match.get("winner")
            
            if self.username == p1:
                opponent = p2
            else:
                opponent = p1
            
            if winner == self.username:
                res = "THẮNG"
            elif winner == "Draw" or winner == "Draw (Timeout)":
                res = "HÒA"
            else:
                res = "THUA"
            
            duration = match.get("duration", 0)
            dur_str = f"{int(duration)}s"
            
            tree.insert("", tk.END, values=(date_str, opponent, res, dur_str))

        tk.Button(top, text="Đóng", command=top.destroy).pack(pady=5)

    def submit_solution(self):
        if not self.current_game_id:
            return
            
        if not self.ui.check_board_full():
            messagebox.showwarning("Chưa xong", "Bạn phải điền đầy đủ bàn cờ trước khi nộp bài.")
            return

        self.ui.add_chat_message("Đã nộp bài! Đang chờ đối thủ...")
        self.send_message({"action": "submit_solution"})
        
        self.ui.disable_all()
        if self.btn_submit:
            self.btn_submit.config(state=tk.DISABLED)

    # ------------------- Hành động người chơi -------------------
    def challenge_player(self):
        if not self.user_listbox: return
        
        sel = self.user_listbox.curselection()
        if self.current_game_id:
            messagebox.showinfo("Thách đấu", "Bạn đang trong trận đấu hiện tại.")
            return
        if self.challenge_pending:
            messagebox.showinfo("Thách đấu", "Đang chờ phản hồi lời thách đấu trước.")
            return
        if not sel:
            messagebox.showwarning("Thách đấu", "Chọn người chơi để thách đấu!")
            return
        opp = self.user_listbox.get(sel[0])
        msg = {"action": "challenge", "opponent": opp}
        self.send_message(msg)
        self.ui.add_chat_message(f"📤 Đã gửi lời mời thách đấu tới {opp}")
        if self.btn_challenge:
            self.btn_challenge.config(state=tk.DISABLED)
        self.challenge_pending = True

    def send_chat(self):
        if not hasattr(self.ui, 'chat_entry'): return 
            
        text = self.ui.chat_entry.get()
        if not text:
            return
        if not self.current_game_id:
            self.ui.add_chat_message("Bạn chưa trong ván game!")
            return
        msg = {"action": "chat", "game_id": self.current_game_id, "message": text}
        self.send_message(msg)
        self.ui.add_chat_message(f"[Tôi]: {text}")
        self.ui.chat_entry.delete(0, tk.END)

    def send_move(self, r, c, val):
        if self.current_game_id:
            msg = {"action": "move", "game_id": self.current_game_id, "cell": [r, c], "value": val}
            self.send_message(msg)

    def on_closing(self):
        self.disconnect()
        self.window.destroy()


# =====================================================
# CHẠY CHƯƠNG TRÌNH
# =====================================================
if __name__ == "__main__":
    ClientGUI()
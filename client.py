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
        self.window.title("Sudoku Multiplayer")
        self.window.configure(bg="#f4ede4")

        # Tiêu đề
        title = tk.Label(
            self.window, text="Sudoku Multiplayer",
            font=("Arial", 24, "bold"), bg="#f4ede4", fg="#5a3825"
        )
        title.pack(pady=(10, 5))

        # Khung Sudoku
        self.game_frame = tk.Frame(self.window, bg="#8B5A2B", bd=8, relief="ridge")
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
                        self.cells[gr][gc] = cell
                        self.cell_name_to_coord[str(cell)] = (gr, gc)

        button_frame = tk.Frame(self.window, bg="#f4ede4")
        button_frame.pack(pady=(0, 10)) # Cách trên 0, cách dưới 10

        # Tạo nút Hoàn Thành
        # LƯU Ý QUAN TRỌNG: Gán nó vào self.client.btn_submit 
        # để các hàm logic bên dưới vẫn điều khiển được nó (bật/tắt)
        self.client.btn_submit = tk.Button(
            button_frame, 
            text="Hoàn thành", 
            bg="#28a745", 
            fg="white",
            font=("Arial", 12, "bold"), # Cho to lên một chút cho đẹp
            command=self.client.submit_solution, 
            state=tk.DISABLED,
            width=15
        )
        self.client.btn_submit.pack()

        # Chat box
        chat_label = tk.Label(self.window, text="Chat", font=("Arial", 14, "bold"), bg="#f4ede4", fg="#5a3825")
        chat_label.pack(pady=(10, 0))

        self.chat_area = scrolledtext.ScrolledText(self.window, height=8, state=tk.DISABLED,
                                                   bg="#fff9f4", fg="#2c2c2c", wrap="word", relief="solid")
        self.chat_area.pack(pady=5, fill=tk.X)

        self.chat_entry = tk.Entry(self.window, width=40, font=('Arial', 12), bg="#f8e9d2", relief="solid")
        self.chat_entry.pack(fill=tk.X, pady=(0, 10))
        self.chat_entry.bind("<Return>", lambda e: self.client.send_chat())

        self.timer_label = tk.Label(self.window, text="My Time: 0:00 | Opponent: 0:00",
                                    font=("Arial", 12), bg="#f4ede4", fg="#5a3825")
        self.timer_label.pack()

    def check_board_full(self):
        """Kiểm tra xem tất cả ô có thể điền đã được điền chưa"""
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                # Nếu ô đó không phải là 'readonly' (ô đề bài) 
                # và nó đang trống
                if cell.cget('state') != 'readonly' and not cell.get():
                    return False # Vẫn còn ô trống
        return True # Đã đầy

    def delayed_check_full(self):
        """
        Kiểm tra sau 1ms để đảm bảo tkinter đã cập nhật giá trị.
        Hàm này sẽ Bật hoặc Tắt nút 'Hoàn thành'
        """
        if self.check_board_full():
            self.client.btn_submit.config(state=tk.NORMAL)
        else:
            self.client.btn_submit.config(state=tk.DISABLED)

    # ------------------- Sudoku logic -------------------
    def validate_entry(self, value, widget_name):
        """Chỉ cho phép nhập số 1-9"""
        # Lên lịch kiểm tra, bất kể phím gõ là gì
        # 'after(1)' đảm bảo nó chạy SAU KHI tkinter đã cập nhật ô
        self.window.after(1, self.delayed_check_full)

        if not (value == "" or (len(value) == 1 and value in "123456789")):
            return False

        if not self.client.current_game_id:
            return True

        try:
            r, c = self.cell_name_to_coord[widget_name]
        except KeyError:
            return False

        if value == "":
            # Người dùng đang xóa số
            # [Tùy chọn: Gửi nước đi là None/0 để cập nhật]
            # self.client.send_move(r, c, None) 
            return True
        
        # Người dùng đang thêm số
        self.client.send_move(r, c, int(value))
        self.cells[r][c].config(fg="#555555")

        return True

    def display_puzzle(self, puzzle):
        """Hiển thị đề bài Sudoku"""
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                cell.config(state="normal")
                cell.delete(0, tk.END)
                # Reset tất cả các màu nền về mặc định của game (#f8e9d2)
                # Phải reset cả disabledbackground và readonlybackground để xóa màu đỏ cũ
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
            widget.config(state="normal")
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
            widget.config(state="readonly", fg="red", readonlybackground=widget.cget('bg'))
        except Exception as e:
            self.add_chat_message(f"Lỗi cập nhật ô: {e}")

    def disable_all(self):
        for r in range(9):
            for c in range(9):
                self.cells[r][c].config(state=tk.DISABLED)

    def highlight_errors(self, error_list):
        """Nhận 1 list tọa độ [[r, c], ...] và tô màu các ô đó"""
        error_color = "#FC665C" # Đây là màu rgb(252, 102, 92)
        
        self.log(f"Highlighting {len(error_list)} errors.") # Tùy chọn: log
        
        for coord in error_list:
            try:
                r, c = coord
                cell_widget = self.cells[r][c]
                
                # Thay vì chỉ config bg, hãy config cả disabledbackground và readonlybackground
                # Điều này đảm bảo khi game over (ô bị disable), nó vẫn hiện màu đỏ
                cell_widget.config(
                    bg=error_color, 
                    disabledbackground=error_color, 
                    readonlybackground=error_color
                )
            except Exception as e:
                self.log(f"Error highlighting cell {coord}: {e}") # Tùy chọn: log

    def log(self, message):
        """Hàm helper để log (gọi hàm add_chat_message)"""
        # Bạn có thể dùng hàm này nếu muốn, hoặc gọi thẳng self.client.ui.add_chat_message
        self.add_chat_message(f"[Debug]: {message}")

    # ------------------- Chat -------------------
    def add_chat_message(self, msg):
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

        # GUI chính
        self.window = tk.Tk()
        self.window.configure(bg="#f4ede4")

        # Khung kết nối
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
        connect_frame.pack(pady=5)

        # Danh sách người dùng
        user_frame = tk.Frame(self.window, bg="#f4ede4")
        self.user_listbox = tk.Listbox(user_frame, height=5)
        self.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.btn_challenge = tk.Button(user_frame, text="Thách đấu", bg="#b97a57", fg="white",
                                       command=self.challenge_player, state=tk.DISABLED)
        self.btn_challenge.pack(side=tk.RIGHT, padx=5)
        # self.btn_submit = tk.Button(user_frame, text="Hoàn thành", bg="#28a745", fg="white",
        #                               command=self.submit_solution, state=tk.DISABLED)
        # self.btn_submit.pack(side=tk.RIGHT, padx=5)
        
        self.btn_history = tk.Button(user_frame, text="Lịch sử", bg="#6c757d", fg="white",
                                     command=self.request_history, state=tk.DISABLED)
        self.btn_history.pack(side=tk.RIGHT, padx=5)

        user_frame.pack(pady=5, fill=tk.X)

        # Khung Sudoku UI
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
            self.btn_challenge.config(state=tk.NORMAL)
            self.btn_history.config(state=tk.NORMAL)
            self.ui.add_chat_message(f" Kết nối thành công với tên: {self.username}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối: {e}")

    def disconnect(self):
        if not self.connected: 
            return # Nếu đã ngắt rồi thì thoát luôn, không in log, không xử lý lại
        
        self.connected = False # Đặt cờ ngay lập tức

        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.btn_challenge.config(state=tk.DISABLED)
        self.btn_history.config(state=tk.DISABLED)
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
        # Bộ giải mã JSON, dùng để đọc từng object một
        decoder = json.JSONDecoder()
        
        while self.connected:
            try:
                # 1. Nhận dữ liệu và thêm vào buffer
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break # Server ngắt kết nối
                
                self.buffer += data
                
                # 2. Xử lý tất cả các tin nhắn hoàn chỉnh có trong buffer
                while self.buffer:
                    try:
                        # 3. Dùng raw_decode để tìm 1 JSON object hoàn chỉnh
                        # Nó trả về (object, vị trí kết thúc)
                        msg, idx = decoder.raw_decode(self.buffer)
                        
                        # 4. Xử lý tin nhắn
                        self.window.after(0, self.handle_server_message, msg)
                        
                        # 5. Cắt bỏ tin nhắn đã xử lý khỏi buffer
                        # lstrip() để xóa khoảng trắng (nếu có)
                        self.buffer = self.buffer[idx:].lstrip()
                        
                    except json.JSONDecodeError:
                        # Nếu buffer không chứa 1 JSON hoàn chỉnh (ví dụ: bị cắt giữa chừng)
                        # thì break vòng lặp 'while self.buffer'
                        # và quay lại chờ recv() thêm dữ liệu
                        break
            
            except Exception as e:
                # Nếu có lỗi nghiêm trọng (ví dụ: mất kết nối)
                if self.connected: # Chỉ log nếu chúng ta không chủ động ngắt
                    self.ui.add_chat_message(f"Lỗi kết nối: {e}")
                break
                
        # Chỉ gọi disconnect nếu vòng lặp bị phá vỡ
        self.disconnect()

    def handle_server_message(self, message):
        action = message.get("action")
        if action == "user_list":
            self.user_listbox.delete(0, tk.END)
            for u in message.get("users", []):
                if u != self.username:
                    self.user_listbox.insert(tk.END, u)

        elif action == "challenge_request":
            challenger = message.get("from")
            accept = messagebox.askyesno("Thách đấu", f"{challenger} thách đấu bạn! Chấp nhận?")
            resp = {"action": "challenge_response", "opponent": challenger, "accept": accept}
            self.send_message(resp)
            if accept:
                self.btn_challenge.config(state=tk.DISABLED)
                self.challenge_pending = False

        elif action == "game_start":
            self.current_game_id = message.get("game_id")
            self.opponent = message.get("opponent")
            puzzle = message.get("puzzle")
            self.ui.display_puzzle(puzzle)
            self.ui.add_chat_message(f" Game bắt đầu với {self.opponent}")
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
            error_list = message.get("errors", []) # LẤY DANH SÁCH LỖI

            if error_list:
                self.ui.highlight_errors(error_list)

            self.window.update_idletasks()

            messagebox.showinfo("Kết thúc", f"Người thắng: {winner}")
            self.ui.disable_all()

            self.current_game_id = None
            self.opponent = None
            if self.connected:
                self.btn_challenge.config(state=tk.NORMAL)
            self.challenge_pending = False

        elif action == "challenge_declined":
            decliner = message.get("opponent")
            self.ui.add_chat_message(f"❌ {decliner} đã từ chối lời thách đấu.")
            if self.connected and not self.current_game_id:
                self.btn_challenge.config(state=tk.NORMAL)
            self.challenge_pending = False

        elif action == "game_finish":
            time_remaining = message.get("time")
            should_wait = message.get("wait", True)
            
            # KHÓA BÀN CỜ NGAY LẬP TỨC KHI SERVER BÁO ĐÃ NỘP (HOẶC HẾT GIỜ)
            self.ui.disable_all() 
            
            if should_wait:
                # Nếu hết giờ, time_remaining sẽ là 0 hoặc số âm
                if time_remaining <= 0:
                    messagebox.showwarning("Hết giờ!", "Bạn đã hết thời gian! Bài làm đã được thu tự động.")
                else:
                    messagebox.showinfo("Đã nộp!", f"Bạn đã nộp bài! Đang chờ đối thủ...")
            
            self.btn_submit.config(state=tk.DISABLED)

        elif action == "opponent_finished":
            self.ui.add_chat_message(f" {message.get('name')} đã hoàn thành Sudoku!")

    def request_history(self):
        """Gửi yêu cầu lấy lịch sử đấu"""
        if self.connected:
            self.send_message({"action": "get_history"})

    def show_history_popup(self, history_data):
        """Hiển thị cửa sổ popup chứa bảng lịch sử"""
        import time # Import time để xử lý ngày tháng
        
        top = tk.Toplevel(self.window)
        top.title(f"Lịch sử đấu của {self.username}")
        top.geometry("600x400")
        top.configure(bg="#f4ede4")

        # Sử dụng Treeview để làm bảng
        from tkinter import ttk
        columns = ("time", "opponent", "result", "duration")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=15)
        
        # Định nghĩa cột
        tree.heading("time", text="Thời gian")
        tree.heading("opponent", text="Đối thủ")
        tree.heading("result", text="Kết quả")
        tree.heading("duration", text="Thời lượng")
        
        tree.column("time", width=150, anchor="center")
        tree.column("opponent", width=100, anchor="center")
        tree.column("result", width=100, anchor="center")
        tree.column("duration", width=100, anchor="center")
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Đổ dữ liệu
        for match in history_data:
            # 1. Xử lý thời gian
            end_time = match.get("end_time", 0)
            date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(end_time))
            
            # 2. Xác định đối thủ và kết quả
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
            
            # 3. Thời lượng
            duration = match.get("duration", 0)
            dur_str = f"{int(duration)}s"
            
            # Thêm vào bảng (thêm tag màu sắc nếu muốn)
            tree.insert("", tk.END, values=(date_str, opponent, res, dur_str))

        # Nút đóng
        tk.Button(top, text="Đóng", command=top.destroy).pack(pady=5)

    def submit_solution(self):
        if not self.current_game_id:
            return
            
        if not self.ui.check_board_full():
            messagebox.showwarning("Chưa xong", "Bạn phải điền đầy đủ bàn cờ trước khi nộp bài.")
            return

        self.ui.add_chat_message("Đã nộp bài! Đang chờ đối thủ...")
        self.send_message({"action": "submit_solution"})
        
        # Khóa bàn cờ lại
        self.ui.disable_all()
        self.btn_submit.config(state=tk.DISABLED)

    # ------------------- Hành động người chơi -------------------
    def challenge_player(self):
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
        self.btn_challenge.config(state=tk.DISABLED)
        self.challenge_pending = True

    def send_chat(self):
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

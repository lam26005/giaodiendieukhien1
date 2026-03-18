import tkinter as tk
from tkinter import messagebox
import serial
import threading

SERIAL_PORT = "COM4"
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except:
    ser = None
    print("⚠ Không thể kết nối tới Arduino")

def send_parameters():
    try:
        t = float(entry_target.get())
        kp = float(entry_kp.get())
        ki = float(entry_ki.get())
        kd = float(entry_kd.get())
        message = f"T:{t} Kp:{kp} Ki:{ki} Kd:{kd}\n"
        if ser:
            ser.write(message.encode())
    except ValueError:
        messagebox.showerror("Lỗi", "Vui lòng nhập đúng định dạng số")

def read_serial():
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode().strip()
                if line.startswith("Angle:"):
                    feedback_text.set(line)
            except:
                pass

root = tk.Tk()
root.title("Giao diện điều khiển PID động cơ DC")

tk.Label(root, text="Góc xoay yêu cầu").grid(row=0, column=0, sticky='e')
entry_target = tk.Entry(root)
entry_target.insert(0, "0.0")
entry_target.grid(row=0, column=1)

tk.Label(root, text="Kp").grid(row=1, column=0, sticky='e')
entry_kp = tk.Entry(root)
entry_kp.insert(0, "0.0")
entry_kp.grid(row=1, column=1)

tk.Label(root, text="Ki").grid(row=2, column=0, sticky='e')
entry_ki = tk.Entry(root)
entry_ki.insert(0, "0.0")
entry_ki.grid(row=2, column=1)

tk.Label(root, text="Kd").grid(row=3, column=0, sticky='e')
entry_kd = tk.Entry(root)
entry_kd.insert(0, "0.0")
entry_kd.grid(row=3, column=1)

btn_send = tk.Button(root, text="Gửi thông số", command=send_parameters, bg="#4CAF50", fg="white")
btn_send.grid(row=4, column=0, columnspan=2, pady=10)

tk.Label(root, text="Phản hồi từ Arduino:", font=("Arial", 10, "bold")).grid(row=5, column=0, columnspan=2)
feedback_text = tk.StringVar()
feedback_text.set("Chưa có dữ liệu...")
label_feedback = tk.Label(root, textvariable=feedback_text, fg="blue", justify="left", wraplength=400)
label_feedback.grid(row=6, column=0, columnspan=2, padx=10, pady=5)

threading.Thread(target=read_serial, daemon=True).start()

root.mainloop()
import sys
import serial
import time
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog
from PyQt5.uic import loadUi
import pyqtgraph as pg
from collections import deque

# Cấu hình Serial (Thử kết nối)
try:
    # Lưu ý: timeout=0.1 để đọc nhanh hơn, tránh lag giao diện
    ser = serial.Serial("COM3", 115200, timeout=0.1)
except:
    ser = None
    print("⚠ Không thể kết nối tới Arduino")


class SerialReader(QtCore.QThread):
    data_received = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True

    def run(self):
        global ser
        while self.is_running and ser and ser.is_open:
            try:
                # Đọc từng dòng, giải mã an toàn
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.data_received.emit(line)
            except Exception as e:
                # Không in lỗi liên tục để tránh spam console
                pass

            # Nghỉ cực ngắn để giảm tải CPU
            time.sleep(0.005)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class Control(QMainWindow):
    def __init__(self):
        super(Control, self).__init__()
        loadUi("control.ui", self)

        # === CẤU HÌNH ĐỒ THỊ 1 (VẬN TỐC) ===
        self.Bang1.setTitle("Vận tốc thực tế", color='b', size="10pt")
        self.Bang1.showGrid(x=True, y=True)
        self.Bang1.setLabel('left', 'Vận tốc', units='deg/s')
        self.Bang1.setLabel('bottom', 'Thời gian', units='s')
        self.line_v_a = self.Bang1.plot(pen=pg.mkPen('r', width=2), name="v_actual")
        self.Bang1.setBackground('w')

        # === CẤU HÌNH ĐỒ THỊ 2 (GIA TỐC) ===
        self.Bang2.setTitle("Góc xoay thực tế", color='b', size="10pt")
        self.Bang2.showGrid(x=True, y=True)
        self.Bang2.setLabel('left', 'Góc xoay', units='deg')
        self.Bang2.setLabel('bottom', 'Thời gian', units='s')
        self.line_a_a = self.Bang2.plot(pen=pg.mkPen('g', width=2), name="q_target")
        self.Bang2.setBackground('w')

        # === KẾT NỐI NÚT ===
        self.settingbutton.clicked.connect(self.gotosetting)
        self.pushButton1.clicked.connect(self.nhap_du_lieu)

        # === DỮ LIỆU ===
        self.maxlen = 200  # Giảm bớt số điểm lưu để vẽ mượt hơn
        self.time_data = deque(maxlen=self.maxlen)
        self.velocity_a_data = deque(maxlen=self.maxlen)
        self.acceleration_a_data = deque(maxlen=self.maxlen)
        self.start_time = 0

        # === KHỞI ĐỘNG LUỒNG ĐỌC ===
        self.reader_thread = None
        if ser:
            self.reader_thread = SerialReader()
            self.reader_thread.data_received.connect(self.hien_thi_du_lieu)
            self.reader_thread.start()
            self.statusbar.showMessage("✓ Đã kết nối Arduino (COM3)", 5000)
        else:
            self.statusbar.showMessage("⚠ Lỗi kết nối Arduino!", 5000)

    def gotosetting(self):
        setting = Setting()
        widget.addWidget(setting)
        widget.setCurrentIndex(widget.currentIndex() + 1)
        widget.setFixedSize(444, 340)

    def nhap_du_lieu(self):
        """Gửi lệnh xuống Arduino"""
        goc = self.textEdit.toPlainText().strip()
        time_val = self.textEdit_2.toPlainText().strip()
        l_val = self.textEdit_3.toPlainText().strip()

        try:
            # Chuyển đổi sang float để kiểm tra
            g_f = float(goc)
            t_f = float(time_val)
            l_f = float(l_val)

            # === [QUAN TRỌNG] ===
            # Format chuỗi gửi đi thật gọn (chỉ lấy 2 số thập phân)
            # để tránh làm tràn bộ đệm của Arduino String
            cmd = "q_target:{:.2f} T_total:{:.2f} l:{:.3f}\n".format(g_f, t_f, l_f)

            if ser and ser.is_open:
                ser.reset_input_buffer()  # Xóa dữ liệu rác cũ
                ser.write(cmd.encode())  # Gửi lệnh
                print(f"SENT: {cmd.strip()}")

                # Reset biểu đồ khi gửi lệnh mới
                self.time_data.clear()
                self.velocity_a_data.clear()
                self.acceleration_a_data.clear()
                self.start_time = 0

                self.statusbar.showMessage("✓ Đã gửi lệnh chạy!", 3000)
            else:
                print(f"OFFLINE CMD: {cmd.strip()}")
                self.statusbar.showMessage("⚠ Chưa kết nối Arduino", 3000)

        except ValueError:
            self.statusbar.showMessage("⚠ Vui lòng nhập số hợp lệ!")

    def hien_thi_du_lieu(self, line):
        """Xử lý dữ liệu nhận về từ Arduino"""
        # Mẫu: t:1.23s | q_target:90.0° q_a:89.5° | v_d:0.0°/s v_a:0.1°/s | ...
        if line.startswith("t:"):
            try:
                parts = line.split('|')

                # 1. Lấy thời gian (t:...)
                t_str = parts[0].split(':')[1].replace('s', '').strip()
                t_curr = float(t_str)

                # 2. Lấy góc thực tế (q_a:...)
                # Tìm phần tử chứa "q_a"
                q_part = [p for p in parts if "q_a:" in p][0]
                q_val = float(q_part.split('q_a:')[1].replace('°', '').strip())

                # 3. Lấy vận tốc thực tế (v_a:...)
                v_part = [p for p in parts if "v_a:" in p][0]
                v_val = float(v_part.split('v_a:')[1].replace('°/s', '').strip())

                # 4. Lấy gia tốc thực tế (a_a:...)
                a_part = [p for p in parts if "a_a:" in p][0]
                a_val = float(a_part.split('a_a:')[1].replace('°/s²', '').strip())

                # === CẬP NHẬT HIỂN THỊ SỐ ===
                self.textBrowser_2.setPlainText(f"{q_val:.1f}")
                self.textBrowser_4.setPlainText(f"{v_val:.1f}")
                self.textBrowser_3.setPlainText(f"{a_val:.1f}")

                # === CẬP NHẬT BIỂU ĐỒ ===
                # Logic thời gian: t0 bắt đầu từ lúc Arduino gửi t=0
                if t_curr < 0.05 and len(self.time_data) > 10:
                    # Nếu thời gian quay về 0 -> Arduino vừa reset -> Xóa đồ thị cũ
                    self.time_data.clear()
                    self.velocity_a_data.clear()
                    self.acceleration_a_data.clear()

                self.time_data.append(t_curr)
                self.velocity_a_data.append(v_val)
                self.acceleration_a_data.append(a_val)

                # Chỉ vẽ lại mỗi 3 điểm dữ liệu nhận được để giảm tải giao diện
                if len(self.time_data) % 3 == 0:
                    self.line_v_a.setData(list(self.time_data), list(self.velocity_a_data))
                    self.line_a_a.setData(list(self.time_data), list(self.acceleration_a_data))

            except (IndexError, ValueError) as e:
                # Bỏ qua các dòng lỗi form (do nhiễu đường truyền)
                pass

        elif "Homed" in line:
            self.statusbar.showMessage("ℹ Đã về Home thành công!")


class Setting(QDialog):
    def __init__(self):
        super(Setting, self).__init__()
        loadUi("setting.ui", self)
        self.backtocontrolbutton.clicked.connect(self.backtocontrol)
        self.pushButton2.clicked.connect(self.nhap_thong_so)

    def nhap_thong_so(self):
        # Lấy dữ liệu và gửi chuỗi ngắn gọn
        try:
            params = {
                'B': float(self.plainTextEdit.toPlainText()),
                'I': float(self.plainTextEdit_2.toPlainText()),
                # 'R': float(self.plainTextEdit_3.toPlainText()), # Arduino code ko dùng R
                'kp': float(self.plainTextEdit_7.toPlainText()),
                'kd': float(self.plainTextEdit_8.toPlainText()),
                'm': float(self.plainTextEdit_5.toPlainText())
            }

            # Format chuỗi gửi: "kp:12.0 kd:1.0 ..."
            cmd = ""
            for key, val in params.items():
                cmd += f"{key}:{val:.4f} "
            cmd += "\n"

            if ser and ser.is_open:
                ser.write(cmd.encode())
                print(f"SETTING: {cmd.strip()}")
            else:
                print("Chưa kết nối Arduino")

        except ValueError:
            print("Lỗi nhập liệu setting")

    def backtocontrol(self):
        control = Control()
        widget.addWidget(control)
        widget.setCurrentIndex(widget.currentIndex() + 1)
        widget.setFixedSize(858, 808)


# ==================== MAIN ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainwindow = Control()
    widget = QtWidgets.QStackedWidget()
    widget.addWidget(mainwindow)
    widget.setFixedWidth(858)
    widget.setFixedHeight(808)
    widget.show()
    sys.exit(app.exec_())
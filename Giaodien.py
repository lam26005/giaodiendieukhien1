import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import serial

try:
    # Cổng COM và Baudrate phải khớp với Arduino
    ser = serial.Serial("COM3", 115200, timeout=1)
except Exception as e:
    ser = None
    print(f"⚠ Không thể kết nối tới Arduino: {e}")
    # Hiển thị lỗi này trên một cửa sổ pop-up
    # (Sẽ tốt hơn, nhưng tạm thời giữ nguyên)


# ================== WORKER THREAD ==================
class SerialReader(QtCore.QThread):
    """
    Luồng này CHỈ làm nhiệm vụ đọc dữ liệu từ Serial
    và phát ra tín hiệu khi có dòng mới.
    """
    data_received = QtCore.pyqtSignal(str)  # Tín hiệu phát ra dữ liệu mới

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True

    def run(self):
        """Chạy vòng lặp đọc dữ liệu serial."""
        global ser
        while self.is_running and ser:
            try:
                if ser.in_waiting > 0:
                    # Đọc 1 dòng, decode, và xoá khoảng trắng thừa
                    line = ser.readline().decode(errors="ignore").strip()
                    if line:
                        self.data_received.emit(line)  # Gửi dữ liệu về GUI
            except serial.SerialException as se:
                print(f"⚠ Lỗi Serial (có thể đã rút dây): {se}")
                self.is_running = False  # Dừng thread nếu có lỗi nghiêm trọng
            except Exception as e:
                print(f"⚠ Lỗi đọc serial: {e}")

    def stop(self):
        """Dừng thread."""
        self.is_running = False
        self.quit()
        self.wait(2000)  # Chờ tối đa 2s cho thread thoát


# ================== MAIN WINDOW (ĐÃ TÁI CẤU TRÚC) ==================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # === BẮT ĐẦU CODE setupUi CỦA BẠN ===
        # (Tôi đã chuyển toàn bộ code setupUi vào __init__)
        self.setObjectName("MainWindow")
        self.resize(556, 259)
        self.setWindowTitle("Bộ điều khiển Động cơ DC (PID)")

        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(260, 40, 141, 20))
        font = QtGui.QFont();
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setText("Góc xoay yêu cầu (°)")

        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(70, 150, 111, 31))
        self.pushButton.setText("Nhập dữ liệu")

        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setGeometry(QtCore.QRect(400, 40, 81, 31))
        self.plainTextEdit.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.plainTextEdit.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.plainTextEdit.setPlainText("0.0")

        self.plainTextEdit_2 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_2.setGeometry(QtCore.QRect(90, 20, 81, 31))
        self.plainTextEdit_2.setPlainText("2.0")  # Giá trị Kp mặc định

        self.plainTextEdit_3 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_3.setGeometry(QtCore.QRect(90, 60, 81, 31))
        self.plainTextEdit_3.setPlainText("0.01")  # Giá trị Ki mặc định

        self.plainTextEdit_4 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_4.setGeometry(QtCore.QRect(90, 100, 81, 31))
        self.plainTextEdit_4.setPlainText("0.05")  # Giá trị Kd mặc định

        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(60, 20, 21, 20))
        font = QtGui.QFont();
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setText("Kp")

        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(60, 60, 21, 20))
        font = QtGui.QFont();
        font.setPointSize(10)
        self.label_4.setFont(font)
        self.label_4.setText("Ki")

        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(60, 100, 21, 20))
        font = QtGui.QFont();
        font.setPointSize(10)
        self.label_3.setFont(font)
        self.label_3.setText("Kd")

        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(260, 90, 141, 20))
        font = QtGui.QFont();
        font.setPointSize(10)
        self.label_5.setFont(font)
        self.label_5.setText("Góc xoay hiện tại (°)")

        self.Gocxoay = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.Gocxoay.setGeometry(QtCore.QRect(400, 90, 81, 31))
        self.Gocxoay.setReadOnly(True)  # <<< CẢI TIẾN: Không cho người dùng sửa ô này
        self.Gocxoay.setPlainText("---")

        self.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 556, 26))
        self.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)
        # === KẾT THÚC CODE setupUi ===

        # === PHẦN LOGIC MỚI ===

        # <<< FIX 1: KẾT NỐI NÚT BẤM
        self.pushButton.clicked.connect(self.nhap_du_lieu)

        # <<< FIX 2: KHỞI TẠO VÀ KẾT NỐI THREAD 1 LẦN DUY NHẤT
        self.reader_thread = None
        if ser:
            self.reader_thread = SerialReader()
            # Kết nối tín hiệu 'data_received' từ thread với hàm 'hien_thi_du_lieu'
            self.reader_thread.data_received.connect(self.hien_thi_du_lieu)
            self.reader_thread.start()  # Bắt đầu chạy thread
            self.statusbar.showMessage("Đã kết nối với Arduino.", 5000)  # 5000ms
        else:
            self.statusbar.showMessage("⚠ Không thể kết nối Arduino. Chạy ở chế độ offline.")

    # ================== HÀM 1: GỬI DỮ LIỆU (ĐÃ SỬA) ==================
    def nhap_du_lieu(self):
        """
        Được gọi khi nhấn nút 'Nhập dữ liệu'.
        Chỉ làm nhiệm vụ LẤY DỮ LIỆU và GỬI ĐI.
        """
        goc = self.plainTextEdit.toPlainText().strip()
        kp = self.plainTextEdit_2.toPlainText().strip()
        ki = self.plainTextEdit_3.toPlainText().strip()
        kd = self.plainTextEdit_4.toPlainText().strip()

        # Định dạng chuẩn, có \n ở cuối
        data = f"T:{goc} Kp:{kp} Ki:{ki} Kd:{kd}\n"
        print("➡ Dữ liệu nhập:", data)

        if ser:
            try:
                ser.write(data.encode())
                self.statusbar.showMessage(f"Đã gửi: T={goc}°", 3000)
            except Exception as e:
                self.statusbar.showMessage(f"⚠ Lỗi gửi dữ liệu: {e}")
        else:
            print("⚠ Chưa có kết nối Arduino, chỉ in dữ liệu.")
            self.statusbar.showMessage("⚠ Không có kết nối Arduino!")

        # <<< FIX: KHÔNG TẠO THREAD MỚI Ở ĐÂY NỮA

    # ================== HÀM 2: HIỂN THỊ DỮ LIỆU (ĐÃ SỬA) ==================
    def hien_thi_du_lieu(self, line):
        """
        Được gọi BẤT CỨ KHI NÀO thread SerialReader có dữ liệu mới.
        Nhiệm vụ: Lọc và hiển thị dữ liệu lên GUI.
        """
        # print("⬅ Dữ liệu Arduino:", line) # Bỏ comment nếu muốn gỡ lỗi

        # <<< FIX 3: LỌC DỮ LIỆU ĐỂ HIỂN THỊ
        if line.startswith("C:"):
            # Đây là dòng dữ liệu góc (VD: "C:89.75")
            angle_value = line[2:]  # Bỏ 2 ký tự "C:"
            self.Gocxoay.setPlainText(angle_value)

        elif line.startswith("Homed") or line.startswith("Đã nhận") or line.startswith(">>"):
            # Đây là thông báo trạng thái từ Arduino
            self.statusbar.showMessage(line)

        # (Những dòng không nhận dạng được sẽ bị bỏ qua)

    # ================== HÀM 3: DỌN DẸP KHI TẮT (MỚI) ==================
    def closeEvent(self, event):
        """
        <<< FIX 4: Được gọi khi người dùng nhấn nút X (đóng cửa sổ).
        Dọn dẹp tài nguyên trước khi thoát.
        """
        print("Đang đóng ứng dụng...")
        if self.reader_thread:
            self.reader_thread.stop()  # Dừng thread
        if ser:
            ser.close()  # Đóng cổng COM

        event.accept()  # Chấp nhận sự kiện đóng


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Khởi tạo cửa sổ chính đã được tái cấu trúc
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
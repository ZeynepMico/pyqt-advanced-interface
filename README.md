# PyQt5 Advanced Serial Port & SSH Interface

This project is NETA Electronics A.Sh. August June–August 2025) was developed during the internship period in the company. The project is a multifunctional desktop application developed to listen to, parse, visualize, and log serial port data, as well as establish and manage connections from a remote device via SSH/SFTP. It was built using the PyQt5 library.

## 🚀 Key Features

* **Serial Port Management:**
* Automatically list and refresh available ports.
* Adjustable Baud Rate, Data Bits, Parity, and Stop Bits.
* Instantly display and save incoming raw data to a file.
* Stop/Start data stream.

* **Advanced Data Parsing:**
* **Simple Mode:** Parsing data incoming with separators such as commas based on column numbers.
* **Regex Mode:** Capture data with Regular Expression for complex data structures.
* **Binary Mode:** Process binary GPS data directly packaged as `struct`.
* **Package Mode:** Verify and process secure data packets with headers and CRC16 checks.

* **Real-Time Graph:**
* Plot up to 8 channels of data simultaneously using `pyqtgraph`.
* Pause, clear, and manually adjust axis ranges on the graph.
* Export graph image as PNG/SVG.
* Hide/show desired graph channels.

* **Interactive Map & GPS Calculations:**
* Display live GPS data (Home location) on the interactive map based on Leaflet.js.
* Accumulate the traveled path as a route on the map (Live Route).
* Switch between different map layers (Standard, Satellite, Topographic).
* Set the Target location by clicking on the map or entering it manually.
* Advanced calculations between Home and Target locations:
* Surface distance (`geodesic`).
* 3D Space distance (Slant Range), Azimuth, and Elevation angles.
* ECEF (Earth-Centered, Earth-Fixed) coordinates of both points.

* **SSH & SFTP Client:**
* Connect to a remote server (Raspberry Pi, Linux server, etc.) via SSH.
* Send commands via the interactive terminal and view the output.
* List files on the remote server with the SFTP file browser.
* Download, upload, delete, rename, and create new folders with the right-click menu.

* **User Management and Interface:**
* Three different authorization levels: Admin, User, and Guest.
* Restrict interface features (e.g., settings, terminal, SSH) based on authorization.
* Switch between Light and Dark themes.

* **Simulation Tools:**
* Test map features without needing a serial port with the built-in NMEA simulator.
* Simulate different data types with external Python scripts (`circular_rota_testi.py`, `grafik_test.py`).

## 🛠️ Installation and Operation

1. **Clone the Project:**
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_PROJECT_NAME.git](https://github.com/YOUR_USERNAME/YOUR_PROJECT_NAME.git)
cd YOUR_PROJECT_NAME
```

2. **Create and Activate a Virtual Environment (Recommended):**
```bash
python -m venv venv
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate
```

3. **Install Required Libraries:**
```bash
pip install -r requirements.txt
```

4. **Run the Application:**
```bash
python main.py
```

## ⚙️ Usage

* **Login Information:**
* **Admin:** `admin` / `admin123`
* **User:** `user` / `user123`
* **Guest:** By clicking the "Login as Guest" button.
* **Virtual Serial Port:** For testing, you can use a virtual serial port tool like [com0com](http://com0com.sourceforge.net/). You can listen to COM7 from the application while one of the simulator scripts writes to COM6.

## 📚 Libraries Used

The main libraries at the heart of the project:

* **[PyQt5](https://riverbankcomputing.com/software/pyqt/)**: The main interface framework.
* **[pyqtgraph](http://www.pyqtgraph.org/)**: For high-performance graphics.
* **[pyserial](https://pyserial.readthedocs.io/)**: For serial port communication.
* **[paramiko](http://www.paramiko.org/)**: For SSH and SFTP connections.
* **[geopy](https://geopy.readthedocs.io/)**: For surface distance calculations.
* **[pymap3d](https://github.com/geospace-code/pymap3d)**: For geodetic and ECEF coordinate transformations.

# 🏠 Smart Home Light Control System (Simulation)

An interactive, desktop-based Smart Home Lighting Simulation written in Python using **Tkinter** for the graphical interface and **Rich** for the terminal demonstration mode.

This project is a **100% software simulation** designed for demonstration and educational purposes. It manages virtual smart bulbs in memory and does not require or connect to physical IoT hardware (e.g., no microcontrollers, ESP32, Arduino, Zigbee, or MQTT brokers are needed).

---

## 📋 Features

- **Room Organization**: 10 pre-configured virtual smart bulbs distributed across 6 rooms (*Living Room, Bedroom, Kitchen, Office, Bathroom, Garage*).
- **Individual Light Controls**:
  - Power Toggle (**Turn ON / Turn OFF**) with immediate color-coded button feedback.
  - **Brightness Adjustment** (0% to 100%) via slider.
  - **Color Temperature Tuning** (2200K warm glow to 6500K cool daylight) via slider.
  - **Color Palette**: 10 preset hex color swatches for decorative lighting.
- **Quick Scene Presets**:
  - 7 preset atmospheres: *Morning, Focus, Relax, Movie, Dinner, Night, Energize*.
  - Independent scope execution: apply presets to either the **current room** or **all rooms** simultaneously.
- **Master Controls**: Global **All ON** and **All OFF** master switches in the navigation sidebar.
- **Energy & Power Usage Analytics**:
  - Live wattage estimation dynamically calculated based on light brightness (max 10 W per bulb).
  - Summary cards showing total lights, lights currently on, lights off, and active power consumption.
  - Per-room visual breakdown bar chart drawn on a responsive canvas.
- **Activity Logging**:
  - Timestamped chronological event log tracking user actions.
  - Direct GUI log viewer with a **Clear Log** button.
- **State Export**:
  - Portable JSON export of the current system state to `lights_state.json`.
  - Accessible via the terminal demo or the **💾 Export JSON** button in the GUI.
- **Dual Interface Modes**:
  - Full desktop graphical user interface with modern dark theme styling (`#1a1a2e`).
  - Terminal demonstration mode featuring styled tables and panels using the Rich library.

---

## 💻 Software Requirements

- **Python**: Version 3.8 or higher (tested and verified on **Python 3.14**).
- **Third-Party Package**:
  - `rich>=13.0.0` (required for the terminal demonstration mode).
- **Operating System Compatibility**:
  - **Tested and Verified**: **Windows** (Windows 10 / Windows 11).
  - *Note regarding other platforms:* This application was developed and tested on Windows. While standard Python and Tkinter code is cross-platform, non-Windows operating systems have not been tested in this environment.

---

## 🪟 Tkinter Requirement & Information

The Graphical User Interface (GUI) relies on Python's built-in `tkinter` package.

- **On Windows (Tested Platform)**:
  `tkinter` is bundled by default with standard Python installers downloaded from [python.org](https://www.python.org/).
  - If you encounter a `ModuleNotFoundError: No module named 'tkinter'` error on Windows, re-run the Python installer, choose **Modify**, and make sure the **tcl/tk and IDLE** checkbox is selected.
- **On Linux (Informational / Unverified)**:
  Some Linux distributions strip Tkinter from the base Python package. If running on Linux, Tkinter typically must be installed via the distribution's package manager (e.g., `sudo apt install python3-tk` on Debian/Ubuntu or `sudo dnf install python3-tkinter` on Fedora).
- **On macOS (Informational / Unverified)**:
  Tkinter is typically included with official Python installer packages from python.org or Homebrew (`brew install python-tk`).

---

## 🚀 Installation Steps

1. **Verify Python is installed**:
   Open a terminal (PowerShell or Command Prompt) and check your Python version:
   ```powershell
   python --version
   ```
   *(or `py --version`)*

2. **Navigate to the project folder**:
   ```powershell
   cd path\to\smart_home_IOT_simulation
   ```

3. **Install required dependencies**:
   Install the third-party dependencies from `requirements.txt`:
   ```powershell
   python -m pip install -r requirements.txt
   ```
   *(or `py -m pip install -r requirements.txt`)*

---

## 🎮 How to Launch the Application on Windows

### 1. Launch the Full Tkinter GUI (Recommended)
Run the script with the `--gui` flag:
```powershell
python smart_home_lights.py --gui
```
*(or using the Python launcher)*:
```powershell
py smart_home_lights.py --gui
```

### 2. Launch the Terminal Demonstration Mode
Run the script without flags to see the interactive Rich terminal output:
```powershell
python smart_home_lights.py
```
*(or using the Python launcher)*:
```powershell
py smart_home_lights.py
```

---

## 📖 How to Use the Application

### Using the Graphical Interface (GUI)

1. **Selecting a Room**:
   - In the left sidebar under **ROOMS**, click any room name (e.g., *Living Room*, *Bedroom*, *Kitchen*).
   - The **💡 Lights** tab updates to show all lights installed in that room.
2. **Controlling an Individual Light**:
   - In the **💡 Lights** table, click on a light to select it.
   - Click the green **Turn ON** or red **Turn OFF** button to toggle power.
   - Drag the **Brightness** slider (0–100%) to dim or brighten the light. Notice power consumption updates immediately.
   - Drag the **Color Temp** slider (2200K–6500K) to adjust between warm candle-glow and crisp daylight.
   - Click any colored square in the **Color** row to set an ambient light color.
3. **Applying Quick Scenes**:
   - Switch to the **🎨 Scenes** tab.
   - Choose a mood (e.g., *Movie, Focus, Relax, Night*).
   - Click **This Room** to apply the scene only to the currently selected room, or click **All** to apply it across the entire home.
4. **Master Controls**:
   - In the left sidebar under **MASTER**, click **☀ All ON** to switch every light on, or **🌙 All OFF** to power down the entire house.
5. **Viewing Power Analytics**:
   - Switch to the **📊 Usage** tab.
   - Review live cards showing active bulbs, inactive bulbs, and instantaneous power draw (in Watts).
   - Inspect the horizontal room-by-room status bars.
6. **Activity Log & JSON Export**:
   - Switch to the **📋 Log** tab to see a history of all room changes, power switches, and scene applications.
   - Click **💾 Export JSON** to save the current lighting state to `lights_state.json`.
   - Click **Clear Log** to reset the history.

---

## 🌐 Offline Operation (No Internet Required)

Once the `rich` package has been installed via `pip`, the application runs **100% offline**:
- No network connections, internet queries, or remote APIs are called.
- All light states, calculations, scenes, and log entries are handled locally in memory.
- State export is written strictly to local storage.

---

## 📦 How to Transfer the Project to Another Laptop

To move this project to a new laptop using a USB drive, cloud storage, or email:

### Step 1: Prepare and Copy the Project Folder
1. On your current laptop, locate the project folder:
   `C:\smart_home_IOT_simulation`
2. *(Optional Clean-up)*: You can delete the `__pycache__` folder if present, as Python will automatically recreate it on the new machine.
3. Compress the folder into a `.zip` archive:
   - In Windows File Explorer, right-click `smart_home_IOT_simulation` → **Compress to ZIP file** (or **Send to** → **Compressed (zipped) folder**).
4. Copy the `.zip` file (or uncompressed folder) onto a USB flash drive or transfer it via your preferred method.

### Step 2: Set Up on the Target Laptop
1. Paste and extract the folder onto the new laptop (for example, at `C:\smart_home_IOT_simulation` or `Desktop`).
2. Make sure Python 3.8+ is installed on the new laptop:
   - When installing Python from [python.org](https://www.python.org/), ensure **"Add python.exe to PATH"** and **"tcl/tk and IDLE"** are checked.
3. Open PowerShell or Command Prompt on the target laptop and navigate into the extracted folder:
   ```powershell
   cd C:\smart_home_IOT_simulation
   ```
4. Install the required dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Launch the application:
   ```powershell
   python smart_home_lights.py --gui
   ```

---

## 📁 Project File Structure

```
smart_home_IOT_simulation/
├── smart_home_lights.py    # Main application source code (GUI & CLI)
├── requirements.txt        # Third-party dependency list (rich)
├── README.md               # Project documentation and setup guide
└── lights_state.json       # Generated JSON state export file
```

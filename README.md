🧮 P1Nky$ W0rk & P@y 4.0 – Your smart Work & Pay Tracker

About the Project
P1Nky$ W0rk & P@y 4.0 is an offline desktop application for managing work hours, wages, and user profiles. Built with Python 3 / PySide6, it’s fully self-contained and ensures maximum privacy and simplicity — ideal for workplaces, rehabilitation, or correctional environments without internet access.

⚙️ Core Features

•	📅 Calendar view (daily, weekly, monthly)

•	➕ Fast entry for work / sick / accident hours

•	💰 Payroll preview with vacation / holiday / 13th month pay calculation

•	📊 Export to PDF / Excel / CSV with month in filename

•	🔁 Import CSV with header aliases (date = Datum)

•	🧑‍💼 User Administration

o	Create, edit, delete users

o	Password reset with secure hash

o	Colored buttons & context menus

•	🔒 AES-GCM encryption for sensitive fields

•	🌐 Multi-language support (German / English via languages.py)

•	💾 Works completely offline


🖥️ Requirements
•	OS: Windows 10 / 11

•	Python: ≥ 3.10

•	Dependencies:

•	pip install -r requirements.txt


🚀 Installation

Option 1 – Developer Mode

git clone https://github.com/PinkyZH/P1NkyS-W0rk-Pay.git

cd P1NkyS-W0rk-Pay

python app.py

Option 2 – Stand-alone EXE (PyInstaller)

pyinstaller --noconfirm --windowed ^
  
  --add-data "src/p1nkyw0rkpy/languages.py;p1nkyw0rkpy" ^
  
  --add-data "assets/icons;assets/icons" ^
  
  src/p1nkyw0rkpy/__main__.py

Option 3 – Briefcase Packaging

briefcase create windows

briefcase build windows

briefcase run windows

briefcase package windows


🧾 Release Notes (4.0)

•	🔥 Removed: Absence & Notification modules

•	🛡️ Added: AES-GCM encryption for DB fields

•	📅 Added: Payroll preview with quick comparison & month filter

•	📊 Added: Monthly PDF/XLSX/CSV export

•	🎨 Improved: Icons, colors, and context menus

•	🧩 Fixed: User Admin ID offset & password reset


📖 License

Released under the MIT License.


👤 Author
PinkyZH
📧 n/a

🇨🇭 Switzerland
GitHub: github.com/PinkyZH/ 


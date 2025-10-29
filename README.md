# 🧮 P1Nky$ W0rk & P@y 4.0 – Your smart Work & Pay Tracker

**About the Project** <br/>
P1Nky$ W0rk & P@y 4.0 is an offline desktop application for managing work hours, wages, and user profiles. Built with Python 3 / PySide6, it’s fully self-contained and ensures maximum privacy and simplicity — ideal for workplaces, rehabilitation, or correctional environments without internet access.

⚙️ **Core Features** <br/>
•	📅 Calendar view (daily, weekly, monthly)<br/>
•	➕ Fast entry for work / sick / accident hours<br/>
•	💰 Payroll preview with vacation / holiday / 13th month pay calculation<br/>
•	📊 Export to PDF / Excel / CSV with month in filename<br/>
•	🔁 Import CSV with header aliases (date = Datum)<br/>
•	🧑‍💼 User Administration<br/>
o	Create, edit, delete users<br/>
o	Password reset with secure hash<br/>
o	Colored buttons & context menus<br/>
•	🔒 AES-GCM encryption for sensitive fields<br/>
•	🌐 Multi-language support (German / English via languages.py)<br/>
•	💾 Works completely offline<br/>
\
🔐 **Default Login (Important!)** <br/>
After first installation, an administrator account is created automatically:<br/>
`Username: admin`<br/>
`Password: admin`<br/>
`Role: Administrator`<br/>
➡️ **Please change the password immediately after the first login!** <br/>
\
🖥️ **Requirements** <br/>
•	OS: Windows 10 / 11<br/>
•	Python: ≥ 3.10<br/>
•	Dependencies:<br/>
•	`pip install -r requirements.txt`<br/>
\
🚀 **Installation** <br/>
**Option 1** – Developer Mode<br/>
`git clone https://github.com/PinkyZH/P1NkyS-W0rk-Pay.git`<br/>
`cd P1NkyS-W0rk-Pay`<br/>
`python app.py`<br/>
\
**Option 2** – Stand-alone EXE (PyInstaller)<br/>
`pyinstaller --noconfirm --windowed`<br/>
  ` --add-data "src/p1nkyw0rkpy/languages.py;p1nkyw0rkpy" `<br/>
  ` --add-data "assets/icons;assets/icons" `<br/>
  ` src/p1nkyw0rkpy/__main__.py`<br/>
\
**Option 3** – Briefcase Packaging<br/>
` briefcase create windows `<br/>
` briefcase build windows `<br/>
` briefcase run windows `<br/>
` briefcase package windows `<br/>
\
🧾 **Release Notes (4.0)** <br/>
•	🔥 Removed: Absence & Notification modules<br/>
•	🛡️ Added: AES-GCM encryption for DB fields<br/>
•	📅 Added: Payroll preview with quick comparison & month filter<br/>
•	📊 Added: Monthly PDF/XLSX/CSV export<br/>
•	🎨 Improved: Icons, colors, and context menus<br/>
•	🧩 Fixed: User Admin ID offset & password reset<br/>
\
📖 **License** <br/>
Released under the MIT License.<br/>
\
👤 **Author** <br/>
PinkyZH<br/>
📧 n/a<br/>
\
🇨🇭 Switzerland<br/>
**GitHub:** github.com/PinkyZH/ <br/>


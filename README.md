# Maze-Activity #

A simple maze game for the Sugar learning environment.

To Know more about sugar, Please refer to;

* [How to Get Sugar on sugarlabs.org](https://sugarlabs.org/)
* [How to use Sugar](https://help.sugarlabs.org/)

## 🧪 How to run this activity (for WSL users)

If you're using WSL (Windows Subsystem for Linux) on Windows, follow the steps below to run the Maze activity inside Ubuntu.

---

### Steps:

1. Install WSL and Ubuntu  
Open PowerShell as Administrator and run, then restart your PC:

```powershell
wsl --install
```

---

2. Set up Python and GTK inside Ubuntu  
Open Ubuntu and run:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv -y
sudo apt install libgtk-4-dev python3-gi python3-gi-cairo gir1.2-gtk-4.0 -y
```

---

3. Clone this project inside WSL  
Replace `your-username` with your GitHub username and run:

```bash
git clone https://github.com/your-username/maze-activity.git
cd maze-activity
```

---

4. Run the Maze activity  
Inside the project folder, run:

```bash
python3 maze.py
```

---

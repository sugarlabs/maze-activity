# Maze-Activity #

A simple maze game for the Sugar learning environment.

To Know more about sugar, Please refer to;

* [How to Get Sugar on sugarlabs.org](https://sugarlabs.org/)
* [How to use Sugar](https://help.sugarlabs.org/)

## 🧪 How to run this activity (for WSL users)

If you're using WSL (Windows Subsystem for Linux) on Windows, follow the steps below to run the Maze activity inside Ubuntu.  

---
### Steps:
1.install wsl and ubuntu

open PowerShell as Administrator and run, restart your pc:

```powershell
wsl --install

2.set up python and gtk inside ubuntu
# open ubuntu and run:
sudo apt update && sudo apt upgrade -y

sudo apt install python3 python3-pip python3-venv -y

sudo apt install libgtk-4-dev python3-gi python3-gi-cairo gir1.2-gtk-4.0 -y

3.clone this project inside WSL
# replace your-username with your github username and run in ubuntu terminal

git clone https://github.com/your-username/maze-activity.git

cd maze-activity

4.run the maze activity 
#run the following command in terminal:

```bash
python3 maze.py

---
import os
import subprocess
import platform

def win_size(): #does not work yet
    os.system('mode con: cols=80 lines=24')

def clear_screen():
    if platform.system()=="Windows": #clear screen for windows
        subprocess.Popen("cls", shell=True).communicate() 
    else: #clear screen for Linux and Mac
        print("\033c", end="")

if __name__ == '__main__':
    print("Run main.py !!!")
    pass
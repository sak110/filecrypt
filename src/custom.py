import os
import time
import subprocess
import platform
import main
import basic

def win_size(): #does not work yet
    os.system('mode con: cols=80 lines=24')

def clear_screen():
    if platform.system()=="Windows": #clear screen for windows
        subprocess.Popen("cls", shell=True).communicate() 
    else: #clear screen for Linux and Mac
        print("\033c", end="")

def exit_warning():
    print('-------------------------------------WARNING------------------------------------')
    print('----------------------------------EXIT INITIATED--------------------------------')
    for i in range (21):
        print()
    print('Enter n to abort exit', end = ' ')
    choice = input()
    if choice == 'n':
         main.level()
    else:
        exit()

def file_error():
    clear_screen()
    print('---------------------------------------ERROR------------------------------------')
    print('----------------------------------FILE NOT FOUND--------------------------------')
    for i in range (21):
        print()
    print('The entered file does not exist in the current directory',flush = True, end = ' ')
    time.sleep(2)
    

if __name__ == '__main__':
    print("Run main.py !!!")
    pass
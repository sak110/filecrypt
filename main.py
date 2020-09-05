import os
import time
import subprocess
import platform
import basic
import advanced

def win_size(): #does not work yet
    os.system('mode con: cols=80 lines=24')

def basic_mode():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('---------------------------------------BASIC------------------------------------')
    for i in range (19):
        print()
    print('1. Encrypt')
    print('2. Decrypt')
    print('Enter your choice :', end = ' ')
    choice = int(input())
    clear_screen
    loop_control = True
    while(loop_control):
        if choice == 1:
            loop_control = False
            basic.start()
        elif choice == 2:
            loop_control = False
            advanced.start()
        else:
            print("ERROR : Please choose a valid choice")
            time.sleep(2)
            clear_screen()
            basic_mode()


def advanced_mode():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('-------------------------------------ADVANCED-----------------------------------')
    for i in range (22):
        print()

def level():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('--------------------------------------OPTIONS-----------------------------------')
    for i in range (19):
        print()
    print('1. BASIC')
    print('2. ADVANCED')
    print('Enter your choice and press enter :', end = ' ')
    choice = int(input())
    clear_screen
    loop_control = True
    while(loop_control):
        if choice == 1:
            loop_control = False
            basic.start()
        elif choice == 2:
            loop_control = False
            advanced.start()
        else:
            print("ERROR : Please choose a valid option")
            time.sleep(2)
            clear_screen()
            level()

def clear_screen():
    if platform.system()=="Windows": #clear screen for windows
        subprocess.Popen("cls", shell=True).communicate() 
    else: #clear screen for Linux and Mac
        print("\033c", end="")

def welcome():
    #print('--------------------------------------------------------------------------------') window width template
    print('-------------------------------------WELCOME------------------------------------')
    print('---------------------------------TO FILE MANAGER--------------------------------')
    for i in range (21):
        print()
    print('press any key to continue', end = '')
    input()
    clear_screen()
    level()

def main ():
    clear_screen()
    welcome()

if __name__ == '__main__':
    main()


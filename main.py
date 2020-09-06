import time
import basic
import advanced
import custom

def level():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('--------------------------------------OPTIONS-----------------------------------')
    for i in range (18):
        print()
    print('1. BASIC')
    print('2. ADVANCED')
    print('0. EXIT')
    print('Enter your choice and press enter :', end = ' ')
    choice = int(input())
    custom.clear_screen()
    loop_control = True
    while(loop_control):
        if choice == 1:
            loop_control = False
            basic.start()
        elif choice == 2:
            loop_control = False
            advanced.start()
        elif choice == 0:
            loop_control = False
            custom.clear_screen()
            custom.exit_warning()
        else:
            print("ERROR : Please choose a valid option")
            time.sleep(2)
            custom.clear_screen()
            level()

def welcome():
    #print('--------------------------------------------------------------------------------') window width template
    print('-------------------------------------WELCOME------------------------------------')
    print('---------------------------------TO FILE MANAGER--------------------------------')
    for i in range (21):
        print()
    print('press any key to continue', end = '')
    input()
    custom.clear_screen()
    level()

def main ():
    custom.clear_screen()
    welcome()

if __name__ == '__main__':
    main()


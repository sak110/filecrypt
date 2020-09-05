import pyAesCrypt
import time
import custom

def start():
    basic_mode()
    # print('-----------------------------------FILE MANAGER---------------------------------')
    # print('---------------------------------------BASIC------------------------------------')
    # for i in range (22):
    #     print()

def basic_mode():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('---------------------------------------BASIC------------------------------------')
    for i in range (19):
        print()
    print('1. Encrypt')
    print('2. Decrypt')
    print('Enter your choice :', end = ' ')
    choice = int(input())
    custom.clear_screen
    loop_control = True
    while(loop_control):
        if choice == 1:
            loop_control = False
            custom.clear_screen()
            encrypt()
        elif choice == 2:
            loop_control = False
        else:
            print("ERROR : Please choose a valid choice")
            time.sleep(2)
            custom.clear_screen()
            basic_mode()

def encrypt():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('------------------------------------ENCRYPTION----------------------------------')
    for i in range (22):
        print()
    file_name = input('Enter the file name : ', end = '')
    passphrase = input('Enter the passphrase to encrypt the file with : ', end = '')



if __name__ == '__main__':
    print("Run main.py !!!")
    pass
    
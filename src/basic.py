from Crypto.Hash import SHA256
import pyAesCrypt
import time
import os
import custom
import main

choice = 1 #To stop vs from telling that choice is not global

def start():
    basic_mode()

def basic_mode():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('---------------------------------------BASIC------------------------------------')
    for i in range (15):
        print()
    print('1. Encrypt')
    print('2. Encrypt and delete the original file')
    print('3. Decrypt')
    print('4. Decrypt and delete the encrypted file')
    print('9. Back')
    print('0. Exit')
    print('Enter your choice :', end = ' ')
    global choice
    choice = int(input())
    custom.clear_screen
    loop_control = True
    while(loop_control):
        if choice == 1 or choice == 2:
            loop_control = False
            custom.clear_screen()
            encrypt()
        elif choice == 3 or choice == 4:
            loop_control = False
            custom.clear_screen()
            decrypt()
        elif choice == 9:
            loop_control = False
            custom.clear_screen()
            main.level() #fix required
        elif choice == 0:
            loop_control = False
            custom.clear_screen()
            custom.exit_warning()
        else:
            print("ERROR : Please choose a valid choice")
            time.sleep(2)
            custom.clear_screen()
            basic_mode()

def encrypt():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('------------------------------------ENCRYPTION----------------------------------')
    for i in range (18):
        print()
    file_name = input('Enter the file name : ')
    passphrase = input('Enter the passphrase : ')
    bufferSize = 64 * 1024
    output_file_name = file_name + ".aes"
    try :
        with open(file_name, "rb") as input_file:
            with open(output_file_name, "wb") as output_file:
                pyAesCrypt.encryptStream(input_file, output_file, passphrase, bufferSize)
        if choice == 2:
            os.remove(file_name)
        print('Encryption successfull !!!')
        print('Output file : {}'.format(output_file_name))
        time.sleep(3)
        custom.clear_screen()
        basic_mode()
    except FileNotFoundError:
        custom.file_error()
        print()
        start()

def decrypt():
    print('-----------------------------------FILE MANAGER---------------------------------')
    print('------------------------------------DECRYPTION----------------------------------')
    for i in range (18):
        print()
    file_name = input('Enter the file name : ')
    passphrase = input('Enter the passphrase to decrypt the file with : ')
    bufferSize = 64 * 1024
    output_file_name = file_name.replace('.aes', '')
    #output_file_name = file_name - '.aes'
    encrypted_file_size = os.stat(file_name).st_size # get encrypted file size
    try:
        with open(file_name, "rb") as input_file:
            try:
                with open(output_file_name, "wb") as output_file:
                    pyAesCrypt.decryptStream(input_file, output_file, passphrase, bufferSize, encrypted_file_size)
            except ValueError:
                os.remove(output_file_name) # remove output file if its empty
        if choice == 4:
            os.remove(file_name)
        print('Decryption successfull !!!')
        print('Output file : {}'.format(output_file_name))
        time.sleep(3)
        custom.clear_screen()
        basic_mode()
    except FileNotFoundError:
        custom.clear_screen()
        custom.file_error()
        print()
        start()

if __name__ == '__main__':
    print("Run main.py !!!")
    pass
    
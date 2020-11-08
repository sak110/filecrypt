from gooey import Gooey, GooeyParser

@Gooey
def main(auto_start=True):
    parser = GooeyParser(description="My Cool GUI Program!")
    parser.add_argument('Filename', widget="FileChooser")
    parser.add_argument('passphrase', help="key to encrypt the file with")

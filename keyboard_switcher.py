#!/usr/bin/python

import argparse
import errno
import os
import subprocess
from contextlib import contextmanager

VERSION = '0.0.1'
CONFIG_FILE_PATH = '~/.keyboard_switcher/layouts.txt'


class KeyboardLayoutStorage:
    AUTO_PRIORITY = -1
    # Lower means sooner
    MAX_PRIORITY = 0
    X_KEYBOARD_MANAGER = 'xmodmap'

    def __init__(self, name, filepath, priority=AUTO_PRIORITY, active=False):
        self.name = name
        self.filepath = filepath
        if active == 'False':
            self.active = False
        else:
            self.active = bool(active)

        priority = int(priority)

        if priority == KeyboardLayoutStorage.AUTO_PRIORITY:
            self.priority = KeyboardLayoutStorage.MAX_PRIORITY
        else:
            self.priority = int(priority)

        KeyboardLayoutStorage.MAX_PRIORITY = max(
            KeyboardLayoutStorage.MAX_PRIORITY, self.priority + 1)

    def dump_to_string(self):
        return "{} {} {} {}".format(self.name, self.filepath, self.priority, self.active)

    def __str__(self):
        return self.dump_to_string()

    # Apply this keyboard layout to the current X session.
    def apply(self, verbose=False):
        logger('Applying keyboard layout {}'.format(self.name), verbose=verbose)

        fullpath = os.path.expanduser(self.filepath)

        return_code = subprocess.call(
            [KeyboardLayoutStorage.X_KEYBOARD_MANAGER, fullpath])
        if return_code != 0:
            logger('Couldn\'t apply keyboard layout!', verbose=True)

    @staticmethod
    def load_from_string(keyboardLayoutStorageString):
        keyboardLayoutString = keyboardLayoutStorageString.split()
        return KeyboardLayoutStorage(*keyboardLayoutString)


class KeyboardLayoutStorageManager:

    def __init__(self, storageFilePath, autoload=True, verbose=False):
        self.storageFilePath = storageFilePath
        self.verbose = verbose
        self.keyboardLayoutStorages = []

        # To prevent overwriting the storage file!
        if autoload:
            self.load_keyboards_layout()

    def check_and_generate_storage_file(self):
        logger('Checking if storage configuration file exists.',
               verbose=self.verbose)
        os.makedirs(os.path.dirname(self.storageFilePath), exist_ok=True)

        if not os.path.exists(self.storageFilePath):
            logger('File doesn\'t exist! Creating one at {}.'.format(
                self.storageFilePath), verbose=self.verbose)
            with open(self.storageFilePath, 'w'):
                pass

    @contextmanager
    def open_storage_file(self, mode):
        storageFilePath = os.path.expanduser(self.storageFilePath)
        self.check_and_generate_storage_file()

        logger('Loading configuration file.', verbose=self.verbose)
        with open(storageFilePath, mode) as storageFile:
            yield storageFile
        logger('Closing configuration file.', verbose=self.verbose)

    def load_keyboards_layout(self):
        self.keyboardLayoutStorages = []
        with self.open_storage_file('r') as storageFile:
            for keyboardLayoutString in storageFile:
                if keyboardLayoutString != "":
                    self.keyboardLayoutStorages.append(
                        KeyboardLayoutStorage.load_from_string(keyboardLayoutString))

    def dump_keyboards_layout(self):
        with self.open_storage_file('w') as storageFile:
            for keyboardLayoutStorage in self.keyboardLayoutStorages:
                storageFile.write(
                    keyboardLayoutStorage.dump_to_string() + '\n')

    def add_keyboard_layout_storage(self, keyboardLayoutStorage, autodump=True):
        keyboardLayoutIndex = self.get_index_of_keyboard_layout_name(
            keyboardLayoutStorage.name)

        if keyboardLayoutIndex >= 0:
            logger(
                'Can\'t add keyboard layout! Name identifier should be unique.', verbose=True)
            return

        if not self.keyboardLayoutStorages:
            keyboardLayoutStorage.active = True
        self.keyboardLayoutStorages.append(keyboardLayoutStorage)
        if autodump:
            self.dump_keyboards_layout()

    def get_index_of_keyboard_layout_name(self, keyboardLayoutName):
        for i in range(len(self.keyboardLayoutStorages) - 1, -1, -1):
            if self.keyboardLayoutStorages[i].name == keyboardLayoutName:
                return i
        return -1

    def get_keyboard_layout(self, keyboardLayoutName):
        keyboardLayoutIndex = self.get_index_of_keyboard_layout_name(
            keyboardLayoutName)
        if keyboardLayoutIndex >= 0:
            return self.keyboardLayoutStorages[keyboardLayoutIndex]
        return None

    def remove_keyboard_layout(self, keyboardLayoutName, autodump=True):
        keyboardLayoutIndex = self.get_index_of_keyboard_layout_name(
            keyboardLayoutName)

        if keyboardLayoutIndex >= 0:
            logger('Removing keyboard layout {}.'.format(
                keyboardLayoutName), verbose=True)
            if self.keyboardLayoutStorages[keyboardLayoutIndex].active:
                nextKeyboardLayoutIndex = self.get_index_of_next_active_keyboard()
                self.set_active_keyboard(nextKeyboardLayoutIndex)
            del self.keyboardLayoutStorages[keyboardLayoutIndex]
            if autodump:
                self.dump_keyboards_layout()
            return
        logger('Keyboard layout not found.', verbose=True)

    def print_keyboards_layout(self):
        for keyboardLayoutStorage in self.keyboardLayoutStorages:
            logger(keyboardLayoutStorage, verbose=True)

    def purge_keyboards_layout(self, autodump=True):
        self.keyboardLayoutStorages = []
        self.dump_keyboards_layout()

    def get_index_of_active_keyboard_layout(self):
        for index, keyboardLayout in enumerate(self.keyboardLayoutStorages):
            if keyboardLayout.active:
                return index
        if self.keyboardLayoutStorages:
            self.keyboardLayoutStorages[0].active = True
            return 0
        return -1

    def get_index_of_next_active_keyboard(self):
        activeKeyboardLayoutIndex = self.get_index_of_active_keyboard_layout()
        activeKeyboardLayoutPriority = self.keyboardLayoutStorages[
            activeKeyboardLayoutIndex].priority
        nextKeyboardLayoutIndex = (activeKeyboardLayoutIndex + 1) % len(self.keyboardLayoutStorages)

        # On a fait le tour des layouts et on prend celui qui possede la plus basse priorite
        if activeKeyboardLayoutPriority == KeyboardLayoutStorage.MAX_PRIORITY - 1:
            for index, keyboardLayout in enumerate(self.keyboardLayoutStorages):
                if keyboardLayout.priority < self.keyboardLayoutStorages[nextKeyboardLayoutIndex].priority:
                    nextKeyboardLayoutIndex = index
        else:
            if activeKeyboardLayoutIndex >= 0:
                for index, keyboardLayout in enumerate(self.keyboardLayoutStorages):
                    if keyboardLayout.priority > activeKeyboardLayoutPriority and keyboardLayout.priority < self.keyboardLayoutStorages[nextKeyboardLayoutIndex].priority:
                        nextKeyboardLayoutIndex = index

        return nextKeyboardLayoutIndex

    def set_active_keyboard(self, keyboardLayoutIndex):
        activeKeyboardLayoutIndex = self.get_index_of_active_keyboard_layout()
        if activeKeyboardLayoutIndex >= 0:
            self.keyboardLayoutStorages[activeKeyboardLayoutIndex].active = False
            self.keyboardLayoutStorages[keyboardLayoutIndex].active = True

    def set_active_keyboard_by_name(self, keyboardLayoutName):
        keyboardLayoutIndex = self.get_index_of_keyboard_layout_name(
            keyboardLayoutName)
        self.set_active_keyboard(keyboardLayoutIndex)

    def apply_active_keyboard(self):
        activeKeyboardLayoutIndex = self.get_index_of_active_keyboard_layout()
        if activeKeyboardLayoutIndex >= 0:
            self.keyboardLayoutStorages[activeKeyboardLayoutIndex].apply()


def logger(message, verbose=False):
    if verbose:
        print(message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage keyboards layout for X session.',
                                     epilog='To generate a keyboard layout, you can dump your current layout by executing \'xmodmap -pke\' and then edit it.\n\
                                     Made by Pierre Glandon (pglandon78@gmail.com)',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '--version', help='show the current version of %(prog)s', action='version', version=VERSION)
    parser.add_argument(
        '-l', '--list', help='show the list of stored keyboards layout', action='store_true')
    parser.add_argument('-v', '--verbose',
                        help='enable verbose', action='store_true')
    parser.add_argument('-c', '--config', help='specify the config file', nargs='?',
                        const=CONFIG_FILE_PATH, default=CONFIG_FILE_PATH, type=str, metavar='PATH')
    parser.add_argument('-s', '--switch', help='switch to specify keyboard layout',
                        nargs=1, type=str, metavar='LAYOUT NAME')
    parser.add_argument('-a', '--add', help='add a keyboard layout',
                        nargs=2, type=str, metavar=('NAME', 'PATH'))
    parser.add_argument('-p', '--priority', help='specify priority when adding/editing a keyboard layout',
                        nargs=1, default=[str(KeyboardLayoutStorage.AUTO_PRIORITY)], type=str)
    parser.add_argument(
        '-r', '--remove', help='remove specified keyboard layout', nargs=1, metavar='NAME')
    parser.add_argument('-e', '--edit', help='edit layout',
                        nargs=1, metavar='NAME')
    parser.add_argument(
        '-n', '--name', help='change name of layout with -e', nargs=1, metavar='NEW_NAME')
    parser.add_argument('--purge', action='store_true',
                        help='remove all keyboard layouts')

    parser.add_argument('-q', '--autoswitch', help='switch to next priority keyboard', action='store_true')

    # parserDict = vars(parser.parse_args('-q'.split()))
    parserDict = vars(parser.parse_args())

    if parserDict['name'] and not parserDict['edit']:
        logger('You have to specify which layout you want to edit with -e.\nType --help to show the manual.', verbose=True)

    keyboardLayoutStorageManager = KeyboardLayoutStorageManager(
        parserDict['config'], verbose=parserDict['verbose'])


    if parserDict['autoswitch']:
        nextKeyboardLayoutIndex = keyboardLayoutStorageManager.get_index_of_next_active_keyboard()
        keyboardLayoutStorageManager.set_active_keyboard(nextKeyboardLayoutIndex)

    if parserDict['list']:
        keyboardLayoutStorageManager.print_keyboards_layout()

    if parserDict['add']:
        keyboardLayoutString = ' '.join(
            parserDict['add'] + parserDict['priority'])
        keyboardLayoutStorageManager.add_keyboard_layout_storage(
            KeyboardLayoutStorage.load_from_string(keyboardLayoutString))

    if parserDict['switch']:
        keyboardLayoutName = parserDict['switch'][0]
        keyboardLayoutStorageManager.set_active_keyboard(
            keyboardLayoutStorageManager.get_index_of_keyboard_layout_name(keyboardLayoutName))

    if parserDict['remove']:
        keyboardLayoutName = parserDict['remove'][0]
        keyboardLayoutStorageManager.remove_keyboard_layout(keyboardLayoutName)

    if parserDict['purge']:
        keyboardLayoutStorageManager.purge_keyboards_layout()

    keyboardLayoutStorageManager.apply_active_keyboard()
    keyboardLayoutStorageManager.dump_keyboards_layout()

    exit(0)

"""
Author: Xiyuan Yang   xiyuan_yang@outlook.com
Date: 2025-04-11 14:50:06
LastEditors: Xiyuan Yang   xiyuan_yang@outlook.com
LastEditTime: 2025-04-13 11:20:52
FilePath: /Autogen-English-Essay/construct.py
Description:
Do you code and make progress today?
Copyright (c) 2025 by Xiyuan Yang, All Rights Reserved.
"""

# Constructing file structures.

import os
from datetime import *


def read_file(filename="Original.txt"):
    """_summary_ :read file contents, especially for getting the original text

    Args:
        filename (str): file name for the original text
    """
    with open(filename, "r", encoding="utf-8") as file:
        return file.read().strip()


def write_file(content: str, filename="Final.txt"):
    """_summary_ :write file contents, especially for getting the original text

    Args:
        filename (str): file name for the original text
        content (str): contents to be written into
    """
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)


def create_dirs(log_folder: str):
    """_summary_: create the log folder for the settings

    Args:
        log_folder (str): The name of the file folder
    """
    # create the 'log' file folder if it doesn't exist
    if not os.path.exists(log_folder):
        # create new folder
        print("Constructing new folder...")
        os.makedirs(log_folder)
    else:
        print("Constructed already.")

    print("Finish!")


def get_log_filename(log_dir="log") -> str:
    """Generate timestamp-based log filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"log_{timestamp}.txt")


def log_conversation(message: str, log_dir="log"):
    """Record conversation to log file"""
    log_file = get_log_filename(log_dir)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n\n")


def print_progress(message: str):
    """Print progress message and log it"""
    print(f"[PROGRESS] {message}")
    log_conversation(f"[SYSTEM] {message}")


if __name__ == "__main__":
    print("Testing...")
else:
    print("Constructing all files...")

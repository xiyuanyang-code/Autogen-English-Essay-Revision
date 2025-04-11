# Constructing file structures.

import os

# create the 'log' file folder if it doesn't exist
log_folder = "log"
if not os.path.exists(log_folder):
    # create new folder
    print("Constructing new folder...")
    os.makedirs(log_folder)
else:
    print("Constructed already.")

# Finish
print("Done!")
############################
# date: 2025-03-12 00:00 #
# 
# TODO - Initiate OTA, RPC etc.
from micropython import opt_level
from _key_new import HASH_KEY_NEW_ID,HASH_KEY_NEW
opt_level(0)

print("\tboot.py")
print(f"Key{'':<10}:{HASH_KEY_NEW[0:8]}")
print(f"Key-ID{'':>7}:{HASH_KEY_NEW_ID}")

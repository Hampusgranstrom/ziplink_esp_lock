############################
# date: 2025-02-25 00:00 #
#
import time
print('\tmain.py')
print('\nBooting using 1sec delay:',end='')

try:
    time.sleep(1)
    print('0\nLoading esp32_elock.py')
    from esp32_elock import *
except KeyboardInterrupt as k:
    print('Abort boot...')
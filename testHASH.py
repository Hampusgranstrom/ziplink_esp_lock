############################
# date: 2025-03-11 00:00 #
#
from config import NVS_ACTIVE
from micropython import const

def calcHashes(_str)-> tuple((str|str)): # TODO: Optimize import/mem
    from elock_hmac_sha256 import hmac_sha256
    from binascii import b2a_base64
    from config import HASH_KEY,HASH_KEY_NEW
    _hash: str = b2a_base64(hmac_sha256(HASH_KEY, _str)).decode().strip('\r\n')
    _hash_new: str =b2a_base64(hmac_sha256(HASH_KEY_NEW, _str)).decode().strip('\r\n')
    del hmac_sha256,HASH_KEY,HASH_KEY_NEW
    return tuple((_hash,_hash_new))

# Move to utils?
# TODO - Move to utils.
def safePrint(_s:str,_rep:str="_")->str: # TODO: Optimize
    if not isinstance(_s,str): return ""
    _safe:str= const("""!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ""")
    
    _res:str=""
    for _ in enumerate(_s):
        _l=_s[_[0]] in _safe
        _res+=_s[_[0]] if _l else _rep
    return _res

async def hashTest(_hash,_str) -> bool:
#     _pstr="".join[chr(x) for x in ] # Listcomprehension with logic???

    print("Check keys:",safePrint(_str))
    safePrint(_hash)
    _rehash,_rehash_new = calcHashes(_str)
#     print("\n",_rehash,"\n",_rehash_new)
#     print()
    _old = (_hash == _rehash)
    _new = (_hash == _rehash_new)

    # TODO - Expand logic to "try" prevent power/time/ghost \
    #                         attacks (in python... *slap*)
#     print("Compute logic:", end=" ")
#     print(f"old{_old} - new{_new}")
    if not _old and not _new:
        print("No match!")
        return False
    print("MATCH!!!")
    if NVS_ACTIVE:
        from esp32 import NVS
        _old_keys = NVS('oldkey').get_i32('count')

        if _old:     
            if _old_keys<1:
                print("Old Key disabled!")
                return False
            elif _old_keys>0:
                print("This is an old key:\n",_old_keys, end=' ')
                return True
        elif _new:
            if _old_keys>=1:
                print("This is a new key",end=' ')
                NVS('oldkey').set_i32('count',_old_keys-1)
                NVS('oldkey').commit()
                print(NVS('oldkey').get_i32('count')," keys left!")
                print("Update keycount")
        return True
    else:
        print(">> NVS INACTIVE")
        return True
    return False

    # Do a softReset?
    from utime import sleep
    while True:
        print("SERIUS ERROR!!!", end='>>')
        sleep(1)
    return False

def setKeys(_knum:int):
    from esp32 import NVS
    NVS('oldkey').set_i32('count',_knum); NVS('oldkey').commit()
    del NVS     
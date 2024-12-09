gold and exp farming timer script for brawlhalla patch 9.01 [(download)](https://github.com/phruut/prawl/releases/lateset)\
please see the [wiki](https://github.com/phruut/prawl/wiki) for more information about the script\
discord server: https://discord.gg/2HDmuqqq9p

## important
add this steam startup option
```
-noeac
```
> [!caution]
> please **always** use `-noeac` option before using the script to avoid the risk of any bans, although it is highly unlikely\
> i am also not responsible for anything that happens to your account

## features
- launch brawlhalla from script (+auto launch on script start option)
- set custom configuration values for timing adjustments and script behavior
- auto start matches, also configurable
- show/hide brawlhalla window
- runs in the background (no interruption as it directly sends inputs only to the brawlhalla window)
- exp rate limit detection (starts again after waiting for the rate limit to reset)
- very light weight and minimal dependencies as it is basically only a timer script

## download
you can find the compiled script in the latest releases, or [directly download file]()
> [!warning]
> your anti-virus may flag this executable as a threat, as it interacts with Win32 API for sending key inputs in the background

## manual install
```bash
git clone https://github.com/
```
```bash
cd prawl
```
```Pip Requirements
python -m pip install -r requirements.txt
```
and then you can run it
```bash
python main.py
```

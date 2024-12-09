gold and exp farming timer script for brawlhalla patch 9.01

## brawlhalla startup options
```
-noeac
```
> [!caution]
> please **always** use `-noeac` option before using the script to avoid the risk of any bans, although it is highly unlikely

## features
- launch brawlhalla from script (+auto launch on script start option)
- set custom configuration values for timing adjustments and script behavior
- auto start matches, also configureable
- show/hide brawlhalla window
- runs in the background (no interruption as it directly sends inputs only to the brawlhalla window)
- exp rate limit detection (starts again after waiting for the rate limit to reset)

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
> [!note]
> i only tested it with python 3.11.9 on windows lol

and then you can run it
```bash
python main.py
```

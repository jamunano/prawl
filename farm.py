import os
import ast
import time
import threading
import random
import winsound
import win32api
import win32con
import win32gui
import webbrowser
import subprocess
import dearpygui.dearpygui as dpg

# global vars cuz im lazy yippee
HWND = win32gui.FindWindow(None, 'Brawlhalla')
TOTAL_GAMES = 0
TOTAL_EXP = 0
CURRENT_EXP = 0

# timer thingy
class Timer:
    def __init__(self):
        self.initial_time = 0
        self.remaining_time = 0
        self.waiting_time = 2700 # 45 minutes
        self.running = False
        self.paused = False
        self.pressing = False
        self.menu_mode = 1
        self._timer_thread = None

    def start(self, minutes):
        if self.running:
            dpg.configure_item('farm_status', default_value='already active', color=(187, 98, 110))
            return
        self.initial_time = minutes * 60
        self.remaining_time = self.initial_time
        self.running = True
        self.paused = False
        self._timer_thread = threading.Thread(target=self._run)
        self._timer_thread.start()

    def stop(self):
        self.running = False
        if self._timer_thread is not None:
            self._timer_thread.join()
        dpg.configure_item('farm_status', default_value='inactive', color=(100, 149, 238))

    def pause(self):
        if self.running:
            self.paused = not self.paused
            status = 'paused' if self.paused else 'resumed'
            dpg.configure_item('farm_status', default_value=f'{status}', color=(187, 98, 110))

    def _run(self):
        global TOTAL_GAMES, TOTAL_EXP, CURRENT_EXP
        while self.running:
            self.pressing = True
            sequence = ['wait_restart', 'spam_menu', 'open_menu', 'disconnect', 'reconnect']
            if dpg.get_value('open_menu_hold'):
                sequence = ['open_menu_hold' if item == 'open_menu' else item for item in sequence]
            if dpg.get_value('open_menu_fix'):
                sequence = ['open_menu_fix' if item == 'open_menu' else item for item in sequence]
            if dpg.get_value('open_menu_fix2'):
                sequence = [sub for item in sequence for sub in (['open_menu_fix', 'open_menu_fix'] if item == 'open_menu' else [item])]
            self.key_sequence(sequence)
            self.pressing = False
            while self.remaining_time > 0 and self.running:
                if self.paused:
                    while self.paused and self.running:
                        time.sleep(1)
                    continue
                mins, secs = divmod(self.remaining_time, 60)
                dpg.configure_item('farm_status', default_value=f'active ({mins}:{secs:02})', color=(207, 104, 225))
                time.sleep(1)
                self.remaining_time -= 1

            if self.remaining_time == 0 and self.running:
                if dpg.get_value('timer_sound'):
                    winsound.Beep(dpg.get_value('beep_frequency'), dpg.get_value('beep_duration'))
                TOTAL_GAMES += 1
                TOTAL_EXP += calculate_exp((self.initial_time/60))
                dpg.set_value('total_games', f'games: {TOTAL_GAMES},')
                dpg.set_value('total_exp', f'exp: {TOTAL_EXP}')

                # rate limit
                CURRENT_EXP += calculate_exp((self.initial_time/60))
                if dpg.get_value('exp_detect') and CURRENT_EXP >= 13000:
                    dpg.configure_item('farm_status', default_value='exp rate limit...', color=(187, 98, 110))
                    if dpg.get_value('exp_wait'):
                        self.remaining_time = self.waiting_time
                        while self.remaining_time > 0 and self.running:
                            mins, secs = divmod(self.remaining_time, 60)
                            dpg.configure_item('farm_status', default_value=f'exp rate limit reset in {mins}:{secs:02}', color=(187, 98, 110))
                            time.sleep(1)
                            self.remaining_time -= 1
                        CURRENT_EXP = 0
                        self.waiting = False
                    else:
                        self.stop
                        return
                self.remaining_time = self.initial_time

                # max games
                if dpg.get_value('max_games') and TOTAL_GAMES >= dpg.get_value('max_games_amount'):
                    dpg.configure_item('farm_status', default_value='max games reached...', color=(187, 98, 110))
                    self.stop
                    return

    # this does the restarting part ye
    def key_sequence(self, sequences):
        global HWND
        
        ACTION_MAP = {
            # waits before starting game
            'wait_restart': [
                *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'starting game in {dpg.get_value("wait_restart")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_restart')) ),
            ],
            # spams through the results screen and chooese the same legend and starts game
            'spam_menu': [
                (lambda: dpg.configure_item('farm_status', default_value='spamming through menu!', color=(207, 104, 225)), 0),
                *( (lambda: keypress(HWND, 'c'), 0) for _ in range(dpg.get_value('start_spam')) ),
                *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'waiting for game {dpg.get_value("wait_gameload")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_gameload')) ),
            ],
            # open menu, waits
            'open_menu': [
                (lambda: dpg.configure_item('farm_status', default_value='open esc menu', color=(207, 104, 225)), 0),
                *( (lambda: keypress(HWND, win32con.VK_ESCAPE), dpg.get_value('esc_presses_delay')) for _ in range(dpg.get_value('esc_presses')) ),
            ],
            # disconnects from game
            'disconnect': [
                (lambda: dpg.configure_item('farm_status', default_value='wait disconnect delay', color=(187, 98, 110)), dpg.get_value('wait_disconnect')),
                (lambda: keypress(HWND, win32con.VK_UP), 0),
                (lambda: keypress(HWND, 'c'), 0),
            ],
            # reconnects to game
            'reconnect': [
                *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'reconnecting in {dpg.get_value("wait_reconnect")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_reconnect')) ),
                (lambda: dpg.configure_item('farm_status', default_value='pressing...', color=(207, 104, 225)), 0),
                (lambda: keypress(HWND, 'c', 2), 0)
            ],

            # temporary fix for people having issues disconnecting from the match (game ignoring esc press after second match)
            # this quickly opens esc menu again and clicks disconnect if it hasnt already
            # this wont matter if the script successfully disconnected from the match the first time because it happens during the transition from in-game to title screen
            'open_menu_fix': [
                (lambda: dpg.configure_item('farm_status', default_value='esc menu fix...', color=(207, 104, 225)), 0),
                (lambda: keypress(HWND, win32con.VK_ESCAPE), 0),
                (lambda: keypress(HWND, win32con.VK_UP), 0),
                (lambda: keypress(HWND, 'c'), 0)
            ],

            # (must have HOLD TO PAUSE option enabled in brawlhalla settings)
            'open_menu_hold': [
                (lambda: dpg.configure_item('farm_status', default_value='open esc menu (hold)', color=(207, 104, 225)), 0),
                (lambda: keypress(HWND, win32con.VK_ESCAPE, 3), 0),
                (lambda: keypress(HWND, win32con.VK_ESCAPE, hold=[2.00,2.50]), 0),
            ]
        }
        actions = []
        for sequence in sequences:
            if sequence in ACTION_MAP:
                actions.extend(ACTION_MAP[sequence])

        for action, delay in actions:
            if not self.running:
                break
            action()
            if delay >= 1: # i split this so you can stop after 1 second checks if you pressed the stop button or not :3
                for _ in range(int(delay)):
                    if not self.running:
                        break
                    time.sleep(1)
            else:
                time.sleep(delay)

# keypress simulation
def keypress(hwnd, key, times=1, hold=[0.06, 0.09]):
    if isinstance(key, str):
        k = win32api.VkKeyScan(key)
    else:
        k = key
    while times > 0:
        times -= 1
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, k, 0)
        time.sleep(random.uniform(hold[0],hold[1]))
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, k, 0)
        time.sleep(random.uniform(0.15, 0.19))

# exp calculate
def calculate_exp(time):
    return (time / 25) * 1000

# set timer
timer = Timer()

# dpg stuff
def _hyperlink(text, address):
    b = dpg.add_button(label=text, callback=lambda:webbrowser.open(address))
    dpg.bind_item_theme(b, "__hyperlinkTheme")

# calculate exp on slider
def update_exp():
    estimated_exp = calculate_exp(dpg.get_value('match_time'))
    dpg.set_value('estimated_exp', f'estimated exp: {int(estimated_exp)}')

# always on top check thing
def update_aot():
    dpg.set_viewport_always_top(dpg.get_value('always_on_top'))

# checks if brawl is running lol
def brawlhalla_running():
    global HWND
    HWND = win32gui.FindWindow(None, 'Brawlhalla')
    return True if HWND else False

# button callbacks
def start_callback():
    if brawlhalla_running():
        timer.start(dpg.get_value('match_time'))
    else:
        dpg.configure_item('farm_status', default_value='brawlhalla window not found', color=(187, 98, 110))

def stop_callback():
    dpg.configure_item('farm_status', default_value='stopping...', color=(187, 98, 110))
    timer.stop()

def oops_callback():
    if timer.running and not timer.pressing:
        timer.pause()
        sequence = ['open_menu', 'disconnect', 'reconnect']
        if dpg.get_value('open_menu_hold'):
            sequence = ['open_menu_hold' if item == 'open_menu' else item for item in sequence]
        timer.key_sequence(sequence)
        timer.pause()

def toggle_callback():
    global HWND
    if brawlhalla_running():
        if win32gui.IsWindowVisible(HWND):
            win32gui.ShowWindow(HWND, win32con.SW_HIDE)
            dpg.configure_item('farm_status', default_value='brawlhalla window hidden', color=(187, 98, 110))
            dpg.configure_item('toggle_button_label', default_value='show brawlhalla window')
            dpg.configure_item('toggle_button', label='show')
        else:
            win32gui.ShowWindow(HWND, win32con.SW_SHOW)
            dpg.configure_item('farm_status', default_value='brawlhalla window shown', color=(100, 149, 238))
            dpg.configure_item('toggle_button_label', default_value='hide brawlhalla window')
            dpg.configure_item('toggle_button', label='hide')
    else:
        dpg.configure_item('farm_status', default_value='brawlhalla window not found', color=(187, 98, 110))

def launch_callback():
    if brawlhalla_running():
        dpg.configure_item('farm_status', default_value='already running', color=(187, 98, 110))
    else:
        subprocess.run('cmd /c start steam://rungameid/291550')
        dpg.configure_item('farm_status', default_value='starting brawlhalla...', color=(100, 149, 238))

# configuration thingies
def config_read():
    default_config = {
        'match_time': 25,
        'timer_sound': False,
        'always_on_top': False,
        'game_start_spam': 10,
        'game_restart_delay': 4,
        'game_load_time': 15,
        'esc_presses': 2,
        'esc_presses_delay': 0,
        'disconnect_delay': 0.1,
        'reconnect_delay': 4,
        'open_menu_default': True,
        'open_menu_fix': False,
        'open_menu_fix2': False,
        'open_menu_hold': False,
        'beep_frequency': 500,
        'beep_duration': 72,
        'exp_detect': False,
        'exp_wait': False,
        'max_games': False,
        'max_games_amount': 16,
        'auto_launch': False
    }

    config = {}

    # if config not exist
    if not os.path.exists('config.ini'):
        with open('config.ini', 'w') as c:
            for key, value in default_config.items():
                c.write(f'{key}={value}\n')
        config = default_config
    else:
        # load existing config
        with open('config.ini', 'r') as c:
            lines = c.readlines()
            for line in lines:
                key, value = line.strip().split('=')
                try:
                    config[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    config[key] = value

        # add missing keys from default config cuz well idk why i did this aaaaaaaaaaa
        updated = False
        with open('config.ini', 'a') as c:
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    c.write(f'{key}={value}\n')
                    updated = True
        if updated:
            with open('config.ini', 'r') as c:
                lines = c.readlines()
                config = {}
                for line in lines:
                    key, value = line.strip().split('=')
                    try:
                        config[key] = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        config[key] = value

    return config

def config_write():
    config = {
        'match_time': dpg.get_value('match_time'),
        'timer_sound': dpg.get_value('timer_sound'),
        'always_on_top': dpg.get_value('always_on_top'),
        'game_start_spam': dpg.get_value('start_spam'),
        'game_restart_delay': dpg.get_value('wait_restart'),
        'game_load_time': dpg.get_value('wait_gameload'),
        'esc_presses': dpg.get_value('esc_presses'),
        'esc_presses_delay': dpg.get_value('esc_presses_delay'),
        'disconnect_delay': dpg.get_value('wait_disconnect'),
        'reconnect_delay': dpg.get_value('wait_reconnect'),
        'open_menu_default': dpg.get_value('open_menu_default'),
        'open_menu_fix': dpg.get_value('open_menu_fix'),
        'open_menu_fix2': dpg.get_value('open_menu_fix2'),
        'open_menu_hold': dpg.get_value('open_menu_hold'),
        'beep_frequency': dpg.get_value('beep_frequency'),
        'beep_duration': dpg.get_value('beep_duration'),
        'exp_detect': dpg.get_value('exp_detect'),
        'exp_wait': dpg.get_value('exp_wait'),
        'max_games': dpg.get_value('max_games'),
        'max_games_amount': dpg.get_value('max_games_amount'),
        'auto_launch': dpg.get_value('auto_launch')
    }
    with open('config.ini', 'w') as c:
        for key, value in config.items():
            c.write(f'{key}={value}\n')

def select_open_menu_default():
    if not dpg.get_value('open_menu_default'):
        dpg.set_value('open_menu_default', True)
    else:
        dpg.configure_item('open_menu_fix', enabled=True)
        dpg.configure_item('open_menu_fix2', enabled=True)

    dpg.configure_item('esc_presses', show=True)
    dpg.configure_item('esc_presses_delay', show=True)
    dpg.configure_item('esc_presses_text', show=True)
    dpg.configure_item('esc_presses_delay_text', show=True)
    dpg.set_value('open_menu_hold', False)

def select_open_menu_fix():
    if dpg.get_value('open_menu_fix2'):
        dpg.set_value('open_menu_fix2', False)

def select_open_menu_fix2():
    if dpg.get_value('open_menu_fix'):
        dpg.set_value('open_menu_fix', False)

def select_open_menu_hold():
    if not dpg.get_value('open_menu_hold'):
        dpg.set_value('open_menu_hold', True)
    dpg.configure_item('open_menu_fix', enabled=False)
    dpg.configure_item('open_menu_fix2', enabled=False)
    dpg.configure_item('esc_presses', show=False)
    dpg.configure_item('esc_presses_delay', show=False)
    dpg.configure_item('esc_presses_text', show=False)
    dpg.configure_item('esc_presses_delay_text', show=False)
    dpg.set_value('open_menu_default', False)
    dpg.set_value('open_menu_fix', False)

def timing_reset():
    dpg.configure_item('__reset_popup', show=False)
    dpg.set_value('start_spam', 10)
    dpg.set_value('wait_restart', 4)
    dpg.set_value('wait_gameload', 15)

    dpg.set_value('esc_presses', 2)
    dpg.set_value('esc_presses_delay', 0)
    dpg.set_value('wait_disconnect', 0.1)
    dpg.set_value('wait_reconnect', 4)

def beep_sound():
    winsound.Beep(dpg.get_value('beep_frequency'), dpg.get_value('beep_duration'))
def beep_reset():
    dpg.set_value('beep_frequency', 500)
    dpg.set_value('beep_duration', 72)

# context thing
dpg.create_context()

with dpg.theme(tag="__hyperlinkTheme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [29, 151, 236, 25])
        dpg.add_theme_color(dpg.mvThemeCol_Text, [100, 149, 238])

# make window
with dpg.window(tag='main'):
    config = config_read()
    with dpg.tab_bar():
        with dpg.tab(label='main'):
            dpg.add_text('match time')
            dpg.add_slider_int(label='minutes', min_value=1, max_value=25, default_value=int(config['match_time']), tag='match_time', callback=update_exp)
            dpg.add_text('estimated exp: 1000', tag='estimated_exp')
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('you may get more or less exp')
            dpg.add_spacer(height=2)

            with dpg.group(horizontal=True):
                dpg.add_checkbox(label='timer sound', tag='timer_sound', default_value=bool(config['timer_sound']))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('beep boop noise')
                dpg.add_checkbox(label='always on top', tag='always_on_top', default_value=bool(config['always_on_top']), callback=update_aot)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('makes window stay on top')
            dpg.add_spacer(height=2)

            with dpg.group(horizontal=True):
                dpg.add_button(label='start', callback=start_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('starts farming (no setup)')
                dpg.add_button(label='stop', callback=stop_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('stops script, resets timer')
                dpg.add_button(label='oops', callback=oops_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('disconnects and reconnects again')
                dpg.add_button(label='hide', tag='toggle_button', callback=toggle_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('hide brawlhalla window', tag='toggle_button_label')
                dpg.add_button(label='launch', callback=launch_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('starts brawlhalla from steam')

            with dpg.group(horizontal=True):
                dpg.add_text(f'matches: {TOTAL_GAMES},', tag='total_games')
                dpg.add_text(f'exp: {TOTAL_EXP}', tag='total_exp')

            with dpg.group(horizontal=True):
                dpg.add_text('status:')
                dpg.add_text('inactive', color=(100, 149, 238), tag='farm_status')

        with dpg.tab(label='config'):

            # timings collapse
            with dpg.collapsing_header(label='timings'):

                dpg.add_spacer(height=2)
                with dpg.tree_node(label='starting / restarting'):
                    dpg.add_spacer(height=2)
                    dpg.add_text('spam amount')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('amount to press when spamming through menu', wrap=260)
                    dpg.add_slider_int(label='presses', min_value=0, max_value=30, default_value=int(config['game_start_spam']), tag='start_spam'),
                    dpg.add_text('match restart delay')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('duration to wait before spamming through the menu to start another game', wrap=260)
                    dpg.add_slider_int(label='seconds', min_value=0, max_value=30, default_value=int(config['game_restart_delay']), tag='wait_restart'),
                    dpg.add_text('match load time')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('duration to wait for the match to start (waiting for the match to load)', wrap=260)
                    dpg.add_slider_int(label='seconds', min_value=5, max_value=30, default_value=int(config['game_load_time']), tag='wait_gameload')

                dpg.add_spacer(height=2)
                with dpg.tree_node(label='disconnect / reconnect'):
                    dpg.add_spacer(height=2)
                    dpg.add_text('mode')
                    dpg.add_checkbox(label='default', tag='open_menu_default', default_value=bool(config['open_menu_default']), callback=select_open_menu_default)
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('the default method of opening the esc menu', wrap=260)
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(label='+fix', tag='open_menu_fix', default_value=bool(config['open_menu_fix']), callback=select_open_menu_fix)
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text('the default method + an extra step for trying to fix the "doesnt open menu after the first game bug" lol', wrap=260)
                        dpg.add_checkbox(label='+fix2', tag='open_menu_fix2', default_value=bool(config['open_menu_fix2']), callback=select_open_menu_fix2)
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text('does the fix TWICE... for good measure i guess? i personally wouldnt recommend, if you want to experiment go ahead', wrap=260)
                    dpg.add_checkbox(label='hold to pause', tag='open_menu_hold', default_value=bool(config['open_menu_hold']), callback=select_open_menu_hold)
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('this didnt work for me, but feel free to try it. if it works after 2+ matches, definitely use this instead as its more consistent\n\nOPTIONS -> SYSTEM SETTINGS ->\nHOLD TO PAUSE: ENABLED', wrap=260)
                    dpg.add_spacer(height=2)
                    dpg.add_text('esc presses', tag='esc_presses_text')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('the amount of times to press the esc button to open the menu, default is 2 because it doesnt open the first press for some reason', wrap=260)
                    dpg.add_slider_int(label='times', min_value=1, max_value=6, default_value=int(config['esc_presses']), tag='esc_presses')
                    dpg.add_text('esc presses delay', tag='esc_presses_delay_text')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('the time to wait between each esc press', wrap=260)
                    dpg.add_slider_float(label='seconds', min_value=0, max_value=1, default_value=float(config['esc_presses_delay']), tag='esc_presses_delay')
                    dpg.add_text('disconnect delay')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('duration to wait before clicking the disconnect button after opening menu', wrap=260)
                    dpg.add_slider_float(label='seconds', min_value=0.1, max_value=1, default_value=float(config['disconnect_delay']), tag='wait_disconnect')
                    dpg.add_text('reconnect delay')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('duration to wait for the game to return to the title screen and reconnect menu to appear', wrap=260)
                    dpg.add_slider_int(label='seconds', min_value=3, max_value=20, default_value=int(config['reconnect_delay']), tag='wait_reconnect')

                # reset timings button
                dpg.add_spacer(height=2)
                dpg.add_button(label='reset')
                with dpg.popup(dpg.last_item(), modal=True, mousebutton=dpg.mvMouseButton_Left, tag='__reset_popup', no_move=True):
                    dpg.add_text('all the "timings" settings will be reset', wrap=260)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="reset", width=75, callback=timing_reset)
                        dpg.add_button(label="cancel", width=75, callback=lambda: dpg.configure_item('__reset_popup', show=False))
                dpg.add_spacer(height=2)

            # beep sound collapse
            with dpg.collapsing_header(label='boop beep?'):
                dpg.add_text('beep frequency')
                dpg.add_slider_int(label='hz', min_value=100, max_value=2000, default_value=int(config['beep_frequency']), tag='beep_frequency')
                dpg.add_text('beep duration')
                dpg.add_slider_int(label='ms', min_value=10, max_value=1000, default_value=int(config['beep_duration']), tag='beep_duration')
                dpg.add_spacer(height=2)
                with dpg.group(horizontal=True):
                    dpg.add_button(label='beep', callback=beep_sound)
                    dpg.add_button(label='reset', callback=beep_reset)

            # other collapse
            with dpg.collapsing_header(label='other'):
                dpg.add_spacer(height=2)
                dpg.add_checkbox(label='launch brawlhalla on script start', tag='auto_launch', default_value=bool(config['auto_launch']))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('automatically starts brawlhalla (if not running already) when running this script', wrap=260)
                dpg.add_checkbox(label='exp rate limit detection', tag='exp_detect', default_value=bool(config['exp_detect']))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('stops farming after reaching 13000 exp', wrap=260)
                dpg.add_checkbox(label='auto wait', tag='exp_wait', default_value=bool(config['exp_wait']))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('automatically starts farming after waiting for rate limit to reset', wrap=260)
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label='', tag='max_games', default_value=bool(config['max_games']))
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('stops after playing x matches', wrap=260)
                    dpg.add_slider_int(label='games', min_value=1, max_value=99, default_value=int(config['max_games_amount']), tag='max_games_amount')

        with dpg.tab(label='help'):
            with dpg.collapsing_header(label='instructions',default_open=True):
                dpg.add_text('this script is for super dummies')
                dpg.add_spacer(height=2)
                with dpg.tree_node(label='GAME RULE'):
                    dpg.add_text('create a private custom lobby', bullet=True)
                    dpg.add_text('game mode: crew battle', bullet=True)
                    dpg.add_text('stocks: 99', bullet=True)
                    dpg.add_text('match time: 25 minutes', bullet=True)
                    dpg.add_text('mapset: (tournament) 1v1', bullet=True)
                    dpg.add_text('max players: 2', bullet=True)
                dpg.add_spacer(height=2)
                with dpg.tree_node(label='LOBBY'):
                    dpg.add_text('map selection: random', bullet=True)
                    dpg.add_text('disable friend/clan join', bullet=True)
                    dpg.add_text('choose legend, dont start game', bullet=True)
                    dpg.add_text('press start button', bullet=True)
                dpg.add_spacer(height=2)
            with dpg.collapsing_header(label='faq'):
                dpg.add_spacer(height=2)
                with dpg.tree_node(label='why crew battle?'):
                    dpg.add_text('because it has 25 minute game option and the less time you spend in game menus, the more exp youre gonna get (i think lol)', wrap=0)
                    _hyperlink('- me 05/17/2024', 'https://discord.com/channels/829496409681297409/1240709211642527824/1240710940140503170')
                    dpg.add_text('xp and gold requires active participation and different modes calculate participation differently so bot is too dumb for ffa basically, because ffa requires actually doing damage and kills', wrap=0)
                    _hyperlink('- sovamorco 10/08/2023', 'https://discord.com/channels/829496409681297409/829503904190431273/1160557662145097898')
                dpg.add_spacer(height=2)
                with dpg.tree_node(label='exp rate limit'):
                    dpg.add_text('Around 5 hours or once you earn around 13000 XP, you have to stop farming for about 45-50 minutes to reset the XP limit.', wrap=0)
                    _hyperlink('- jeffriesuave 10/16/2023', 'https://discord.com/channels/829496409681297409/829503904190431273/1163246039197831198')
                    dpg.add_text('*there are other reports saying you only have to wait 30 minutes. the wait time is 45 minutes for exp rate limit detection option in the config', wrap=0)

    # auto launch
    if config['auto_launch']:
        launch_callback()

# setup and start
dpg.create_viewport(title='simple bhbot 11-13', width=300, height=200)
dpg.set_viewport_always_top(dpg.get_value('always_on_top'))
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window('main', True)
dpg.start_dearpygui()
config_write() # saves any changes before closing
dpg.destroy_context()

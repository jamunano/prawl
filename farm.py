import os
import time
import threading
import random
import winsound
import win32api
import win32con
import win32gui
import dearpygui.dearpygui as dpg

# global vars cuz im lazy yippee
hwnd = win32gui.FindWindow(None, 'Brawlhalla')
total_games = 0

# timer thingy
class Timer:
    def __init__(self):
        self.initial_time = 0
        self.remaining_time = 0
        self.running = False
        self._timer_thread = None

    def start(self, minutes):
        if self.running:
            dpg.configure_item('farm_status', default_value='already active', color=(187, 98, 110))
            return
        self.initial_time = minutes * 60
        self.remaining_time = self.initial_time
        self.running = True
        self._timer_thread = threading.Thread(target=self._run)
        self._timer_thread.start()

    def _run(self):
        global total_games
        while self.running:
            self.start_sequence()
            while self.remaining_time > 0 and self.running:
                mins, secs = divmod(self.remaining_time, 60)
                dpg.configure_item('farm_status', default_value=f'active ({mins}:{secs:02})', color=(207, 104, 225))
                time.sleep(1)
                self.remaining_time -= 1

            if self.remaining_time == 0 and self.running:
                if dpg.get_value('timer_sound'):
                    winsound.Beep(dpg.get_value('beep_frequency'), dpg.get_value('beep_duration'))
                total_games += 1
                dpg.set_value('total_games', f'total games: {total_games}')
                self.remaining_time = self.initial_time
                if dpg.get_value('max_games') and total_games >= dpg.get_value('max_games_amount'):
                    dpg.configure_item('farm_status', default_value='max games reached...', color=(187, 98, 110))
                    self.stop
                    return
                if dpg.get_value('stop_farm'):
                    local_time = time.localtime()
                    stop_time = dpg.get_value('stop_farm_time')
                    if local_time.tm_hour >= stop_time['hour'] and local_time.tm_min >= stop_time['min']:
                        dpg.configure_item('farm_status', default_value='over time...', color=(187, 98, 110))
                        self.stop
                        return

    # this does the restarting part ye
    def start_sequence(self):
        actions = [
            # waits before starting game
            *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'starting game in {dpg.get_value("wait_restart")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_restart')) ),

            # spams through the results screen and chooese the same legend and starts game
            (lambda: dpg.configure_item('farm_status', default_value='spamming through menu!', color=(207, 104, 225)), 0),
            *( (lambda: keypress(hwnd, 'c'), 0) for _ in range(10) ),
            *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'waiting for game... {dpg.get_value("wait_gameload")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_gameload')) ),

            # open menu, waits
            (lambda: dpg.configure_item('farm_status', default_value='open esc menu', color=(207, 104, 225)), 0),
            (lambda: keypress(hwnd, win32con.VK_ESCAPE, 2), dpg.get_value('wait_disconnect')),

            # disconnect
            (lambda: dpg.configure_item('farm_status', default_value='wait disconnect delay', color=(187, 98, 110)), dpg.get_value('wait_disconnect')),
            (lambda: keypress(hwnd, win32con.VK_UP), 0),
            (lambda: keypress(hwnd, 'c'), 0),

            # reconnect
            *( (lambda i=i: dpg.configure_item('farm_status', default_value=f'reconnecting in {dpg.get_value("wait_reconnect")-i}...', color=(187, 98, 110)), 1) for i in range(dpg.get_value('wait_reconnect')) ),
            (lambda: dpg.configure_item('farm_status', default_value='pressing...', color=(207, 104, 225)), 0),
            (lambda: keypress(hwnd, 'c', 3), 0)
        ]

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

    def stop(self):
        self.running = False
        if self._timer_thread is not None:
            self._timer_thread.join()
        dpg.configure_item('farm_status', default_value='inactive', color=(100, 149, 238))

def keypress(hwnd, key, times=1):
    if isinstance(key, str):
        k = win32api.VkKeyScan(key)
    else:
        k = key
    while times > 0:
        times -= 1
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, k, 0)
        time.sleep(random.uniform(0.05, 0.09))
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, k, 0)
        time.sleep(random.uniform(0.15, 0.19))

# set timer
timer = Timer()

# calculate exp on slider
def update_exp():
    minutes = dpg.get_value('match_time')
    estimated_exp = (minutes / 25) * 1000
    dpg.set_value('estimated_exp', f'estimated exp: {int(estimated_exp)}')

# always on top check thing
def update_aot():
    dpg.set_viewport_always_top(dpg.get_value('always_on_top'))

# button callbacks
def start_callback():
    global hwnd
    if hwnd:
        timer.start(dpg.get_value('match_time'))
    else:
        hwnd = win32gui.FindWindow(None, 'Brawlhalla')
        dpg.configure_item('farm_status', default_value='brawlhalla window not found', color=(187, 98, 110))

def stop_callback():
    dpg.configure_item('farm_status', default_value='stopping...', color=(187, 98, 110))
    timer.stop()

def config_read():
    config = {}
    if not os.path.exists('config.ini'):
        config = {
            'match_time': 25,
            'timer_sound': 0,
            'always_on_top': 0,
            'game_restart_delay': 4,
            'game_load_time': 15,
            'disconnect_delay': 0.1,
            'reconnect_delay': 4,
            'beep_frequency': 500,
            'beep_duration': 72,
            'max_games': 0,
            'max_games_amount': 16
        }
        with open('config.ini', 'w') as c:
            for key, value in config.items():
                c.write(f'{key}={value}\n')
    with open('config.ini', 'r') as c:
        lines = c.readlines()
        for line in lines:
            key, value = line.strip().split('=')
            config[key] = value
    return config

def config_write():
    config = {
        'match_time': dpg.get_value('match_time'),
        'timer_sound': dpg.get_value('timer_sound'),
        'always_on_top': dpg.get_value('always_on_top'),
        'game_restart_delay': dpg.get_value('wait_restart'),
        'game_load_time': dpg.get_value('wait_gameload'),
        'disconnect_delay': dpg.get_value('wait_disconnect'),
        'reconnect_delay': dpg.get_value('wait_reconnect'),
        'beep_frequency': dpg.get_value('beep_frequency'),
        'beep_duration': dpg.get_value('beep_duration'),
        'max_games': dpg.get_value('max_games'),
        'max_games_amount': dpg.get_value('max_games_amount')
    }
    with open('config.ini', 'w') as c:
        for key, value in config.items():
            c.write(f'{key}={value}\n')

def timing_reset():
    dpg.set_value('wait_restart', 4)
    dpg.set_value('wait_gameload', 15)
    dpg.set_value('wait_disconnect', 0.1)
    dpg.set_value('wait_reconnect', 4)

def beep_sound():
    winsound.Beep(dpg.get_value('beep_frequency'), dpg.get_value('beep_duration'))
def beep_reset():
    dpg.set_value('beep_frequency', 500)
    dpg.set_value('beep_duration', 72)

# context thing
dpg.create_context()

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
            dpg.add_spacer(height=2)

            dpg.add_text(f'total games: {total_games}', tag='total_games')
            with dpg.group(horizontal=True):
                dpg.add_text('status:')
                dpg.add_text('inactive', color=(100, 149, 238), tag='farm_status')

        with dpg.tab(label='config'):
            with dpg.collapsing_header(label='timings'):
                dpg.add_text('game restart delay')
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('duration to wait before spamming through the menu to start a game', wrap=260)
                dpg.add_slider_int(label='seconds', min_value=0, max_value=30, default_value=int(config['game_restart_delay']), tag='wait_restart'),
                dpg.add_spacer(height=2)
                dpg.add_text('game load time')
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('duration to wait for the game to start (waiting for the game to load and countdown)', wrap=260)
                dpg.add_slider_int(label='seconds', min_value=5, max_value=30, default_value=int(config['game_load_time']), tag='wait_gameload')
                dpg.add_spacer(height=2)
                dpg.add_text('disconnect delay')
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('duration to wait before clicking the disconnect button after opening menu', wrap=260)
                dpg.add_slider_float(label='seconds', min_value=0.1, max_value=1, default_value=float(config['disconnect_delay']), tag='wait_disconnect')
                dpg.add_spacer(height=2)
                dpg.add_text('reconnect delay')
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text('duration to wait before attempting to reconnect', wrap=260)
                dpg.add_slider_int(label='seconds', min_value=3, max_value=20, default_value=int(config['reconnect_delay']), tag='wait_reconnect')
                dpg.add_button(label='reset', callback=timing_reset)
                dpg.add_spacer(height=2)
            with dpg.collapsing_header(label='boop beep?'):
                dpg.add_text('beep frequency')
                dpg.add_slider_int(label='hz', min_value=100, max_value=2000, default_value=int(config['beep_frequency']), tag='beep_frequency')
                dpg.add_text('beep duration')
                dpg.add_slider_int(label='ms', min_value=10, max_value=1000, default_value=int(config['beep_duration']), tag='beep_duration')
                dpg.add_spacer(height=2)
                with dpg.group(horizontal=True):
                    dpg.add_button(label='beep', callback=beep_sound)
                    dpg.add_button(label='reset', callback=beep_reset)
            with dpg.collapsing_header(label='other'):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label='stop at', tag='stop_farm')
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text('stops at set time', wrap=260)
                local_time = time.localtime()
                dpg.add_time_picker(default_value={'hour': local_time.tm_hour+3, 'min': local_time.tm_min, 'sec': 0}, tag='stop_farm_time')
                dpg.add_spacer(height=2)
                dpg.add_checkbox(label='max games', tag='max_games', default_value=bool(config['max_games']))
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
            with dpg.collapsing_header(label='options'):
                with dpg.tree_node(label='timer sound'):
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_checkbox(label='timer sound', default_value=True)
                    dpg.add_text('this option just makes a beep noise when a match is finished', wrap=0)
                with dpg.tree_node(label='always on top'):
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_checkbox(label='always on top', default_value=True)
                    dpg.add_text('keeps script window always on top...', wrap=0)
                with dpg.tree_node(label='start'):
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_button(label='start')
                    dpg.add_text('starts farming timer, use after you setup you lobby and have a legend selected', wrap=0)
                with dpg.tree_node(label='stop'):
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_button(label='stop')
                    dpg.add_text('immidiately stops the timer and everything, if you want to start farming again, go back to lobby and press start', wrap=0)
            with dpg.collapsing_header(label='faq'):
                with dpg.tree_node(label='why crew battle?'):
                    dpg.add_text('because it has 25 minute game option and the less time you spend in game menus, the more exp youre gonna get (i think lol)', wrap=0)
                    dpg.add_text('- me 05/17/2024', color=(100, 149, 238), user_data='https://discord.com/channels/829496409681297409/1240709211642527824/1240710940140503170')
                    dpg.add_text('xp and gold requires active participation and different modes calculate participation differently so bot is too dumb for ffa basically, because ffa requires actually doing damage and kills', wrap=0)
                    dpg.add_text('- sovamorco 10/08/2023', color=(100, 149, 238), user_data='https://discord.com/channels/829496409681297409/829503904190431273/1160557662145097898')

# setup and start
dpg.create_viewport(title='simple bhbot', width=300, height=200)
dpg.set_viewport_always_top(dpg.get_value('always_on_top'))
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window('main', True)
dpg.start_dearpygui()
config_write() # saves any changes before closing
dpg.destroy_context()

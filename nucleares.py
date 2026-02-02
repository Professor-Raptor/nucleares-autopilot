

#!/usr/bin/env python3
import threading
import time as pytime
import requests
from collections import deque
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.styles import Style
from prompt_toolkit.application.current import get_app

# ==========================
# CONFIG / CONSTANTS
# ==========================

SERVER_DOMAIN = 'http://localhost:8785'
TICK_SECONDS = 0.5

ROD_MIN, ROD_MAX = 0.0, 100.0
BYPASS_MIN, BYPASS_MAX = 0.0, 100.0
PUMP_MIN, PUMP_MAX = 0.0, 100.0

# ==========================
# HTTP HELPERS
# ==========================

def get_var(name: str) -> str:
    response = requests.get(f'{SERVER_DOMAIN}/?variable={name}', timeout=1).json()
    if response == None:
        response = 0.0
    return response

def get_alarms():
    return requests.get(f'{SERVER_DOMAIN}/?variable=ALARMS_ACTIVE', timeout=1).text

def post_var(name: str, val):
    requests.post(f'{SERVER_DOMAIN}/?variable={name}&value={val}', timeout=1)

def order_rods_pos(val): post_var('RODS_ALL_POS_ORDERED', val)
def order_bypass(i, val): post_var(f'STEAM_TURBINE_{i}_BYPASS_ORDERED', val)
def order_pump(i, val): post_var(f'COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED', val)

# ==========================
# SHARED STATE
# ==========================

lock = threading.Lock()

master_on = False
core_on = True
egen_on = True
sgen_on = True

bypass_enabled = [True, True, True]
pump_enabled = [True, True, True]

min_core_temp = 310.0
target_surplus = 2.0
target_vol = 33000.0

core_temp_hist = deque(maxlen=600)

last_core_adjust: Optional[float] = None
last_egen_adjust: Optional[float] = None
last_sgen_adjust = [None, None, None]

core_temp_hold_active = False
error_line: Optional[str] = None

# ---- SAFE DEFAULT TELEMETRY (CRITICAL FIX) ----
telemetry = {
    'time': 0.0,
    'core_temp': 0.0,
    'rods_pos': 0.0,
    'power_demand_mw': 0.0,
    'power_output_mw': 0.0,
    'bypass': [0.0, 0.0, 0.0],
    'sg_vol': [0.0, 0.0, 0.0],
    'sg_in': [1.0, 1.0, 1.0],
    'sg_out': [1.0, 1.0, 1.0],
    'pump': [0.0, 0.0, 0.0],
    'alarms': [],
}

# ==========================
# UTILS
# ==========================

def clamp_check(val, lo, hi):
    return lo <= val <= hi

def clamp(value, lo=0, hi=100):
    return max(lo, min(hi, value))

def nearest_past_temp(target_time):
    for t, temp in reversed(core_temp_hist):
        if t <= target_time:
            return temp
    return None

def set_error(msg: str):
    global error_line
    error_line = msg

# ==========================
# CONTROL LOGIC
# ==========================

def control_tick():
    global last_core_adjust, last_egen_adjust, core_temp_hold_active

    if not master_on:
        return

    time_min = telemetry['time']

    # ---------- CORE ----------
    if core_on:
        if last_core_adjust is None or time_min - last_core_adjust >= 4.0:
            prev = nearest_past_temp(time_min - 1.0)
            cur = telemetry['core_temp']
            rods = telemetry['rods_pos']

            if prev is not None:
                if cur < min_core_temp and cur < prev:
                    new = rods - 0.1
                    order_rods_pos(clamp(new, ROD_MIN, ROD_MAX))
                    last_core_adjust = time_min

                elif cur > min_core_temp + 5 and cur > prev:
                    new = rods + 0.1
                    order_rods_pos(clamp(new, ROD_MIN, ROD_MAX))
                    core_temp_hold_active = True
                    last_core_adjust = time_min

                elif core_temp_hold_active and cur < min_core_temp + 2:
                    new = rods - 0.1
                    order_rods_pos(clamp(new, ROD_MIN, ROD_MAX))
                    core_temp_hold_active = False
                    last_core_adjust = time_min

    # ---------- EGEN ----------
    if egen_on:
        if last_egen_adjust is None or time_min - last_egen_adjust >= 1.0:
            enabled = [i for i in range(3) if bypass_enabled[i]]
            if enabled:
                demand = telemetry['power_demand_mw'] + target_surplus
                delta = telemetry['power_output_mw'] - demand
                ad = abs(delta)

                step = 0
                if 2 < ad < 8: step = 1
                elif 9 <= ad < 20: step = 3
                elif ad >= 20: step = 8

                if step:
                    direction = 1 if delta > 0 else -1
                    for i in enabled:
                        new = telemetry['bypass'][i] + direction * step
                        order_bypass(i, clamp(new, BYPASS_MIN, BYPASS_MAX))
                    last_egen_adjust = time_min

    # ---------- SGEN ----------
    if sgen_on:
        for i in range(3):
            if not pump_enabled[i]:
                continue

            last = last_sgen_adjust[i]
            if last is not None and time_min - last < 1.0:
                continue

            vol = telemetry['sg_vol'][i]
            inlet = telemetry['sg_in'][i]
            outlet = telemetry['sg_out'][i]
            pump = telemetry['pump'][i]

            if outlet == 0:
                continue

            ratio = inlet / outlet
            diff = vol - target_vol
            ad = abs(diff)

            step = 0
            lo1, hi1 = None, None
            lo2, hi2 = None, None

            if ad <= 1000:
                lo1, hi1 = 0.999, 1.001
                lo2, hi2 = 0.999, 1.001
            elif ad <= 2000:
                step = 1
                lo1, hi1 = 0.99, 1.01
                lo2, hi2 = 0.99, 1.01
            elif ad < 5000:
                step = 1
                lo1, hi1 = 1.04, 1.07
                lo2, hi2 = 0.93, 0.96
            else:
                step = 2
                lo1, hi1 = 1.07, 1.11
                lo2, hi2 = 0.96, 0.89

            if step and not (lo1 <= ratio <= hi1) or not (lo2 <= ratio <= hi2):
                direction = 1 if diff < 0 else -1
                new = pump + direction * step
                order_pump(i, clamp(new, PUMP_MIN, PUMP_MAX))

# ==========================
# TELEMETRY UPDATE
# ==========================

def update_telemetry():
    telemetry['time'] = get_var('TIME_STAMP')
    telemetry['core_temp'] = get_var('CORE_TEMP')
    telemetry['rods_pos'] = get_var('RODS_POS_ACTUAL')

    telemetry['power_demand_mw'] = get_var('POWER_DEMAND_MW')
    gens = [get_var(f'GENERATOR_{i}_KW') for i in range(3)]
    telemetry['power_output_mw'] = sum(gens) / 1000.0

    telemetry['bypass'] = [get_var(f'STEAM_TURBINE_{i}_BYPASS_ACTUAL') for i in range(3)]
    telemetry['sg_vol'] = [get_var(f'COOLANT_SEC_{i}_LIQUID_VOLUME') for i in range(3)]
    telemetry['sg_in'] = [get_var(f'STEAM_GEN_{i}_INLET') for i in range(3)]
    telemetry['sg_out'] = [get_var(f'STEAM_GEN_{i}_OUTLET') for i in range(3)]
    telemetry['pump'] = [get_var(f'COOLANT_SEC_CIRCULATION_PUMP_{i}_SPEED') for i in range(3)]

    alarms = get_alarms()
    telemetry['alarms'] = [a.strip() for a in alarms.split(',') if a.strip()][:10]

    core_temp_hist.append((telemetry['time'], telemetry['core_temp']))

# ==========================
# BACKGROUND LOOP
# ==========================

def control_loop():
    while True:
        try:
            with lock:
                update_telemetry()
                control_tick()
        except Exception as e:
            set_error(str(e))
        request_redraw()
        pytime.sleep(TICK_SECONDS)

# ==========================
# UI
# ==========================

style = Style.from_dict({
    'cyan': 'cyan',
    'yellow': 'yellow',
    'red': 'red',
    'darkgrey': 'darkgrey',
    'darkcyan': 'darkcyan',
    'seagreen': 'seagreen',
})

def render():
    f = []
    f.append(('', '\n\n'))
    f.append(('cyan' if master_on else 'yellow', '   NUCLEARES AUTOPILOT\n\n'))

    f.append(('cyan' if core_on else '', '       CORE\n'))
    ct = telemetry['core_temp']
    f.append(('yellow' if ct < min_core_temp or ct > min_core_temp + 5 else '', f'   Temp: {ct:.1f}\n'))
    f.append(('', f'   MinT: {min_core_temp}\n'))
    f.append(('', f'   Rods: {telemetry["rods_pos"]:.1f}\n\n'))

    f.append(('cyan' if egen_on else '', '       EGEN\n'))
    po = telemetry['power_output_mw']
    pd = telemetry['power_demand_mw'] + target_surplus
    f.append(('yellow' if abs(po - pd) > 2 else '', f'   Pwr Output: {po:.1f}\n'))
    f.append(('', f'   Pwr Demand: {telemetry["power_demand_mw"]:.1f}\n'))
    f.append(('', f'   Tg Surplus: {target_surplus}\n'))

    bp_val = next((telemetry['bypass'][i] for i in range(3) if bypass_enabled[i]), 0.0)
    f.append(('yellow' if bp_val < 6 or bp_val > 90 else '', f'   Bypass val: {bp_val:.1f}\n'))
    f.append(('', f'   Bp on: '))
    f.append(('seagreen', f'{[i+1 for i,v in enumerate(bypass_enabled) if v]}\n\n'))

    f.append(('cyan' if sgen_on else '', '       SGEN\n'))
    # f.append(('', '         SG1  SG2  SG3\n'))
    f.append(('seagreen' if pump_enabled[0] else 'darkgrey', '         SG1'))
    f.append(('seagreen' if pump_enabled[1] else 'darkgrey', '  SG2'))
    f.append(('seagreen' if pump_enabled[2] else 'darkgrey', '  SG3\n'))
    f.append(('', f'   LVol: {telemetry["sg_vol"][0]/100:>3.0f}  {telemetry["sg_vol"][1]/100:>2.0f}  {telemetry["sg_vol"][2]/100:>2.0f}\n'))
    f.append(('', f'   Pump: {telemetry["pump"][0]:>3.0f}  {telemetry["pump"][1]:>3.0f}  {telemetry["pump"][2]:>3.0f}\n'))
    f.append(('', f'   Tg Vol: {target_vol}\n\n'))

    f.append(('', '       ALARMS\n'))
    for a in telemetry['alarms']:
        f.append(('red', f'   {a}\n'))

    if error_line:
        f.append(('red', '\n' + error_line + '\n'))

    return f

body = Window(content=FormattedTextControl(render), always_hide_cursor=True)
input_field = TextArea(prompt='> ', style='cyan', multiline=False)

def on_enter(_):
    global master_on, core_on, egen_on, sgen_on
    global min_core_temp, target_surplus, target_vol
    global error_line

    cmd = input_field.text.strip().lower()
    input_field.text = ''
    error_line = None

    parts = cmd.split()
    try:
        if parts[0] == 'on': master_on = True
        elif parts[0] == 'off': master_on = False
        elif parts[0] == 'core': core_on = parts[1] == 'on'
        elif parts[0] == 'egen': egen_on = parts[1] == 'on'
        elif parts[0] == 'sgen': sgen_on = parts[1] == 'on'
        elif parts[0] == 'temp': min_core_temp = float(parts[1])
        elif parts[0] == 'surplus': target_surplus = float(parts[1])
        elif parts[0] == 'volume': target_vol = float(parts[1])
        elif parts[0] == 'bypass': bypass_enabled[int(parts[1])-1] = parts[2] == 'on'
        elif parts[0] == 'pump': pump_enabled[int(parts[1])-1] = parts[2] == 'on'
        elif parts[0] == 'exit': app.exit()
        elif parts[0] == 'help':
            set_error("on/off | core/egen/sgen on/off | temp X | surplus X | volume X | bypass N on/off | pump N on/off | exit")
    except Exception:
        set_error("Invalid command")

def request_redraw():
    app = get_app()
    if app is None:
        return
    loop = app.loop
    if loop is None:
        return
    loop.call_soon_threadsafe(app.invalidate)

input_field.accept_handler = on_enter

layout = Layout(HSplit([body, input_field]))
app = Application(layout=layout, style=style, full_screen=True)

threading.Thread(target=control_loop, daemon=True).start()
app.run()

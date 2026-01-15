# Nucleares Autopilot
A Python script that automates plant control in the Steam game Nucleares via the built-in webserver feature. It can manage core temp via rods, electrical output via bypass valves, and/or steam generator volumes via 2nd loop pumps.  


## Install 
- [nucleares.exe](https://github.com/Professor-Raptor/nucleares-autopilot/releases/download/v0.1.0/nucleares.exe)  -- Windows standalone binary  
- [nucleares.py](https://github.com/Professor-Raptor/nucleares-autopilot/releases/download/v0.1.0/nucleares.py)  -- Python script file (requires dependencies)

If you know nothing about Python and want to just download and run, try the executable. Know that you will not be able to configure it, although you shouldn't need to anyways.  
The python file is just a copy from the repo. The version in the main branch may have updates so consider just grabbing it from there. You will need these:  
```
python -m pip install prompt_toolkit  
python -m pip install requests  
```

## Limitations
Unfortunately, I like 90% vibe coded this script, please forgive me. It does not use PID or any other sophisticated solutions; I just eyeballed the control logic with some basic rules. The core/rod control is particularly delicate and slow; it is primarily designed only to hold the current temperature. The intention is for the core temp to be completely stable just 1-4 degrees above the set minimum temp before turning control on. Having the reactor outside of this condition when turning on core control will likely cause issues.  
The script was designed around using five fuel cells, although it seems to work okay with one. If you are using more than five, I imagine at some point you will need to tweak the core control logic (specifically, consider changing +5 and +2 to higher numbers).  
I’ve not even tried using this with chemicals, so for all I know, it may not work at all when using them.  


## Usage
The following commands are available:  
- ON - enable master control  
- OFF - disable master control  
- CORE <"on" or "off"> - enables/disables control specifically for the CORE system (rods)  
- EGEN <"on" or "off"> - enables/disables control  specifically for the EGEN system (bypass valves)  
- SGEN <"on" or "off"> - enables/disables control  specifically for the SGEN system (2nd loop pumps)  
- TEMP <value> - set the core temperature target (minimum)  
- SURPLUS <value> - (MW) set how much power to generate above demand (for bypass control)  
- BYPASS <loop ID> <"on" or "off"> - enables/disables control of each loop’s bypass valve (1, 2, or 3)  
- VOLUME <value> - set target coolant volume for steam generators (for pump control)  
- PUMP <loop ID> <"on" or "off"> - enables/disables control of each loop’s 2nd pump (1, 2, or 3)  
- EXIT - exit the script  
- HELP - display commands  

First, if you’ve not already done so, under status on your tablet, start the webserver on port 8785 (should be the default so you can leave the box blank).  
In the UI, each header will be colored cyan or green to indicate if control is enabled for that system.  
If you do not have all three loops installed, YOU MUST FIRST DISABLE PUMPS THAT ARE NOT INSTALLED (e.g: “pump 1 off”).  
By default, the master control is off. Core control was only designed to hold the temperature, so first get the core stable at your desired temperature. Then set the temperature to just below this temperature (e.g: “temp 320”). Then you can finally enable control (e.g. “on” and/or “core on”). 

![TUI Image](https://private-user-images.githubusercontent.com/194707211/535980641-ee70eb78-3a85-4ff9-8dab-e8fdccc6215e.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3Njg0MzgxNTUsIm5iZiI6MTc2ODQzNzg1NSwicGF0aCI6Ii8xOTQ3MDcyMTEvNTM1OTgwNjQxLWVlNzBlYjc4LTNhODUtNGZmOS04ZGFiLWU4ZmRjY2M2MjE1ZS5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwMTE1JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDExNVQwMDQ0MTVaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT02NTg2ZDQwNDAwNzUyNTllMzEyNDJmNGI1NTkxNjk4ODk2NzkwNGZhNDVhZGZkODliMDIwNzRmYjVmMjJjMmM5JlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.PFz0a0eevTg_6puBqVcOYjcaliKKNwDSYhFJOBxg-sg)

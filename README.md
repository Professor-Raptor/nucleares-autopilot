# Nucleares Autopilot
A script that automates plant control in the Steam game Nucleares. It can manage core temp using rods, electrical output using bypass valves, and/or steam generator volumes using 2nd loop pumps. 

Unfortunately this script is like 90% vibe coded, but it does work. If you haven’t done so yet, consider [GHXX’s controller](https://github.com/GHXX/NuclearesController) first since it’ s probably better thought out. 
Autopilot does not use PID, or any other sophisticated solutions, I just eyeballed the control logic with some basic rules. The core/rod control is the most delicate and slow. It is primarily designed only to hold the current temperature. The intention is for the core temp to be completely stable just 1-4 degrees above the set minimum temp before turning control on. Having the reactor outside of this condition could cause autopilot to oscillate or worse. This was designed around having 5 fuel cells and 

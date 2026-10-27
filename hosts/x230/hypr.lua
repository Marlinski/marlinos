-- X230-only Hyprland settings (loaded last by roles/desktop/config/hypr/hyprland.lua)
local bind, exec = ...

-- ---------------------------------------------------------------- this machine

hl.monitor({ output = "LVDS-1", mode = "1366x768@60", position = "0x0", scale = 1 })

-- the X230's small PS/2 touchpad needs a fast scroll
hl.config({ input = { touchpad = { scroll_factor = 2.0 } } })

-- the power button asks first (logind ignores it, see etc/systemd/logind.conf.d/power-key.conf).
-- The X230 only reports the button when held about a second: quick taps never reach Linux.
bind("XF86PowerOff", "Power menu", exec("~/.local/bin/power-menu"))

-- marlinos Hyprland config (single file, Hyprland 0.56+, Lua)
-- Key bindings go through bind(keys, description, dispatcher, flags): the description shows in
-- `hyprctl binds` and in `cheat hyprland`, which reads the bind(...) lines and the section comments.

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

local terminal = "uwsm app -- alacritty"
local browser  = "uwsm app -- firefox"
local menu     = 'fuzzel --launch-prefix="uwsm app -- "'

local function bind(keys, description, dispatcher, flags)
    local f = { description = description }
    for k, v in pairs(flags or {}) do f[k] = v end
    hl.bind(keys, dispatcher, f)
end
local exec = hl.dsp.exec_cmd

-- ---------------------------------------------------------------- autostart
hl.on("hyprland.start", function()
    hl.exec_cmd("uwsm app -- waybar")
    hl.exec_cmd("uwsm app -- mako")
    hl.exec_cmd("uwsm app -- hypridle")
    hl.exec_cmd("uwsm app -- /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1")
end)

-- ---------------------------------------------------------------- look
-- Tokyo Night palette: bg 1a1b26, fg c0caf5, blue 7aa2f7, grey 414868
hl.config({
    general = {
        gaps_in = 3,
        gaps_out = 6,
        border_size = 2,
        col = {
            active_border = "rgb(7aa2f7)",
            inactive_border = "rgb(414868)",
        },
        layout = "dwindle",
    },
    decoration = {
        rounding = 0,
        shadow = { enabled = false },
        blur = { enabled = false },
    },
    animations = { enabled = true },
    dwindle = { preserve_split = true },
    misc = {
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        background_color = "rgb(1a1b26)",
        focus_on_activate = true,
    },
    ecosystem = {
        no_update_news = true,
        no_donation_nag = true,
    },
})

hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } })
hl.animation({ leaf = "global", enabled = true, speed = 3, bezier = "quick" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 2, bezier = "quick", style = "slide" })
-- windows snap into place (open, close, move)
for _, leaf in ipairs({ "windows", "windowsIn", "windowsOut", "windowsMove" }) do
    hl.animation({ leaf = leaf, enabled = false })
end

-- ---------------------------------------------------------------- input
hl.config({
    input = {
        kb_layout = "us",
        kb_options = "compose:caps",
        repeat_rate = 40,
        repeat_delay = 600,
        numlock_by_default = true,
        follow_mouse = 1,
        touchpad = {
            natural_scroll = false,
            scroll_factor = 0.4,
        },
    },
})

-- ---------------------------------------------------------------- apps
bind("SUPER + Return", "Terminal", exec(terminal))
bind("SUPER + Space", "Launcher", exec(menu))
bind("SUPER + B", "Browser", exec(browser))
bind("SUPER + SHIFT + B", "Browser (private)", exec(browser .. " --private-window"))
bind("SUPER + F", "File manager", exec(terminal .. " -e ranger"))
bind("SUPER + T", "Activity", exec(terminal .. " -e btop"))
bind("SUPER + N", "Editor", exec(terminal .. " -e nvim"))
bind("SUPER + A", "Claude", exec(terminal .. " -e claude"))
bind("SUPER + M", "Music", exec("~/.local/bin/music"))

-- ---------------------------------------------------------------- session
bind("SUPER + Escape", "Lock", exec("loginctl lock-session"))
bind("SUPER + SHIFT + Escape", "Exit Hyprland", exec("uwsm stop"))
bind("SUPER + CTRL + Escape", "Suspend", exec("systemctl suspend"))
bind("SUPER + SHIFT + Space", "Toggle bar", exec("pkill -SIGUSR1 waybar"))

-- ---------------------------------------------------------------- windows
bind("SUPER + SHIFT + Q", "Close window", hl.dsp.window.close())
bind("SUPER + W", "Close window", hl.dsp.window.close())
bind("SUPER + V", "Toggle floating", hl.dsp.window.float({ action = "toggle" }))
bind("SUPER + J", "Toggle split", hl.dsp.layout("togglesplit"))
bind("F11", "Fullscreen", hl.dsp.window.fullscreen({ mode = "fullscreen" }))
bind("SUPER + SHIFT + F", "Maximize", hl.dsp.window.fullscreen({ mode = "maximized" }))

bind("SUPER + left", "Focus left", hl.dsp.focus({ direction = "l" }))
bind("SUPER + right", "Focus right", hl.dsp.focus({ direction = "r" }))
bind("SUPER + up", "Focus up", hl.dsp.focus({ direction = "u" }))
bind("SUPER + down", "Focus down", hl.dsp.focus({ direction = "d" }))
bind("SUPER + SHIFT + left", "Move left", exec("~/.local/bin/hypr-move l"))
bind("SUPER + SHIFT + right", "Move right", exec("~/.local/bin/hypr-move r"))
bind("SUPER + SHIFT + up", "Move up", exec("~/.local/bin/hypr-move u"))
bind("SUPER + SHIFT + down", "Move down", exec("~/.local/bin/hypr-move d"))
bind("SUPER + minus", "Shrink width", hl.dsp.window.resize({ x = -60, y = 0, relative = true }))
bind("SUPER + equal", "Grow width", hl.dsp.window.resize({ x = 60, y = 0, relative = true }))
bind("SUPER + SHIFT + minus", "Shrink height", hl.dsp.window.resize({ x = 0, y = -60, relative = true }))
bind("SUPER + SHIFT + equal", "Grow height", hl.dsp.window.resize({ x = 0, y = 60, relative = true }))

bind("SUPER + mouse:272", "Move window", hl.dsp.window.drag(), { mouse = true })
bind("SUPER + mouse:273", "Resize window", hl.dsp.window.resize(), { mouse = true })

-- ---------------------------------------------------------------- workspaces
bind("SUPER + 1", "Workspace 1", hl.dsp.focus({ workspace = 1 }))
bind("SUPER + 2", "Workspace 2", hl.dsp.focus({ workspace = 2 }))
bind("SUPER + 3", "Workspace 3", hl.dsp.focus({ workspace = 3 }))
bind("SUPER + 4", "Workspace 4", hl.dsp.focus({ workspace = 4 }))
bind("SUPER + 5", "Workspace 5", hl.dsp.focus({ workspace = 5 }))
bind("SUPER + 6", "Workspace 6", hl.dsp.focus({ workspace = 6 }))
bind("SUPER + 7", "Workspace 7", hl.dsp.focus({ workspace = 7 }))
bind("SUPER + 8", "Workspace 8", hl.dsp.focus({ workspace = 8 }))
bind("SUPER + 9", "Workspace 9", hl.dsp.focus({ workspace = 9 }))
bind("SUPER + SHIFT + 1", "Move to workspace 1", hl.dsp.window.move({ workspace = 1, follow = true }))
bind("SUPER + SHIFT + 2", "Move to workspace 2", hl.dsp.window.move({ workspace = 2, follow = true }))
bind("SUPER + SHIFT + 3", "Move to workspace 3", hl.dsp.window.move({ workspace = 3, follow = true }))
bind("SUPER + SHIFT + 4", "Move to workspace 4", hl.dsp.window.move({ workspace = 4, follow = true }))
bind("SUPER + SHIFT + 5", "Move to workspace 5", hl.dsp.window.move({ workspace = 5, follow = true }))
bind("SUPER + SHIFT + 6", "Move to workspace 6", hl.dsp.window.move({ workspace = 6, follow = true }))
bind("SUPER + SHIFT + 7", "Move to workspace 7", hl.dsp.window.move({ workspace = 7, follow = true }))
bind("SUPER + SHIFT + 8", "Move to workspace 8", hl.dsp.window.move({ workspace = 8, follow = true }))
bind("SUPER + SHIFT + 9", "Move to workspace 9", hl.dsp.window.move({ workspace = 9, follow = true }))
bind("SUPER + Tab", "Next workspace", hl.dsp.focus({ workspace = "e+1" }))
bind("SUPER + SHIFT + Tab", "Previous workspace", hl.dsp.focus({ workspace = "e-1" }))
bind("SUPER + Prior", "Previous workspace", hl.dsp.focus({ workspace = "e-1" }))
bind("SUPER + Next", "Next workspace", hl.dsp.focus({ workspace = "e+1" }))
bind("SUPER + SHIFT + Prior", "Move to previous workspace", hl.dsp.window.move({ workspace = "e-1", follow = true }))
bind("SUPER + SHIFT + Next", "Move to next workspace", hl.dsp.window.move({ workspace = "e+1", follow = true }))

-- ---------------------------------------------------------------- hardware keys
local held = { locked = true, repeating = true }   -- works on the lock screen, repeats while held
local locked = { locked = true }
bind("XF86AudioRaiseVolume", "Volume up", exec("wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"), held)
bind("XF86AudioLowerVolume", "Volume down", exec("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), held)
bind("XF86AudioMute", "Mute", exec("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), locked)
bind("XF86AudioMicMute", "Mute mic", exec("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), locked)
bind("XF86MonBrightnessUp", "Brightness up", exec("brightnessctl set 5%+"), held)
bind("XF86MonBrightnessDown", "Brightness down", exec("brightnessctl set 5%-"), held)
bind("XF86AudioPlay", "Play/pause", exec("playerctl play-pause"), locked)
bind("XF86AudioNext", "Next track", exec("playerctl next"), locked)
bind("XF86AudioPrev", "Previous track", exec("playerctl previous"), locked)

-- ---------------------------------------------------------------- capture
bind("Print", "Screenshot region", exec('hyprshot -m region -o "$(xdg-user-dir PICTURES)"'))
bind("SHIFT + Print", "Screenshot window", exec('hyprshot -m window -o "$(xdg-user-dir PICTURES)"'))
bind("CTRL + Print", "Screenshot screen", exec('hyprshot -m output -o "$(xdg-user-dir PICTURES)"'))
bind("ALT + Print", "Screen recording", exec("~/.local/bin/screenrecord"))
bind("SUPER + Print", "Color picker", exec("hyprpicker -a"))

-- ---------------------------------------------------------------- this machine
-- hosts/<host>/hypr.lua (monitors, input quirks...). Every desktop host must have one; it gets
-- bind() and exec as arguments.
local host = os.getenv("HOME") .. "/.config/marlinos/host/hypr.lua"
local chunk, err = loadfile(host)
if chunk then
    chunk(bind, exec)
else
    hl.notification.create({ text = "marlinos: " .. tostring(err), timeout = 10000, color = "rgb(f7768e)" })
end

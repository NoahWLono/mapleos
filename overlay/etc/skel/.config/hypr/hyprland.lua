-- MapleOS Core. Native Lua syntax, Hyprland >= 0.55.
-- Caelestia integration files are preserved separately, not mixed into this shell.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
hl.config({
    general = { gaps_in = 5, gaps_out = 12, border_size = 2, layout = "dwindle" },
    decoration = { rounding = 12, blur = { enabled = true, size = 3, passes = 2 } },
    input = { kb_layout = "us", follow_mouse = 1, touchpad = { natural_scroll = true } },
    misc = { disable_hyprland_logo = true, force_default_wallpaper = 0 },
})
hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("systemctl --user start hyprpolkitagent.service")
    hl.exec_cmd("swaybg -i /usr/share/backgrounds/mapleos/maple.png -m fill")
    hl.exec_cmd("waybar")
    hl.exec_cmd("mako")
    hl.exec_cmd("nm-applet --indicator")
    hl.exec_cmd("udiskie")
end)

-- Current native Lua dispatcher API.
hl.bind("SUPER + Return", hl.dsp.exec_cmd("foot"))
hl.bind("SUPER + D", hl.dsp.exec_cmd("fuzzel"))
hl.bind("SUPER + E", hl.dsp.exec_cmd("thunar"))
hl.bind("SUPER + B", hl.dsp.exec_cmd("firefox"))
hl.bind("SUPER + A", hl.dsp.exec_cmd("foot -e maple workbench"))
hl.bind("SUPER + W", hl.dsp.window.close())
hl.bind("SUPER + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + SHIFT + E", hl.dsp.exec_cmd("hyprshutdown"))
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd("sh -c 'grim -g \"$(slurp)\" - | wl-copy'"))
for i=1,9 do
    hl.bind("SUPER + " .. i, hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER + SHIFT + " .. i, hl.dsp.window.move({ workspace = i }))
end
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked=true, repeating=true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked=true, repeating=true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked=true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set +5%"), { locked=true, repeating=true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"), { locked=true, repeating=true })

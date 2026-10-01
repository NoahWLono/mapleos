if status is-interactive
    fish_add_path --path $HOME/.local/bin
    function fish_greeting
        if type -q fastfetch
            fastfetch --config /usr/share/mapleos/fastfetch.json
        end
    end
    if type -q starship
        starship init fish | source
    end
    if type -q zoxide
        zoxide init fish | source
    end
end

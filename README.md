# dotdot -- dot-files manager

Yeah, yet another dotfiles manager.

This is an iteration over a previous solution that became annoying to maintain.
As I still wanted the same overall behaviour -- create links in my home pointing
to my dotfiles repo -- I decided to create a new tool with the desired
behaviour instead of migrate my setup to chezmoi or something else.

BTW, check [this link](https://dotfiles.github.io/utilities/) for a
comprehensive list of tools that are way more powerful than this one.

# Installing

```
$ pip install git+https://github.com/kassick/dotdot
```

# Creating dots

## Simple file dot example

1. Create a file `dots/tmux.conf` with your tmux configuration
2. Run `dotdot -d dots install tmux.conf`
3. Voilá! `~/.tmux.conf` points to `$CWD/dots/tmux.conf`

## A setup consisting of several files

1. Create a folder `dots/zshrc`
2. Create files `dots/zshrc/zshrc` and `dots/zshrc/zprofile`
3. Run `dotdot -d dots install zshrc`
4. `~/.zshrc` and `~/.zprofile` point to the files under `$CWD/dots/zshrc`

## Spec-file based setup

For more complex setups, you must create a `spec.yaml` file inside a folder and
specify the actions

### Clonning a repository

For an up-to-date *oh-my-zsh*, we must have the repository cloned locally. We
can specify the process in the spec.yaml this way:

1. Create `dots/zsh/zshrc` and `dots/zsh/zprofile`
2. Create `dots/zsh/spec.yaml` with contents

```yaml
    description: ZSH setup

    actions:
    - git_clone:
        - url: https://github.com/ohmyzsh/ohmyzsh.git
          to: .oh-my-zsh
    - link:
        - zshrc
        - zprofile
```

3. Run `dotdot -d dots install zsh`
4. You should now have a git repo under `~/.oh-my-zsh` and files `~/.zshrc` and
   `~/.zprofile` pointing to the copies under `dots/zsh`

### Running commands

To run something upon installation, use the `execute` action

```yaml
description: Give me classical alt-tab without extensions
actions:
- execute: |
    gsettings set org.gnome.desktop.wm.keybindings switch-applications "['<Super>Tab']"
    gsettings set org.gnome.desktop.wm.keybindings switch-applications-backward "['<Shift><Super>Tab']"
    gsettings set org.gnome.desktop.wm.keybindings switch-windows "['<Alt>Tab']"
    gsettings set org.gnome.desktop.wm.keybindings switch-windows-backward "['<Alt><Shift>Tab']"
```

### Symlinking files under some path

Sometimes the destination of your files is somewhat deep under your home (e.g.
`.local/share/fonts`) and you don't want to list every one of the fonts in the
spec file. In this case, you can use the `link_recursively` rule

1. Store your fonts under `dots/fonts/local/share/fonts`
2. Tell dotdot to symlink every file under local to it's corresponding path
   under $HOME:
```yaml
description: Fonts
actions:
- link_recursively: local
```
3. All files under `dots/fonts/local/share/fonts` will be symlinked to
   `~/.local/share/fonts`.

### Variants

Say that you need a dot to run one command under ubuntu, but another one under
fedora? That's what variants are for.

Create the named variants under the `variants` key and specify different actions
for any variant you want. Use yaml references if you want to avoid repeating
yourself.

```yaml
description: A Package with variants

common_actions: &common_actions
  - execute: echo cmd1
  - execute: |
      echo cmd2
      echo cmd3


variants:

  fedora: &fedora
    - execute: echo fedora only first
    - *common_actions
    - execute: echo fedora only last

  ubuntu:
    - execute: echo ubuntu only first
    - *common_actions
    - execute: echo ubuntu only last

  default: *fedora
```

Use the '-V' flag under `install` and `show` to specify which variant to use.

# Command line reference

Run `dotdot --help` to get the full help

- `dotdot -d dots list`: Shows all packages found under `dots`
- `dotdot -d dots show pkg1`: Displays information on pkg1, including the available variants and commands that would be executed
- `dotdot -d dots show -V fedora pkg1`: Shows the actions that would be executed under the `fedora` variant
- `dotdot -d dots install pkg1`: Install pkg1. It there are variants, it will use the default one.
- `dotdot -d dots install -V fedora pkg1`: Install pkg1 using the rules under the `fedora` variant.
- `dotdot help-actions`: Lists all actions that can be used in the spec file
- `dotdot help-actions link`: Shows detailed help for the link action

# Actions documentation

## `link`

Creates symlinks pointing to the target files or folders.

The link action can handle:
- a single item

```yaml
actions:
# creates ~/.file
- link: file
```

- multiple items
```yaml
actions:
# creates ~/.file1 and ~/.file2
- link:
  - file1
  - file2
```

- Multiple items with source and origin specified. When specifying a
  destination, it's up to the user to create a hidden file or a visible one.

```yaml
actions:
- link:
  # creates ~/.new_file_name pointing to original_file_name
  - from: original_file_name
    to: .new_file_name
  # creates ~/new_other_file_name pointing to other_file
  - from: other_file
    to: new_other_file_name
  # creates ~/.file1 -- when no destination is specified, we hide the file
  - file1
```

The tool can handle absolute paths in the `to` field, but this tool us supposed
to be a dot-file setup tool, not some full-fledged installer. In this case,
you'd need to call the tool with sudo.

```yaml
actions:
- link:
  - from: launcher.desktop
    to: /usr/share/applications/launcher.desktop
```

## `copy`

Copies a file from the package directory to the user's home. Same syntax as
`link`

```yaml
- actions:
  - copy: file1
```

## `link_recursively`

Recreates a tree structure under the destination and links all files present in
the target.

- Link all files under the path to their corresponding paths at the home
  directory

```yaml
actions:
# local contains:
# local/share/zsh/custom/plugins/my_plugin/myplugin.plugin.zsh
# local/etc/zsh/env.d/99_some_script.zsh
#
# this rule creates:
# ~/.local/share/zsh/custom/plugins/my_plugin/myplugin.plugin.zsh
# ~/.local/share/env.d/99_some_script.zsh
- link_recursively: local
```

- Multiple items

```yaml
actions:
# will scan for files under local and etc.d, creating corresponding links under ~/.local and ~/.etc.d
- link_recursively
  - local
  - etc.d
```

- Multiple items with source and origin specified. When specifying a
  destination, it's up to the user to create a hidden file or a visible one.

```yaml
actions:
- link_recursively:
  - from: share
    to: .local/share
  # replicates the folder structure under etc.d links under ~/.local/etc.d
  # creating symlinks pointing to the package
  - from: etc.d
    to: .local/etc.d
```

## `execute`

The execute rule runs a sequence of commands and verify their exit-status.

Execute can have a single command that will be executed at the same path as the
`spec.yaml` file:

```yaml
actions:
# requires setup.sh present and executable
- execute: ./setup.sh
# requires setup.sh present
- execute: sh setup.sh
```

Commands under a same `execute:` rule are glued together ane executed in a same
`sh` process. In between every command, the exit-status will be checked and the
script will be interrupted in case of error:

```yaml
actions:
- execute:
    - echo this is the first command
    - [ "a" == "b" ]  # exit status != 0
    - echo this command never executes
```

You can use variable definitions unser the same `execute:` rule -- but not
between different ones:

```yaml
actions:
- execute:
    - GUESS=content
    - echo $GUESS        # will output "content"
- execute: echo $GUESS   # will produce no output
```

Because every item under `execute:` will be checked for status, we can not use
`if`, `for`, `case`, etc. in different items, but we can give provide a single
multiline item:

```yaml
actions:
- execute:
    - read GUESS
    - |
      if [ "$GUESS" == "correct_value"]; then
        echo CORRECT!
      else
        false
      fi
    - echo 'This executes only if the user guessed right'
```

## `git_clone`

Clones a git repository to some destination path. If the path already exists as
a git repo, it pulls changes from the origin.

```yaml
actions:
- git_clone:
    # VERY META
    - from: https://github.com/kassick/dotdot
      to: Sources/user/dotdot
      branch: develop
```

`branch` is optional. When branch is not defined, the tool will pick the first
of the following branches that exist on remote:
- The current ref
- `main`
- `master`

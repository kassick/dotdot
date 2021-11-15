import os
import sys
import textwrap
from argparse import ArgumentParser

from yaml.error import YAMLError

from dotdot.actions import get_actions_help
from dotdot.exceptions import InvalidActionType, InvalidPackageException
from dotdot.pkg import Package


def exception_to_msg(ex: Exception) -> str:
    if isinstance(ex, InvalidPackageException):
        return 'path contains an invalid dot'
    elif isinstance(ex, YAMLError):
        return 'Invalid spec'
    elif isinstance(ex, InvalidActionType):
        return 'Spec contains invalid actions'
    else:
        return str(ex)


def cmd_list(args):
    if not os.path.isdir(args.dots_path):
        print('Invalid dots path', args.dots_path)
        sys.exit(1)

    pkgs, errors = Package.scan(args.dots_path)

    if errors:
        print('Warning: Errors found on the following dots:')
        for dot, ex in errors:
            print(f'- {dot}: {exception_to_msg(ex)}')
            if args.verbose:
                ex_msg = textwrap.indent(str(ex), '    ')
                print(ex_msg)
        print('\n-----\n')

    print('Available dots:')
    for p in pkgs:
        dsc = f': {p.description}' if p.description else ''
        print(f'- {p.name}{dsc}')


def cmd_install(args):
    pkgs = []
    for dot in args.dot:
        dot_path = os.path.join(args.dots_path, dot)
        try:
            pkgs.append(Package.from_dot_path(dot_path, variant=args.variant))
        except Exception as e:
            print(f'ERROR: Could not load dot {dot}')
            print(exception_to_msg(e))

            return

    for pkg in pkgs:
        print(f'Installing {pkg.name}')
        for action in pkg.actions:
            try:
                action = action.materialize()
                print(action.msg())
                action.execute()
            except Exception as e:
                print('Error while executing action:', str(e))
                return


def cmd_show(args):
    dot_path = os.path.join(args.dots_path, args.dot)
    try:
        pkg = Package.from_dot_path(dot_path, variant=args.variant)
    except Exception as e:
        print(f'ERROR: Could not load dot {dot_path}')
        print(f'{exception_to_msg(e)}: {e}')

        return

    print('Dot:', pkg.name)
    if pkg.description:
        print('Description:', pkg.description)

    variant = args.variant or 'default'
    variant_names = (f'*{v}' if v == variant else v for v in pkg.variants)

    print('Variants:', ', '.join(variant_names))

    print('Actions:')
    for action in pkg.actions:
        action = action.materialize()
        print(action.msg())


def cmd_help_actions(args):
    help_dict = get_actions_help()
    if not args.action:
        # list all actions

        print('Available actions:')
        for action, action_help in help_dict.items():
            try:
                desc = next(
                    line for line in action_help.split('\n')
                    if len(line.strip()))
            except Exception:
                desc = None

            line = action
            if desc:
                line += f': {desc}'

            print('-', line)
    else:
        if args.action not in help_dict:
            print(f'No such actoin `{args.action}`')
            return

        action_help = help_dict[args.action]
        print(f'Action `{args.action}`')
        print(action_help)

    print(args)


def main():
    parser = ArgumentParser(
        'dotdot',
        description='''A tool to manage dotfiles''')

    parser.add_argument('--verbose', '-v', action='store_true', default=False)

    parser.add_argument(
        '--dots-path',
        '-d',
        type=str,
        help='Path where dotfiles are stored')

    sub_parser = parser.add_subparsers(help='Avaiable commands')

    help_actions_parser = sub_parser.add_parser('help-actions')
    help_actions_parser.set_defaults(func=cmd_help_actions)
    help_actions_parser.add_argument('action', nargs='?')

    list_cmd_parser = sub_parser.add_parser('list')
    list_cmd_parser.set_defaults(func=cmd_list)

    show_cmd_parser = sub_parser.add_parser('show')
    show_cmd_parser.set_defaults(func=cmd_show)
    show_cmd_parser.add_argument('--variant', '-V', type=str, default=None)

    show_cmd_parser.add_argument(
        'dot',
        help='Dot to show',
    )

    install_cmd_parser = sub_parser.add_parser('install')
    install_cmd_parser.set_defaults(func=cmd_install)
    install_cmd_parser.add_argument('--variant', '-V', type=str, default=None)

    install_cmd_parser.add_argument('dot', help='Dots to install', nargs='+')

    args = parser.parse_args()
    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

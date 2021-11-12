import os
import textwrap
from argparse import ArgumentParser

from yaml.error import YAMLError

from dotdot.dot import Package
from dotdot.exceptions import InvalidActionType, InvalidPackageException


def exception_to_msg(ex: Exception) -> str:
    if isinstance(ex, InvalidPackageException):
        return f'path contains an invalid dot'
    elif isinstance(ex, YAMLError):
        return f'Invalid spec'
    elif isinstance(ex, InvalidActionType):
        return f'Spec contains invalid actions'
    else:
        return str(ex)


def cmd_list(args):
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
            pkgs.append(Package.from_dot_path(dot_path))
        except Exception as e:
            print(f'ERROR: Could not load dot {dot}')
            print(exception_to_msg(e))

            return

    for pkg in pkgs:
        print(f'Installing {pkg.name}')
        for action in pkg.actions:
            try:
                action = action.to_final_paths(pkg.package_path)
                print(action.msg())
                action.execute(dry_run=args.dry_run)
            except Exception as e:
                print('Error while executing action:', str(e))
                return



def main():
    parser = ArgumentParser(
        'dotdot',
        description='''A tool to manage dotfiles'''
    )

    parser.add_argument(
        '--dots-path', '-d', type=str,
        help='Path where dotfiles are stored'
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true',
        default=False
    )

    sub_parser = parser.add_subparsers(help='Avaiable commands')

    list_cmd_parser = sub_parser.add_parser('list')
    list_cmd_parser.set_defaults(func=cmd_list)

    install_cmd_parser = sub_parser.add_parser('install')
    install_cmd_parser.set_defaults(func=cmd_install)


    install_cmd_parser.add_argument(
        '--dry-run',
        help='Do not execute the actions',
        action='store_true',
        default=False
    )

    install_cmd_parser.add_argument(
        'dot',
        help='Dots to install',
        nargs='+'
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

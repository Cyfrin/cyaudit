import sys

from cyaudit import __main__


def main():
    __main__.main(sys.argv[1:])


def version() -> str:
    return __main__.get_version()

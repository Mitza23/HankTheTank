"""
The command-line interface for Hank
"""
import argparse

from .game_master import start


def main():
    parser = argparse.ArgumentParser(
        description="Hank The Tank - CS:GO Aiming Assistant\n" +
                    "A tool for automatically aiming and shooting in CS:GO\n\n" +
                    "K - start/stop the program\n\n" +
                    "F1 - change opponent team\n\n" +
                    "F2 - change aiming strategy\n\n" +
                    "F3 - toggle drawing mode(slows the process considerably)\n\n" +
                    "F4 - change spray time"
    )
    start()


if __name__ == "__main__":
    main()

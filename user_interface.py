import argparse
import asyncio
import logging
import os
import signal
import sys
from enum import Enum
from typing import TypeVar

from api import API
from botli_dataclasses import Challenge_Request
from config import Config
from engine import Engine
from enums import Challenge_Color, Perf_Type, Variant
from event_handler import Event_Handler
from game_manager import Game_Manager
from logo import LOGO

try:
    import readline
except ImportError:
    readline = None

COMMANDS = {
    'blacklist': 'Temporarily blacklists a user. Use config for permanent blacklisting. Usage: blacklist USERNAME',
    'challenge': 'Challenges a player. Usage: challenge USERNAME [TIMECONTROL] [COLOR] [RATED] [VARIANT]',
    'clear': 'Clears the challenge queue.',
    'create': 'Challenges a player to COUNT game pairs. Usage: create COUNT USERNAME [TIMECONTROL] [RATED] [VARIANT]',
    'help': 'Prints this message.',
    'leave': 'Leaves tournament. Usage: leave ID',
    'matchmaking': 'Starts matchmaking mode.',
    'quit': 'Exits the bot.',
    'rechallenge': 'Challenges the opponent to the last received challenge.',
    'reset': 'Resets matchmaking. Usage: reset PERF_TYPE',
    'stop': 'Stops matchmaking mode.',
    'tournament': 'Joins tournament. Usage: tournament ID [TEAM] [PASSWORD]',
    'whitelist': 'Temporarily whitelists a user. Use config for permanent whitelisting. Usage: whitelist USERNAME'
}

EnumT = TypeVar('EnumT', bound=Enum)

def get_lichess_token():
    """Lấy token từ file secrets hoặc biến môi trường"""
    token_path = "secrets/token.txt"  # Đường dẫn file chứa token
    
    # Thử đọc token từ file
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
            if token:
                return token
    
    # Nếu không có file, lấy từ biến môi trường
    token = os.getenv("LICHESS_KEY")
    if token:
        return token
    
    # Nếu không tìm thấy token, báo lỗi
    print("Error: LICHESS_KEY secret is not set in file or environment.")
    sys.exit(1)

class User_Interface:
    async def main(self,
                   config_path: str,
                   start_matchmaking: bool,
                   tournament_id: str | None,
                   tournament_team: str | None,
                   tournament_password: str | None,
                   allow_upgrade: bool) -> None:
        token = get_lichess_token()  # Lấy token từ file hoặc biến môi trường
        
        self.config = Config.from_yaml(config_path)
        self.config.token = token

        async with API(self.config) as self.api:
            print(f'{LOGO} {self.config.version}\n')

            account = await self.api.get_account()
            username: str = account['username']
            self.api.append_user_agent(username)
            await self._handle_bot_status(account.get('title'), allow_upgrade)
            await self._test_engines()

            self.game_manager = Game_Manager(self.api, self.config, username)
            self.game_manager_task = asyncio.create_task(self.game_manager.run())

            if tournament_id:
                self.game_manager.request_tournament_joining(tournament_id, tournament_team, tournament_password)

            self.event_handler = Event_Handler(self.api, self.config, username, self.game_manager)
            self.event_handler_task = asyncio.create_task(self.event_handler.run())

            if start_matchmaking:
                self._matchmaking()

            if not sys.stdin.isatty():
                signal.signal(signal.SIGINT, self.signal_handler)
                signal.signal(signal.SIGTERM, self.signal_handler)
                await self.game_manager_task
                return

            if readline and not os.name == 'nt':
                completer = Autocompleter(list(COMMANDS.keys()))
                readline.set_completer(completer.complete)
                readline.parse_and_bind('tab: complete')

            while True:
                command = (await asyncio.to_thread(input)).split()
                if len(command) == 0:
                    continue

                match command[0]:
                    case 'blacklist':
                        self._blacklist(command)
                    case 'challenge':
                        self._challenge(command)
                    case 'create':
                        self._create(command)
                    case 'leave':
                        self._leave(command)
                    case 'clear':
                        self._clear()
                    case 'exit' | 'quit':
                        await self._quit()
                        break
                    case 'matchmaking':
                        self._matchmaking()
                    case 'rechallenge':
                        self._rechallenge()
                    case 'reset':
                        self._reset(command)
                    case 'stop':
                        self._stop()
                    case 'tournament':
                        self._tournament(command)
                    case 'whitelist':
                        self._whitelist(command)
                    case _:
                        self._help()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', default='config.yml', type=str, help='Path to config.yml.')
    parser.add_argument('--matchmaking', '-m', action='store_true', help='Start matchmaking mode.')
    parser.add_argument('--tournament', '-t', type=str, help='ID of the tournament to be played.')
    parser.add_argument('--team', type=str, help='The team to join the tournament with, if one is required.')
    parser.add_argument('--password', type=str, help='The tournament password, if one is required.')
    parser.add_argument('--upgrade', '-u', action='store_true', help='Upgrade account to BOT account.')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging.')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.run(User_Interface().main(args.config,
                                      args.matchmaking,
                                      args.tournament,
                                      args.team,
                                      args.password,
                                      args.upgrade),
                debug=args.debug)

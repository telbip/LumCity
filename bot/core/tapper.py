import asyncio
import random

from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import time
from urllib.parse import unquote ,quote
import json
import re

from curl_cffi import requests

from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.raw import types
from bot.core.agents import generate_random_user_agent
from bot.core.headers import headers, get_sec_ch_ua


from bot.utils import logger
from bot.utils.logger import SelfTGClient
from bot.exceptions import InvalidSession
from bot.config import settings

self_tg_client = SelfTGClient()

class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.fullname = None
        self.start_param = None
        self.peer = None
        self.first_run = None
        self.scraper = None

        self.session_ug_dict = self.load_user_agents() or []

        user_agent = self.check_user_agent()
        headers['User-Agent'] = user_agent
        headers.update(**get_sec_ch_ua(user_agent))

    async def generate_random_user_agent(self):
        return generate_random_user_agent()

    def info(self, message):
        from bot.utils import info
        info(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def debug(self, message):
        from bot.utils import debug
        debug(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def check_timeout_error(self, error):
        try:
            error_message = str(error)
            is_timeout_error = re.search("504, message='Gateway Timeout'", error_message)
            return is_timeout_error
        except Exception as e:
            return False

    def check_error(self, error, message):
        try:
            error_message = str(error)
            is_equal = re.search(message, error_message)
            return is_equal
        except Exception as e:
            return False

    def warning(self, message):
        from bot.utils import warning
        warning(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def error(self, message):
        from bot.utils import error
        error(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def critical(self, message):
        from bot.utils import critical
        critical(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def success(self, message):
        from bot.utils import success
        success(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | User agent saved successfully")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = f'sessions/accounts.json'

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            if settings.USE_REF == True:
                ref_id = settings.REF_ID
            else:
                ref_id = random.choice(['T7B3IMWS'])

            self.start_param = random.choices([ref_id, 'T7B3IMWS'], weights=[70, 30], k=1)[0]
            peer = await self.tg_client.resolve_peer('LumCity_bot')

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url='https://lumcity.app/app'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            try:
                if self.user_id == 0:
                    information = await self.tg_client.get_me()
                    self.user_id = information.id
                    self.first_name = information.first_name or ''
                    self.last_name = information.last_name or ''
                    self.username = information.username or ''
            except Exception as e:
                self.error(f'Error during get tg web data: {e}')

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(
                f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def custom_quote(self, value):
        return ''.join(
            c if c.isalnum() or c in '-._~ ' else quote(c) if c != '"' else c for c in value)

    async def transform_input_string(self, input_string):
        parts = input_string.split('&')
        transformed_parts = []

        for part in parts:
            if part.startswith('user='):
                key, value = part.split('=', 1)
                encoded_value = await self.custom_quote(value)
                transformed_parts.append(f'{key}={encoded_value}')
            else:
                transformed_parts.append(part)

        transformed_string = '&'.join(transformed_parts)
        return transformed_string

    async def login(self, http_client, initdata):
        output_string = await self.transform_input_string(initdata)
        url = "https://back.lumcity.app/jwt/token?"


        for retry_count in range(settings.MAX_RETRIES):
            try:
                response = await http_client.get(url+output_string)

                response.raise_for_status()

                resp_json = response.json()

                if not resp_json.get('accessToken'):
                    self.error(f"Error during login | Invalid server response: {resp_json}")
                    return False

                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Login successful.")
                return resp_json.get("accessToken")

            except Exception as e:
                self.error(f"Error during login attempt {retry_count + 1}: {e}")
                await asyncio.sleep(delay=random.randint(5, 10))
                if retry_count == settings.MAX_RETRIES - 1:
                    await asyncio.sleep(delay=random.randint(5, 10))
                continue

        self.error("Login failed after max retries.")
        return False

    async def upgrade(self, http_client):
        url = "https://back.lumcity.app/miner-upgrades/all-upgrades"

        for retry_count in range(settings.MAX_RETRIES):
            try:
                await asyncio.sleep(delay=random.randint(3, 5))
                response = await http_client.get(url)

                response.raise_for_status()
                resp_json = response.json()
                return resp_json

            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    await asyncio.sleep(delay=random.randint(1, 3))
                continue

    async def upgrades(self, http_client):
        url = "https://back.lumcity.app/miner-upgrades/buy"
        data = {"type":"pickaxe","tokenId":1}
        for retry_count in range(settings.MAX_RETRIES):
            try:
                await asyncio.sleep(delay=random.randint(3, 5))
                response = await http_client.post(url, json=data)

                response.raise_for_status()
                resp_json = response.json()
                return response.status_code, resp_json.get('pickaxeLevel') if resp_json.get("success") else response.text

            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    await asyncio.sleep(delay=random.randint(1, 3))
                continue

    async def get_user_info(self, http_client):

        url = 'https://back.lumcity.app/miner/storage/balance/'
        for retry_count in range(settings.MAX_RETRIES):
            try:
                await asyncio.sleep(delay=2)
                response = await http_client.get(url)
                response.raise_for_status()

                user_data = response.json()
                return user_data

            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during getting user info: <light-yellow>{e}</light-yellow>")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue
        return None

    async def collect(self, http_client):

        url = 'https://back.lumcity.app/miner/'
        data = {}
        for retry_count in range(settings.MAX_RETRIES):
            try:
                await asyncio.sleep(delay=2)
                response = await http_client.post(url, json=data)
                response.raise_for_status()

                return response.status_code, float((response.json()).get('storage')) if response.status_code == 201 else response.text

            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during getting storage: <light-yellow>{e}</light-yellow>")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue

    async def get_storage(self, http_client):

        url = 'https://back.lumcity.app/balance/all'
        for retry_count in range(settings.MAX_RETRIES):
            try:
                await asyncio.sleep(delay=2)
                response = await http_client.get(url)
                response.raise_for_status()

                return (response.json()).get("balances")[1].get("amount")

            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during getting storage: <light-yellow>{e}</light-yellow>")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue

    async def check_proxy(self, http_client) -> None:
        try:

            response = await http_client.get('https://ipinfo.io/json', headers={}, timeout=5)

            response.raise_for_status()
            data = response.json()

            ip = data.get('ip')
            city = data.get('city')
            country = data.get('country')
            self.info(f"Check proxy! Country: <cyan>{country}</cyan> | City: <light-yellow>{city}</light-yellow> | Proxy IP: {ip}")
            return True
        except Exception as error:
            self.error(f"Proxy: 😢 Error: {error}")
            return False

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            self.info(f"Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(random_delay)

        access_token = None
        login_need = True

        http_client = requests.AsyncSession(impersonate="chrome124")
        http_client.headers.update(headers)

        if settings.USE_PROXY_FROM_FILE:
            proxys = {
                "http": proxy,
                "https": proxy
            }
            http_client.proxies = proxys

        self.access_token_created_time = 0
        self.token_live_time = random.randint(4000, 4600)
        tries_to_login = 3

        while True:
            try:
                if not await self.check_proxy(http_client):
                    self.error('Failed to connect to proxy server. Sleep 150 seconds.')
                    await asyncio.sleep(150)
                    continue
                if time() - self.access_token_created_time >= self.token_live_time:
                    login_need = True

                if login_need:
                    if "Authorization" in http_client.headers:
                        del http_client.headers["Authorization"]
                    self.info(f"Authorization")
                    init_data = await self.get_tg_web_data(proxy=proxy)
                    #await asyncio.sleep(delay=2000)
                    access_token = await self.login(http_client, init_data)
                    if not access_token:
                        return

                    http_client.headers['Authorization'] = f"Bearer {access_token}"

                    self.access_token_created_time = time()
                    self.token_live_time = random.randint(1500, 1900)


                    login_need = False

                await asyncio.sleep(3)

            except Exception as error:
                self.error(f"Unknown error during login: <light-yellow>{error}</light-yellow>")
                break

            try:
                await asyncio.sleep(delay=2)
                user_info = await self.get_user_info(http_client)
                await asyncio.sleep(delay=2)

                if user_info is not None:
                    if 'balance' in user_info:
                        miner_balance = user_info['balance']
                        self.info(f"Coin Balance: 💰 <light-green>{miner_balance}</light-green> 💰")
                        miner_balance = float(miner_balance)
                        if miner_balance >= 0.001:
                            status, balance = await self.collect(http_client)
                            if status == 201:
                                storage = float(await self.get_storage(http_client))
                                self.success(f"Collect GOLT! New balance: {storage}")
                            else:
                                self.error(f"Can't collect GOLT! Response {status}")
                                continue
                    await asyncio.sleep(delay=2)
                    miner_upgrades_data = await self.upgrade(http_client)
                    await asyncio.sleep(delay=2)

                    storage = float(await self.get_storage(http_client))
                    miner = miner_upgrades_data["pickaxeUpgrade"]
                    pickaxe_price = float(miner.get("priceGolt"))

                    await asyncio.sleep(delay=2)
                    if storage >= pickaxe_price:
                        status, storage = await self.upgrades(http_client)
                        if status == 201:
                            self.success(f"Upgraded miner! New balance: {storage}")
                        else:
                            self.error(f"Can't upgrade! Response {status}: {storage}")
                    else:
                        logger.info(f"Waiting for more GOLT. remaining: {pickaxe_price - storage}")

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💤 sleep 30 minutes 💤")
                await asyncio.sleep(delay=1800)

            except Exception as error:
                self.error(f"😢 Unknown error: <light-yellow>{error}</light-yellow>")
                await asyncio.sleep(delay=120)

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | 😢 Invalid Session 😢")

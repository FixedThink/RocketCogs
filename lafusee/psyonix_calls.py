# Used by Red.
import aiohttp
from redbot.core import Config


class PsyonixCalls:
    """Class for querying the Psyonix API asynchronically"""

    API_URL = "https://api.rocketleague.com/api/v1/{p}/"  # p= platform, uid=gamer-id
    API_GAS = API_URL + "leaderboard/stats/{t}/{uid}"  # {} * 3, t=GAS-type
    API_RANK = API_URL + "playerskills/{uid}"  # {} * 2
    API_TITLES = API_URL + "playertitles/{uid}"  # {} * 2

    PSY_TOKEN_NONE = ":x: Error: No token set for the Psyonix API."
    PSY_TOKEN_INVALID = ":x: Error: The Psyonix API token is invalid."

    PLAYER_ERROR = ":x: Error: That ID is not associated with an account that has played Rocket League.\n" \
                   "Please make sure the right account is used."
    CLIENT_ERROR = ":satellite: There was a connection error with the Rocket League API. " \
                   "Please try the command again in 10 seconds."
    TIMEOUT_ERROR = ":hourglass:  The request to the Rocket League API timed out. " \
                    "This means that the API might be down. Try again later."
    UNKNOWN_STATUS_ERROR = "Something went wrong whilst querying the Psyonix API.\nStatus: {}\n Query: {}"

    def __init__(self, cog):
        # Load config in order to always have an updated token.
        self.config = Config.get_conf(cog, identifier=80590423, force_registration=True)
        self.config.register_global(psy_token=None, steam_token=None)
        self.session = aiohttp.ClientSession()

    async def call_psyonix_api(self, request_url: str) -> tuple:
        """Given an url, call the API using the configured token

        Returns a list if valid, False if invalid, and None if there is no token.
        Also returns a error if there is one."""
        token = await self.config.psy_token()
        if token is None:
            to_return = False
            error = self.PSY_TOKEN_NONE
        else:
            headers = {"Authorization": token}
            try:
                async with self.session.get(request_url, headers=headers) as response:
                        resp = response
                        resp_status = resp.status
                        if resp_status == 200:   # Valid response.
                            resp_json = await resp.json()
                        else:
                            resp_json = None
            except aiohttp.client_exceptions.ClientConnectionError:
                to_return = False
                error = self.CLIENT_ERROR
            except aiohttp.client_exceptions.ServerTimeoutError:
                to_return = False
                error = self.TIMEOUT_ERROR
            else:
                if resp_json is not None:
                    if isinstance(resp_json, list):
                        resp_json = resp_json[0]
                    to_return = resp_json
                    error = None
                else:
                    to_return = False
                    if resp_status == 401:
                        error = self.PSY_TOKEN_INVALID
                    elif resp_status == 400:
                        error = self.PLAYER_ERROR
                    else:
                        raise Exception(self.UNKNOWN_STATUS_ERROR.format(resp_status, request_url))
        return to_return, error

    async def player_skills(self, platform: str, valid_id) -> tuple:
        """Composes the PlayerSkills query call, and returns its response

        Structure of a normal API response:
        {user_name: str, player_skills: [list of playlist_dict], user_id: str, season_rewards: {wins: int, level: int}}

        Structure of playlist_dict:
        {division: int, matches_played: int, mu: float, playlist: int, sigma: float,
        skill: int, tier: int, tier_max: int, win_steak: int}

        Note: the original response has the dict wrapped in a list, but the call method removes it.
        """
        request_url = self.API_RANK.format(p=platform, uid=valid_id)
        to_return, notice = await self.call_psyonix_api(request_url)
        return to_return, notice

    async def player_titles(self, platform: str, valid_id) -> tuple:
        """Composes the PlayerTitles query call, and returns its response

        Structure of a normal API response:
        {titles: [list of titles]}
        """
        request_url = self.API_TITLES.format(p=platform, uid=valid_id)
        response, notice = await self.call_psyonix_api(request_url)
        if notice:
            to_return = False
        else:
            to_return = response.get("titles", False)
        return to_return, notice
# Default library.
import asyncio
from collections import OrderedDict
from typing import Dict, List, Optional

# Used by Red.
import aiohttp

# Local imports.
from .exceptions import PsyonixCallError


class PsyonixCalls:
    """Class for querying the Psyonix API asynchronically"""
    ERROR = ":x: Error: "

    API_URL = "https://api.rocketleague.com/api/v1/{p}/"  # p=platform, uid=gamer-id
    API_GAS = API_URL + "leaderboard/stats/{t}/{uid}"  # {} * 3, t=GAS-type
    API_RANK = API_URL + "playerskills/{uid}"  # {} * 2
    API_TITLES = API_URL + "playertitles/{uid}"  # {} * 2

    GAS_LIST = ["goals", "assists", "saves", "wins", "mvps", "shots"]
    PSY_TOKEN_NONE = ERROR + "No token set for the Psyonix API."
    # Constants based on status codes.
    PLAYER_ERROR = ERROR + "That ID is not associated with an account that has played Rocket League.\n" \
                           "Please make sure the right account is used. `(Status: 400)`"
    PSY_TOKEN_INVALID = ERROR + "The Psyonix API token is invalid. `(Status: 401)`"
    SERVER_ERROR = ":satellite: The Rocket League API is experiencing issues. " \
                   "Please try the command again in 30 seconds. `(Status: {})`"
    LOOP_NOT_ALL_200 = ERROR + "One or more stats in the loop returned a non-200 status!"
    # Other request-based errors.
    TIMEOUT_ERROR = ":hourglass: The request to the Rocket League API timed out. " \
                    "This means that the API might be down. Try again later."
    UNKNOWN_STATUS_ERROR = ERROR + "Something went wrong whilst querying the Psyonix API.\n" \
                                   "See the console for the query in question. `(Uncaught status: {})`"
    # Other errors.
    NO_MATCHES = ERROR + "This account has purchased Rocket League, but has no online matches on record!"

    def __init__(self, config):
        # Load config in order to always have an updated token.
        self.config = config
        self.session = aiohttp.ClientSession()

    async def _fetch(self, request_url, headers) -> (Optional[List[dict]], int):
        """Send a get request to the Psyonix API, and fetch the response"""
        async with self.session.get(request_url, headers=headers) as response:
            resp = response
            resp_status = resp.status
            if resp_status == 200:  # Valid response.
                resp_json = await resp.json()
            else:
                resp_json = None
        return resp_json, resp_status

    async def _call_psyonix_api(self, request_url: str) -> dict:
        """Given an url, call the API using the configured token

        Returns a list if valid, False if invalid, and None if there is no token.
        Also returns a error if there is one."""
        token = await self.config.psy_token()
        if token is None:
            raise PsyonixCallError(self.PSY_TOKEN_NONE)
        headers = {"Authorization": token}
        try:
            resp_json, resp_status = await self._fetch(request_url, headers)
        except aiohttp.client_exceptions.ServerTimeoutError:
            raise PsyonixCallError(self.TIMEOUT_ERROR)
        if resp_status == 200:  # TODO: test if «resp_json is not None» is needed.
            if isinstance(resp_json, list):
                resp_json = resp_json[0]
            to_return = resp_json
        else:
            if resp_status == 401:
                raise PsyonixCallError(self.PSY_TOKEN_INVALID)
            if resp_status == 400:
                raise PsyonixCallError(self.PLAYER_ERROR)
            if resp_status in {500, 502}:
                raise PsyonixCallError(self.SERVER_ERROR.format(resp_status))
            print(request_url)
            raise PsyonixCallError(self.UNKNOWN_STATUS_ERROR.format(resp_status))
        return to_return

    async def player_skills(self, platform: str, valid_id,
                            ensure_played: bool = False) -> Optional[dict]:  # TODO: Check if optional
        """Composes the PlayerSkills query call, and returns its response

        if ensure_played is True, there will be a notice if the player_skills value is an empty list.

        Structure of a normal API response:
        {user_name: str, player_skills: [list of playlist_dict], user_id: str, season_rewards: {wins: int, level: int}}

        Structure of playlist_dict:
        {division: int, matches_played: int, mu: float, playlist: int, sigma: float,
        skill: int, tier: int, tier_max: int, win_steak: int}

        Note: the original response has the dict wrapped in a list, but the call method removes it.
        """
        request_url = self.API_RANK.format(p=platform, uid=valid_id)
        to_return = await self._call_psyonix_api(request_url)
        skills: List[Dict[str, Optional[float]]] = to_return.get("player_skills") if to_return else None
        if ensure_played and not skills:
            raise PsyonixCallError(self.NO_MATCHES)
        elif skills:  # Skills exist, replace nulls with 0. TODO: Maybe build in exception for raw.
            for d in skills:
                for k, v in d.items():
                    if v is None:
                        d[k] = 0
        return to_return

    async def player_titles(self, platform: str, valid_id) -> Optional[dict]:
        """Composes the PlayerTitles query call, and returns its response

        Structure of a normal API response:
        {titles: [list of titles]}
        """
        request_url = self.API_TITLES.format(p=platform, uid=valid_id)
        response = await self._call_psyonix_api(request_url)
        return response.get("titles")

    async def player_stat_values(self, platform: str, valid_id) -> OrderedDict:
        """Get all the six stats for a player: wins, MVPs, goals, assists, saves, and shots

        Structure of a normal API response (per individual stat):
        {user_id: str, stat_type: str, value: str}
        """
        token = await self.config.psy_token()
        if token is None:
            raise PsyonixCallError(self.PSY_TOKEN_NONE)
        headers = {"Authorization": token}
        tasks = []
        for i in self.GAS_LIST:
            url = self.API_GAS.format(p=platform, t=i, uid=valid_id)
            task = asyncio.ensure_future(self._fetch(url, headers))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)  # Structure: List[Tuple[List[dict]]]
        if any(status != 200 for d, status in responses):  # One or more values does not have status 200.
            print(responses)
            raise PsyonixCallError(self.LOOP_NOT_ALL_200)
        # Unpack gas-values to an OrderedDict.
        return OrderedDict((d["stat_type"], int(d["value"])) for (d,), status in responses)

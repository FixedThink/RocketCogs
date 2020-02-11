# Used by Red.
import aiohttp

# Local files.
from .exceptions import SteamCallError


class SteamCalls:
    """Class for querying the Steam API asynchronically"""
    # t = token, v = vanity url.
    API_VANITY = "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={t}&vanityurl={v}"
    STEAM_NO_MATCH = ":x: Error: That Steam vanity ID does not seem to exist. Please check your input."
    STEAM_TOKEN_NONE = ":x: Error: No token set for the Steam API."
    # Constants based on status codes.
    STEAM_BAD_REQUEST = ":x: Error: The request done to the Steam API was improper." \
                        "\nSee the console for more info. `(Status: 400)`"
    STEAM_TOKEN_INVALID = ":x: Error: The Steam API token is invalid. `(Status: 403)`"
    SERVER_ERROR = ":satellite: The Steam API is experiencing issues. Please try the command again. `(Status: {})`"
    # Other request-based errors.
    TIMEOUT_ERROR = ":hourglass: The request to the Steam API timed out. This means that the API might be down. " \
                    "Try to use the 17-digit number instead of the vanity ID, or try again later."
    UNKNOWN_STATUS_ERROR = "Something went wrong whilst querying the Steam API.\nStatus: {}\n Query: {}"

    def __init__(self, config):
        # Load config in order to always have an updated token.
        self.config = config
        self.session = aiohttp.ClientSession()

    async def _call_steam_api(self, request_url: str) -> dict:
        """Given an url, call the API using the configured token

        Returns a list if valid, False if invalid, and None if there is no token.
        Also returns a error if there is one."""
        try:
            async with self.session.get(request_url) as response:
                resp = response
                resp_status = resp.status
                if resp_status == 200:
                    resp_json = await resp.json()
                else:
                    resp_json = None
        except aiohttp.client_exceptions.ServerTimeoutError:
            raise SteamCallError(self.TIMEOUT_ERROR)
        if resp_json is not None:
            to_return = resp_json.get("response")
        else:  # No valid response.
            if resp_status == 403:
                raise SteamCallError(self.STEAM_TOKEN_INVALID)
            elif resp_status == 400:
                print("Invalid request URL: {}".format(request_url))
                raise SteamCallError(self.STEAM_BAD_REQUEST)
            elif resp_status in {500, 502, 503}:
                raise SteamCallError(self.SERVER_ERROR.format(resp_status))
            raise Exception(self.UNKNOWN_STATUS_ERROR.format(resp_status, request_url))
        return to_return

    async def vanity_to_id64(self, vanity_id: str) -> str:
        """Convert a Steam vanity id into an id64, so that it can be used in the Psyonix API

        Structure of a normal API response if there's a match:
        {response: {steamid: str, success: 1}}

        Structure of an API response if there's no match:
        {response: {message: "No match", success: 42}}
        """
        token = await self.config.steam_token()
        if token is None:
            raise SteamCallError(self.STEAM_TOKEN_NONE)
        request_url = self.API_VANITY.format(t=token, v=vanity_id)
        resp_dict = await self._call_steam_api(request_url)
        id64 = resp_dict.get("steamid")
        if not id64:  # No match found for steamid.
            raise SteamCallError(self.STEAM_NO_MATCH)
        return id64

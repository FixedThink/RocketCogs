# Used by Red.
import aiohttp
from redbot.core import Config


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

    def __init__(self, cog):
        # Load config in order to always have an updated token.
        self.config = Config.get_conf(cog, identifier=80590423, force_registration=True)
        self.config.register_global(psy_token=None, steam_token=None)
        self.session = aiohttp.ClientSession()

    async def call_steam_api(self, request_url: str) -> tuple:
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
            to_return = False
            error = self.TIMEOUT_ERROR
        else:
            if resp_json is not None:
                to_return = resp_json.get("response")
                error = None
            else:  # No valid response.
                to_return = False
                if resp_status == 403:
                    error = self.STEAM_TOKEN_INVALID
                elif resp_status == 400:
                    error = self.STEAM_BAD_REQUEST
                    print("Invalid request URL: {}".format(request_url))
                elif resp_status in {500, 502}:
                    error = self.SERVER_ERROR.format(resp_status)
                else:
                    raise Exception(self.UNKNOWN_STATUS_ERROR.format(resp_status, request_url))
        return to_return, error

    async def vanity_to_id64(self, vanity_id: str) -> tuple:
        """Convert a Steam vanity id into an id64, so that it can be used in the Psyonix API

        Structure of a normal API response if there's a match:
        {response: {steamid: str, success: 1}}

        Structure of an API response if there's no match:
        {response: {message: "No match", success: 42}}
        """
        token = await self.config.steam_token()
        if token is None:
            to_return = False
            notice = self.STEAM_TOKEN_NONE
        else:
            request_url = self.API_VANITY.format(t=token, v=vanity_id)
            resp_dict, notice = await self.call_steam_api(request_url)

            if notice:  # Error by call_steam_api.
                to_return = False
            else:  # Response is a dict.
                to_return = resp_dict.get("steamid", False)
                if not to_return:  # No match found for steamid.
                    notice = self.STEAM_NO_MATCH
        return to_return, notice

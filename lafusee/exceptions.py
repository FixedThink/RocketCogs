from redbot.core.commands import CommandError


class LaFuseeError(CommandError):
    """Generic error for the RL commands cog"""


class CustomNotice(LaFuseeError):
    """Generic custom command error"""
    pass


class AccountInputError(LaFuseeError):
    """Used when a platform-id couple yields an error"""
    pass


class PsyonixCallError(LaFuseeError):
    """Used when a call to the Psyonix API yields an error"""
    pass


class SteamCallError(LaFuseeError):
    """Used when a call to the Psyonix API yields an error"""
    pass


class TokenError(LaFuseeError):
    """Errors related to setting and using tokens"""
    pass

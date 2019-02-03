from typing import Optional, Tuple


# Platform tuples.  TODO: Eventually move all of this to a .json file.
PC_NAMES = {"pc", "steam"}
PS4_NAMES = {"ps4", "psn"}
XBOX_NAMES = {"xbox", "xb1", "xboxone"}
SWITCH_NAMES = {"switch", "nintendo", "swi", "nintendoswitch"}
# Constants.
EMBED_DIVMOD_COLOURS = {0: 0xca8700, 1: 0xdadada, 2: 0x909090, 3: 0xddbb20, 4: 0x10bbee,
                        5: 0x10abcd, 6: 0xaa60dd, 7: 0xbb00bb}
TIER_DIVMOD_NAMES = {0: "Unranked", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum",
                     5: "Diamond", 6: "Champion", 7: "Grand Champion"}
ROMAN_NUMS = {1: "I", 2: "II", 3: "III", 4: "IV"}


def best_playlist(player_skills: dict) -> Tuple[int, Optional[int], set]:  # TODO: review whether first int is optional.
    """
    :param player_skills: A dict with a player's skills.
    :return: A tuple containing the player's best rank, playlist, and what lists they've played in.
    """
    # Check which playlists have data and which ones not.
    played_lists = {d["playlist"] for d in player_skills}
    # Get highest ranked playlist (only if there's data for any ranked playlist).
    if any(n != 0 for n in played_lists):
        best_playlist_dict = max((d for d in player_skills if d["playlist"] != 0),
                                 key=lambda x: (x["tier"], x["division"], x["mu"]))
        best_tier = best_playlist_dict.get("tier")
        best_list_id = best_playlist_dict.get("playlist")
    else:
        best_tier = 0
        best_list_id = None
    return best_tier, best_list_id, played_lists


def com(ctx, command, tick: bool = True) -> str:
    """
    :param ctx: The context manager as provided by the command. Used for the prefix.
    :param command: The command for which the command link should be made.
    :param tick: (Optional) Whether to surround the command with backticks (`). Defaults to False.
    :return: A string in with a readable command link (excluding any code blocks).

    Make a string to refer to another command
    """
    return "{t}{p}{com}{t}".format(p=ctx.prefix, com=command.qualified_name, t="`" if tick else "")


def get_tier_colour(tier_n: int) -> int:
    """
    :param tier_n: The tier number.
    :return: A hex code for the colour of the rank embed.
    """
    colour_key = (tier_n + 2) // 3  # For unranked: (0 + 2) // 3 == 0
    return EMBED_DIVMOD_COLOURS[colour_key]


def get_tier_name(tier_n: int) -> str:
    """
    :param tier_n: tier number
    :return: tier name
    """
    """Based on a tier number, get the tier name"""
    key, div = divmod((tier_n + 2), 3)
    if key in (0, 7):
        to_return = TIER_DIVMOD_NAMES[key]
    else:
        to_return = " ".join((TIER_DIVMOD_NAMES[key], ROMAN_NUMS[div + 1]))
    return to_return


def get_url_platform(platform_in: str):
    """
    :param platform_in: a string with the platform as put in by the user.
    :return: The platform string needed for an API request.
    """
    to_check = platform_in.lower()
    if to_check in PC_NAMES:
        to_return = "steam"
    elif to_check in PS4_NAMES:
        to_return = "ps4"
    elif to_check in XBOX_NAMES:
        to_return = "xboxone"
    elif to_check in SWITCH_NAMES:
        to_return = "switch"  # Currently not supported by API.
    else:  # No matching platform found.
        to_return = False
    return to_return

from typing import Optional, Tuple


def _use_plist(check_d: dict, allow_special: bool = True) -> bool:
    """
    :param check_d: Dict of a playlist-specific player skills.
    :param allow_special: Whether to count special playlists or not
    :return: A boolean determining whether the playlist should be considered.
    """
    to_check = check_d["playlist"]
    return to_check != 0 if allow_special else 0 < to_check < 20


def best_playlist(player_skills: list, allow_special: bool = True) -> Tuple[int, Optional[int], set]:
    """    # TODO: review whether first int in type hint is optional.
    :param player_skills: A list with a player's skills (extracted from the skills response dict).
    :param allow_special: Whether to count special playlists or not
    :return: A tuple containing the player's best rank, playlist, and what lists they've played in.
    """
    # Check which playlists have data and which ones not.
    played_lists = {d["playlist"] for d in player_skills}
    # Get highest ranked playlist (only if there's data for any ranked playlist).
    if any(n != 0 for n in played_lists):
        best_playlist_dict = max((d for d in player_skills if _use_plist(d, allow_special)),
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


def float_sr(skills_item: dict) -> float:
    """
    :param skills_item: An item of the "player_skills" list in the PlayerSkills API response dict.
    :return: Skill rating in float format.
    """
    return skills_item["mu"] * 20 + 100

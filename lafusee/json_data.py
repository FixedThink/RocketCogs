# Default library.
import json
import os
from typing import Optional, Dict


def _json_key_to_int(to_convert: dict) -> dict:
    """Converts the keys of a (JSON) dictionary to integers"""
    return {int(k): v for k, v in to_convert.items()}


class GetJsonData:
    """Obtains the data to be retrieved from the conversion dict json"""
    CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
    DATA_FOLDER = CURRENT_FOLDER + "/Data/"
    JSON_PATH = DATA_FOLDER + "conversion_dicts.json"
    PLAYLIST_ID_SET = {0, 10, 11, 12, 13, 27, 28, 29, 30}
    MODE_DICT = {1: "short", 2: "medium", 3: "long"}

    def __init__(self):
        with open(self.JSON_PATH, 'r') as f:
            json_dict = json.load(f)
        self.divmod_colours: Dict[int, str] = _json_key_to_int(json_dict["embed_divmod_colours"])
        self.divmod_tiers: Dict[int, str] = _json_key_to_int(json_dict["tier_divmod_names"])
        self.icons: Dict[int, str] = _json_key_to_int(json_dict["tier_icons"])
        self.roman_nums: Dict[int, str] = _json_key_to_int(json_dict["roman_numerals"])
        self.str_to_platform: Dict[str, list] = json_dict["platform_convert"]
        self.str_to_playlist: Dict[str, int] = json_dict["playlist_convert"]
        self.int_to_plist_str: Dict[str, Dict[int, str]] = {}  # To be filled.
        for k, v in json_dict["playlist_names"].items():  # Manually unpack nested dict to convert str keys to int.
            self.int_to_plist_str[k] = _json_key_to_int(v)

    def get_input_platform(self, platform_in: str) -> Optional[str]:
        """
        :param platform_in: a string with the platform as put in by the user.
        :return: The platform string needed for an API request.
        """
        to_return = None  # Default value (if no matching platform found).
        to_check = platform_in.lower()
        if to_check in self.str_to_platform["pc_names"]:
            to_return = "steam"
        elif to_check in self.str_to_platform["ps4_names"]:
            to_return = "ps4"
        elif to_check in self.str_to_platform["xbox_names"]:
            to_return = "xboxone"
        elif to_check in self.str_to_platform["switch_names"]:
            to_return = "switch"  # Currently not supported by API.
        return to_return

    def get_input_playlist(self, playlist_str: str) -> Optional[int]:
        """
        :param playlist_str: a string with the playlist as put in by the user
        :return: The playlist ID (int) if there is a match, None otherwise.
        """
        try:  # Allow people to put in actual playlist IDs too.
            playlist_int = int(playlist_str)
        except ValueError:  # Validate playlist using conversion dict.
            to_return = self.str_to_playlist.get(playlist_str.lower(), None)
        else:
            to_return = playlist_int if playlist_int in self.PLAYLIST_ID_SET else None
        return to_return

    def get_tier_colour(self, tier_n: int) -> int:
        """
        :param tier_n: The tier number.
        :return: A hex code for the colour of the rank embed.
        """
        colour_key = (tier_n + 2) // 3  # For unranked: (0 + 2) // 3 == 0
        return int(self.divmod_colours[colour_key], 16)  # 0x-values stored as string.

    def get_tier_icon(self, tier_n: int) -> str:
        """
        :param tier_n: The tier number.
        :return: A string with the image link.
        """
        return self.icons[tier_n]

    def get_tier_name(self, tier_n: int) -> str:
        """
        :param tier_n: tier number
        :return: tier name
        """
        key, div = divmod((tier_n + 2), 3)
        if key in (0, 7):
            to_return = self.divmod_tiers[key]
        else:
            to_return = " ".join((self.divmod_tiers[key], self.roman_nums[div + 1]))
        return to_return

    def get_playlist_name(self, playlist_id: int, mode: int = 2) -> str:
        """
        :param playlist_id:
        :param mode:
        :return:
        """
        assert 1 <= mode <= 3, "The mode int must be 1, 2, or 3."
        mode_str = self.MODE_DICT[mode]
        return self.int_to_plist_str[mode_str][playlist_id]

    def tier_div_str(self, skills_item: dict) -> str:
        """
        :param skills_item: An item (playlist) of the "player_skills" list in the PlayerSkills API response dict.
        :return: A string depicting that playlist's tier and division (if applicable).
        """
        tier_n = skills_item["tier"]
        div = skills_item["division"] + 1
        tier = self.get_tier_name(tier_n)
        return "{} Div. {}".format(tier, div) if tier_n not in (0, 19) else tier

    def reward_level_str(self, response: dict) -> str:
        """
        :param response: The PlayerSkills API response dict
        :return: A player's Season Rewards level summarised into a string
        """
        rewards = response["season_rewards"]
        level, wins = rewards["level"], rewards["wins"]
        if level:
            level_str = self.divmod_tiers[level]
            bonus_str = " (+{})".format(wins) if level != 7 else ""
            to_return = "{}{}".format(level_str, bonus_str)
        else:
            to_return = "*None*"
        return to_return

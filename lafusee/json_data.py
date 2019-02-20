# Default library.
import json
import os
from typing import Optional


def _json_key_to_int(to_convert: dict) -> dict:
    """Converts the keys of a (JSON) dictionary to integers"""
    return {int(k): v for k, v in to_convert.items()}


class GetJsonData:
    """Obtains the data to be retrieved from the conversion dict json"""
    CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
    DATA_FOLDER = CURRENT_FOLDER + "/Data/"
    JSON_PATH = DATA_FOLDER + "conversion_dicts.json"

    def __init__(self):
        with open(self.JSON_PATH, 'r') as f:
            json_dict = json.load(f)
        self.divmod_colours = _json_key_to_int(json_dict["embed_divmod_colours"])
        self.divmod_tiers = _json_key_to_int(json_dict["tier_divmod_names"])
        self.icons = _json_key_to_int(json_dict["tier_icons"])
        self.roman_nums = _json_key_to_int(json_dict["roman_numerals"])
        self.platform_convert = json_dict["platform_convert"]

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

    def get_url_platform(self, platform_in: str) -> Optional[str]:
        """
        :param platform_in: a string with the platform as put in by the user.
        :return: The platform string needed for an API request.
        """
        to_return = None  # Default value (if no matching platform found).
        to_check = platform_in.lower()
        if to_check in self.platform_convert["pc_names"]:
            to_return = "steam"
        elif to_check in self.platform_convert["ps4_names"]:
            to_return = "ps4"
        elif to_check in self.platform_convert["xbox_names"]:
            to_return = "xboxone"
        elif to_check in self.platform_convert["switch_names"]:
            to_return = "switch"  # Currently not supported by API.
        return to_return

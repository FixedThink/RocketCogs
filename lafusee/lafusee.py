# Default libraries.
import re

# Used by Red.
import discord
from discord.ext import commands
from redbot.core import checks, Config, data_manager

# Local files.
from .psyonix_calls import PsyonixCalls
from .steam_calls import SteamCalls
from .db_queries import DbQueries


class LaFusee:
    """Rocket League rank commands."""
    # TODO: move methods and their constants to a separate file.
    # Constants.
    EMBED_DIVMOD_COLOURS = {0: 0xca8700, 1: 0xdadada, 2: 0x909090, 3: 0xddbb20, 4: 0x10bbee,
                            5: 0x10abcd, 6: 0xaa60dd, 7: 0x602090}
    TIER_DIVMOD_NAMES = {0: "Unranked", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum",
                         5: "Diamond", 6: "Champion", 7: "Grand Champion"}
    ROMAN_NUMS = {1: "I", 2: "II", 3: "III", 4: "IV"}
    # Platform tuples.
    PC_NAMES = {"pc", "steam"}
    PS4_NAMES = {"ps4", "psn"}
    XBOX_NAMES = {"xbox", "xb1", "xboxone"}
    SWITCH_NAMES = {"switch", "nintendo", "swi", "nintendoswitch"}

    PLAYLIST_ID_TO_NAME = {0: "Casual", 10: "Ranked Duel 1v1", 11: "Ranked Doubles 2v2",
                           12: "Ranked Solo Standard 3v3", 13: "Ranked Standard 3v3"}
    PLAYLIST_ID_MINIMAL = {0: "Casual", 10: "Duels", 11: "Doubles", 12: "Solo 3s", 13: "Standard"}
    PLAYLIST_ID_SHORT = {0: "Casual", 10: "1s", 11: "2s", 12: "s3s", 13: "3s"}
    # Token command notices.
    TOKEN_ADDED = "Successfully set the token for the {} API."
    TOKEN_DELETED = "Successfully cleared the token for the {} API."
    TOKEN_NONE = ":x: Error: No token set."
    TOKEN_NOT_SET = TOKEN_NONE + "Which makes deleting it a little complicated."
    TOKEN_LEN_ERROR = ":x: Error: The token you put in is not as long as the accepted token size ({})."
    TOKEN_HEX_ERROR = ":x: Error: Your input does not seem to be hexadecimal."
    TOKEN_NOT_PRIVATE = ":warning: Because of safety reasons, please send the bot this command in DMs. Input ignored."
    TOKEN_INVALID = ":x: Error: Token is invalid."
    # RL rank role constants.
    ROLE_DISABLED = ":put_litter_in_its_place: Successfully disabled the RL rank role functionality for this server."
    ROLE_ENABLED = ":white_check_mark: Successfully enabled the RL rank role functionality for this server."
    ROLESET_SUCCESS = ":white_check_mark: Successfully added all roles!"
    ROLE_NOT_ENABLED = "Don't forget to enable the RL rank role functionality by doing `{}{}`"
    ROLE_NOT_COMPLETE = "You can either add each missing role individually using `{}{}`, " \
                        "or rerun this command when all roles are set up."
    # Other API constants.
    PSY_TOKEN_LEN = 40
    STEAM_TOKEN_LEN = 32
    # Minimal embed constants.
    MINIMAL_ONLY_MMR = "`{:<8}\u200b`  **{:0.2f}**"
    MINIMAL_RANKED = "`{ls:<8}\u200b`  **{n:0.2f}**  ({bold}{tier_div}{bold})"
    MINIMAL_NO_MATCHES = "`{:<8}\u200b`  *No matches played*"
    # Other constants.
    STEAM_PROFILE_URL = "https://steamcommunity.com/profiles/{}"
    ID64_NON_NUMERIC = ":x: Error: `/profiles/` links must have a fully numeric id!"

    def __init__(self, bot):
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/account_registrations.db"
        self.config = Config.get_conf(self, identifier=80590423, force_registration=True)
        self.config.register_global(psy_token=None, steam_token=None)
        # Structure of rankrole_dict: {tier_n: role_id}
        self.config.register_guild(rankrole_enabled=False, rankrole_dict={})
        self.psy_api = PsyonixCalls(self)
        self.steam_api = SteamCalls(self)
        self.link_db = DbQueries(self.PATH_DB)

    # Configuration commands.
    @checks.mod_or_permissions(administrator=True)
    @commands.group(name="rl_api", invoke_without_command=True)
    async def _api_config(self, ctx):
        """Configure the API keys needed for the RL commands"""
        await ctx.send_help()

    @_api_config.command()
    @checks.mod_or_permissions(administrator=True)
    async def set_psyonix_token(self, ctx, token):
        """Configures the token required to query the Psyonix API

        Only the hexadecimal code is needed."""
        msg = ctx.message
        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            try:
                await msg.delete()  # Delete message immediately if not sent in DMs.
            except discord.errors.Forbidden:
                print("No perms to delete message")
            notice = self.TOKEN_NOT_PRIVATE
        else:
            if len(token) == self.PSY_TOKEN_LEN:
                try:
                    int(token, 16)  # Token is a valid hexadecimal string.
                    str_token = "Token {}".format(token)
                    await self.config.psy_token.set(str_token)
                    notice = self.TOKEN_ADDED.format("Psyonix")
                except ValueError:
                    notice = self.TOKEN_HEX_ERROR
            else:
                notice = self.TOKEN_LEN_ERROR.format(self.PSY_TOKEN_LEN)
        await ctx.send(notice)

    @_api_config.command()
    @checks.mod_or_permissions(administrator=True)
    async def delete_psyonix_token(self, ctx):
        """Removes the currently set token from the config"""
        token = await self.config.psy_token()
        if token is not None:
            await self.config.psy_token.clear()
            notice = self.TOKEN_DELETED.format("Psyonix")
        else:
            notice = self.TOKEN_NOT_SET
        await ctx.send(notice)

    @_api_config.command()
    @checks.mod_or_permissions(administrator=True)
    async def set_steam_token(self, ctx, token):
        """Configures the token required to query the Steam API

        Only the hexadecimal code is needed."""
        msg = ctx.message
        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            try:
                await msg.delete()  # Delete message immediately if not sent in DMs.
            except discord.errors.Forbidden:
                print("No perms to delete message")
            notice = self.TOKEN_NOT_PRIVATE
        else:
            if len(token) == self.STEAM_TOKEN_LEN:
                try:
                    int(token, 16)  # Token is a valid hexadecimal string.
                    await self.config.steam_token.set(str(token))
                    notice = self.TOKEN_ADDED.format("Steam")
                except ValueError:
                    notice = self.TOKEN_HEX_ERROR
            else:
                notice = self.TOKEN_LEN_ERROR.format(self.STEAM_TOKEN_LEN)
        await ctx.send(notice)

    @_api_config.command()
    @checks.mod_or_permissions(administrator=True)
    async def delete_steam_token(self, ctx):
        """Removes the currently set token from the config"""
        token = await self.config.steam_token()
        if token is not None:
            await self.config.steam_token.clear()
            notice = self.TOKEN_DELETED.format("Steam")
        else:
            notice = self.TOKEN_NOT_SET
        await ctx.send(notice)

    @checks.mod_or_permissions(administrator=True)
    @commands.group(name="rl_role", invoke_without_command=True)
    async def _rl_role(self, ctx):
        """Configure the RL rank role configuration for this server"""
        await ctx.send_help()

    @_rl_role.command(name="toggle")
    @checks.mod_or_permissions(administrator=True)
    async def toggle_rl_role(self, ctx):
        """Toggles the RL rank role functionality"""
        is_enabled = await self.config.guild(ctx.guild).rankrole_enabled()
        if is_enabled:
            to_send = self.ROLE_DISABLED
        else:
            to_send = self.ROLE_ENABLED
        # Set rankrole_enabled as the inverse of is_enabled (as this command is a toggle).
        await self.config.guild(ctx.guild).rankrole_enabled.set(not is_enabled)
        await ctx.send(to_send)

    @_rl_role.command(name="set")
    @checks.mod_or_permissions(administrator=True)
    async def set_rl_role(self, ctx, mode: str):
        """Toggles the RL rank role functionality

        There are two possible modes:
        **generate** - creates new rank roles and automatically saves them
        **detect** - detects existing roles based on their name.

        For `detect`, the role names must have proper capitalization and roman numerals, like \"Diamond III\"."""
        gld = ctx.guild
        low_mode = mode.lower()
        if low_mode == "generate":
            role_dict = {}
            if gld.me.guild_permissions.manage_roles is False:
                to_say = ":x: Error: I do not have sufficient permissions to add roles."
            else:
                for i in reversed(range(1, 20)):  # Reversed because of hierarchy.
                    role_colour = discord.Colour(self.get_tier_colour(i))
                    role_name = self.get_tier_name(i)
                    new_role = await gld.create_role(name=role_name, colour=role_colour, hoist=True)
                    role_dict[i] = new_role.id
                    if i % 5 == 0:
                        await ctx.send(f"{i} out of 19 roles done.")
                to_say = self.ROLESET_SUCCESS
            await self.config.guild(gld).rankrole_dict.set(role_dict)
        elif low_mode == "detect":
            role_dict = {}
            say_list = []
            matches = 0
            for i in range(1, 20):
                tier_str = self.get_tier_name(i)
                role = discord.utils.get(gld.roles, name=tier_str)
                if role:
                    matches += 1
                    role_id = role.id
                    role_dict[i] = role_id
                    say_list.append(f":white_check_mark: Detected `{role_id}` for {tier_str}")
                else:
                    role_dict[i] = None
                    say_list.append(f":x: Did not find a role for {tier_str}")
            if matches < 19:
                comment = self.ROLE_NOT_COMPLETE  # TODO: add manual command.
            elif await self.config.guild(gld).rankrole_enabled() is False:
                comment = self.ROLE_NOT_ENABLED.format(ctx.prefix, self.toggle_rl_role.qualified_name)
            else:
                comment = self.ROLESET_SUCCESS
            to_say = "**Total matches:** {} out of 19\n{}\n\n{}".format(matches, comment, "\n".join(say_list))
            await self.config.guild(gld).rankrole_dict.set(role_dict)
        else:
            to_say = ":x: Error: Invalid mode."
        await ctx.send(to_say)

    # Request commands.
    @commands.command(name="lfg")
    @checks.mod_or_permissions(administrator=True)
    async def minimal(self, ctx, platform, profile_id):
        """Minimal embed test"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            query, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                player_name = query["user_name"]
                player_skills = query.get("player_skills")
                if not player_skills:  # Debug exception.
                    raise Exception("lfg -> No player skills")
                # TODO: make everything below this line a method, in order to support `[p]lfg me` later on.
                best_tier, best_list_id, played_lists = self.best_playlist(player_skills)
                unplayed_lists = {n for n in (0, 10, 11, 12, 13) if n not in played_lists}
                # Create rows for each playlist.
                rank_summary = self.rank_summary_str(player_skills, best_list_id, unplayed_lists)
                # Create embed, whilst using the highest tier's colour.
                embed = discord.Embed()
                embed.colour = self.get_tier_colour(best_tier)
                # Set author and description. Profile links only exist for Steam.
                player_url = self.STEAM_PROFILE_URL.format(query["user_id"]) \
                    if url_platform == "steam" else discord.Embed.Empty
                embed.set_author(name="Rocket League Stats - {}".format(player_name), url=player_url)
                embed.description = rank_summary
                await ctx.send(embed=embed)
        if notice:
            await ctx.send(notice)

    # Debug commands.
    @checks.is_owner()
    @commands.group(name="rltest", invoke_without_command=True)
    async def _tests(self, ctx):
        """Debug commands for the RL module"""
        await ctx.send_help()

    @_tests.command(name="skills")
    @checks.mod_or_permissions(administrator=True)
    async def skills_test(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerSkills query"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            response, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                str_list = []
                for k, v in response.items():
                    str_row = "`{}`: {}".format(k, v)
                    str_list.append(str_row)
                await ctx.send("\n".join(str_list))
        # Send a notice if the call was invalid.
        if notice:
            await ctx.send(notice)

    @_tests.command(name="titles")
    @checks.mod_or_permissions(administrator=True)
    async def titles_test(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerTitles query"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            response, notice = await self.psy_api.player_titles(url_platform, url_id)
            if not notice:
                await ctx.send(response)
        # Send a notice if the call was invalid.
        if notice:
            await ctx.send(notice)

    @_tests.command(name="raw")
    @checks.is_owner()
    async def raw_skills(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerSkills query"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            response, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                await ctx.send(response)
        # Send a notice if the call was invalid.
        if notice:
            await ctx.send(notice)

    @_tests.command(name="vanity")
    @checks.is_owner()
    async def test_vanity(self, ctx, vanity_id):
        """Used for testing the Steam API vanity id conversion"""
        response, notice = await self.steam_api.vanity_to_id64(vanity_id)
        await ctx.send("{}\n{}".format(response, notice))

    @_tests.command(name="user_bundle")
    @checks.is_owner()
    async def test_platform_id_bundle(self, ctx, platform, profile_id):
        """Used for testing the platform - gamerID bundle"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        await ctx.send("{} - {} \n{}".format(url_platform, url_id, notice))

    @_tests.command(name="re")
    @checks.is_owner()
    async def test_regex_split(self, ctx, steam_url):
        """Used for testing regex for the platform bundle"""
        id_split = re.split(r'/id/', steam_url, maxsplit=1)
        profiles_split = re.split(r'/profiles/', steam_url, maxsplit=1)

        if len(id_split) == 2:  # Means that a split took place.
            to_say = id_split[-1].rstrip("/")
        elif len(profiles_split) == 2:
            to_say = profiles_split[-1].rstrip("/")
        else:
            to_say = "`{}` could not be split".format(steam_url)
        await ctx.send(to_say)

    @_tests.command(name="colour")
    async def test_embed_colour(self, ctx, hex_code):
        """Test embed colours"""
        embed = discord.Embed(title="Tell me, black or white?", colour=int(hex_code, 16))
        embed.description = "Hi\nHELLLLOOOOOOO\nOk."
        embed.set_footer(text="Hex code: {}".format(hex_code))
        await ctx.send(embed=embed)

    # Utilities
    async def platform_id_bundle(self, platform_in: str, id_in: str):
        """Verify the input of a platform and gamer id

        By default, number input for id_in (for Steam) will be treated as an id3/id64.
        In order to use vanity id that consists solely of digit, it must be prefixed with /id/"""
        notice = None
        platform_out = self.get_url_platform(platform_in)
        if not platform_out:
            notice = ":x: Error: that platform does not exist."
        elif platform_out == "switch":
            platform_out = False
            notice = ":x: Error: Psyonix does not (yet) support rank queries for the Nintendo Switch. " \
                     "When they do, we will make sure to add support for it."
        if notice:
            id_out = False
        else:  # Valid platform.
            if platform_out == "steam":
                if id_in.lstrip("-").isdigit():
                    id_out = self.int_to_steam_id64(int(id_in))
                else:
                    # Do regex checks for /id/ and /profiles/.
                    re_split_a = re.split(r'/profiles/', id_in, maxsplit=1)
                    re_split_b = re.split(r'/id/', id_in, maxsplit=1)
                    if len(re_split_a) == 2:  # Successful split, so a match.
                        clean_id = re_split_a[-1].rstrip("/")
                        try:
                            id_out = self.int_to_steam_id64(int(clean_id))
                        except ValueError:
                            id_out = False
                            notice = self.ID64_NON_NUMERIC
                    elif len(re_split_b) == 2:
                        clean_id = re_split_b[-1].rstrip("/")
                        id_out, notice = await self.steam_api.vanity_to_id64(clean_id)
                    else:
                        id_out, notice = await self.steam_api.vanity_to_id64(id_in)
            else:
                id_out = id_in
        return platform_out, id_out, notice

    def int_to_steam_id64(self, id_64: int) -> int:
        """Converts a SteamID64 to the one that the Psyonix API recognizes

        The reason for this is that Valve accepts multiple ID64s for the same account."""
        return (id_64 % (2 ** 32)) + 76561197960265728

    def get_url_platform(self, platform_in: str):
        """returns the appropriate platform string for an API request."""
        to_check = platform_in.lower()
        if to_check in self.PC_NAMES:
            to_return = "steam"
        elif to_check in self.PS4_NAMES:
            to_return = "ps4"
        elif to_check in self.XBOX_NAMES:
            to_return = "xboxone"
        elif to_check in self.SWITCH_NAMES:
            to_return = "switch"  # Currently not supported by API.
        else:  # No matching platform found.
            to_return = False
        return to_return

    def best_playlist(self, player_skills: dict) -> tuple:
        """Given a dict with a player's skills, return their best rank, playlist, and what lists they've played in"""
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

    def rank_summary_str(self, player_skills: dict, best_list_id: int, unplayed_lists: set) -> str:
        """Return a string with a player's summarized rank in a given playlist

        player_skills must be a dict that is provided by the API, or None if there are no stats.
        best_list_id is the number of the playlist in which the user has the highest ranking.
        unplayed_lists is a set of the playlists which the user has not played in."""
        desc_rows = {}
        for i in player_skills:
            rating = i["mu"] * 20 + 100
            playlist_id = i["playlist"]
            playlist = self.PLAYLIST_ID_MINIMAL[playlist_id]
            if playlist_id == 0:  # == casual.
                playlist_str = self.MINIMAL_ONLY_MMR.format(playlist, rating)
            else:
                tier_n = i["tier"]
                tier = self.get_tier_name(tier_n)
                div = i["division"] + 1
                # Embolden best playlist.
                bold = "**" if playlist_id == best_list_id else ""
                tier_div = "{} Div. {}".format(tier, div) if tier_n not in (0, 19) else tier
                playlist_str = self.MINIMAL_RANKED.format(ls=playlist, n=rating, bold=bold, tier_div=tier_div)
            desc_rows[playlist_id] = playlist_str
        for n in unplayed_lists:
            playlist = self.PLAYLIST_ID_MINIMAL[n]
            desc_rows[n] = self.MINIMAL_NO_MATCHES.format(playlist)
        to_return = "\n".join(v for k, v in sorted(desc_rows.items()))
        return to_return

    def get_tier_colour(self, tier_n: int):
        """Get the colour for the rank embed based on a tier number."""
        colour_key = (tier_n + 2) // 3  # For unranked: (0 + 2) // 3 == 0
        return self.EMBED_DIVMOD_COLOURS[colour_key]

    def get_tier_name(self, tier_n: int):
        """Based on a tier number, get the tier name"""
        key, div = divmod((tier_n + 2), 3)
        if key in (0, 7):
            to_return = self.TIER_DIVMOD_NAMES[key]
        else:
            to_return = " ".join((self.TIER_DIVMOD_NAMES[key], self.ROMAN_NUMS[div + 1]))
        return to_return

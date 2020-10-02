# Default libraries.
import re
from collections import OrderedDict
from json import dumps  # Only used for debug output formatting.
from typing import List, Literal, Optional

# Used by Red.
import discord
import redbot.core.utils.menus as red_menu
from redbot.core import checks, Config, data_manager
from redbot.core import commands
from redbot.core.bot import Red

from .db_queries import DbQueries
# Local files.
from .exceptions import CustomNotice, LaFuseeError, AccountInputError, TokenError, PsyonixCallError
from .json_data import GetJsonData
from .psyonix_calls import PsyonixCalls
from .static_functions import best_playlist, com, float_sr
from .steam_calls import SteamCalls


class LaFusee(commands.Cog):
    """Rocket League rank commands"""
    # TODO: Give notice about spaces when someone with xbox puts in their ID wrongly. (or fix with *).
    # Constants.
    PSY_TOKEN_LEN = 40
    STEAM_TOKEN_LEN = 32
    PLAYLIST_IDS = (0, 10, 11, 12, 13, 27, 28, 29, 30)

    # Emotes used in constants.
    BIN = ":put_litter_in_its_place: "
    ERROR = ":x: Error: "
    DONE = ":white_check_mark: "
    # Token command notices.
    TOKEN_ADDED = "Successfully set the token for the {} API."
    TOKEN_DELETED = "Successfully cleared the token for the {} API."
    TOKEN_NONE = ERROR + "No token set."
    TOKEN_NOT_SET = TOKEN_NONE + "Which makes deleting it a little complicated."
    TOKEN_LEN_ERROR = ERROR + "The token you put in is not as long as the accepted token size ({})."
    TOKEN_HEX_ERROR = ERROR + "Your input does not seem to be hexadecimal."
    TOKEN_NOT_PRIVATE = ":warning: Because of safety reasons, please send the bot this command in DMs. Input ignored."
    TOKEN_INVALID = ERROR + "Token is invalid."
    # Rank role configuration constants.
    R_CONF_DISABLED = BIN + "Successfully disabled the rank role functionality for this server."
    R_CONF_ENABLED = DONE + "Successfully enabled the rank role functionality for this server."
    R_SPECIAL_IGNORE = DONE + "The rank role check will now ignore the special playlists."
    R_SPECIAL_UNIGNORE = BIN + "The rank role check will no longer ignore the special playlists."
    R_CONF_SUCCESS = DONE + "Successfully added all roles!"
    R_CONF_NOT_ENABLED = "Don't forget to enable the RL rank role functionality by doing {}"
    R_CONF_INVALID_MODE = ERROR + "Invalid mode."
    R_CONF_INCOMPLETE = "You can either add each missing role individually using {}, " \
                        "or rerun this command when all roles are set up."
    R_GENERATE_NO_PERMS = ERROR + "I do not have sufficient permissions to add roles"
    R_GENERATE_PROGRESS = "{n} out of 22 roles done."
    R_DETECT_SUCCESS = DONE + "Detected `{role_id}` for {tier_str}"
    R_DETECT_FAIL = ":x: Did not find a role for {tier_str}"
    R_DETECT_TOTAL = "**Total matches:** {match_count} out of 22\n{note}\n\n{rest}"
    # Account registration + rank role update constants.
    LINKED_UNRANKED = "Your linked account is (currently) unranked in every playlist."
    RANK_ROLE_ADDED = "You received the {r_role} role."
    RANK_ROLE_REMOVED = "Your rank roles are removed."
    RANK_ROLE_INTACT = "You already seem to have the right rank role ({r_role}), so your roles are not changed."
    RANK_ROLE_UPDATED = "Your rank role is successfully updated to {r_role}."
    RANK_ROLE_NULL = "You did not have any rank roles, so none were deleted either"
    RANK_ROLE_DISABLED = ERROR + "You cannot obtain a rank role on this server!"
    RANK_ROLE_UPDATE_UNRANKED = ERROR + LINKED_UNRANKED + "\nThus, your rank roles could not be updated."
    LINK_SUCCESS = DONE + "Successfully linked your {} ID with this account!"
    LINK_ROLE_UNRANKED = LINKED_UNRANKED + "\nThus, you cannot receive a rank role."
    LINK_REMOVED = BIN + "Successfully unlinked your {} ID from this account."
    LINK_AND_RANKROLE_REMOVED = LINK_REMOVED + "\nIf you had any rank roles, these were removed as well."  # 1 {}
    LINK_REMOVE_ROLE_NOTE = "Keep in mind that you __don't__ have to unlink your account to update any rank roles.\n"
    LINK_REMOVE_PROMPT = "**Are you sure you want to unlink your account?**\n{}" \
                         "If so, resend this command, but with `yes` at the end, to unlink your {} ID. " \
                         "No action needed otherwise. {}"  # 3× {}.
    # General user link errors.
    USER_NOT_REGISTERED = ERROR + "This user has not registered their account!"
    ALREADY_REGISTERED = ":no_entry_sign: You have already linked your account!\n" \
                         "To change your account, first *unlink* the current account with {}, then link a new one."
    AUTHOR_NOT_REGISTERED = ERROR + "You do not have a registered account."
    AUTHOR_REGISTER_PROMPT = AUTHOR_NOT_REGISTERED + "\nUse {} to register one."
    # Platform-tag validation constants.
    ID64_NON_NUMERIC = ERROR + "`/profiles/` links must have a fully numeric ID!"
    SWITCH_UNSUPPORTED = ERROR + "Psyonix does not (yet) support rank queries for the Nintendo Switch.\n" \
                                 "When they do, this command will support it as soon as possible."
    PLATFORM_EXAMPLES = "Try one of these: PC, PS4, XBOX"
    PLATFORM_INVALID = ERROR + "That platform does not exist.\n" + PLATFORM_EXAMPLES
    # Playlist validation constants.
    PLAYLIST_INVALID = ERROR + "Invalid playlist input."
    PLAYLIST_NOT_PLAYED = ERROR + "{plist} is never played on this account."
    # Help message constants.
    GROUP_FOOTER = "Tip: adding 'me' or 'user' behind a stat command name shows your own stats, " \
                   "or lets you view the stats of another Discord user."
    PLAYLIST_INPUT = "Playlists are accepted in multiple formats, including:\n" \
                     "`casual` • `duel` • `doubles` • `solostandard` • `hoops` • `rumble` • `dropshot` • `snowday\n" \
                     "1s` • `2s` • `ss` • `3s` • `hs` • `rb` • `ds` • `sd`"
    PROFILE_INPUT = "**PC** – Use your vanity ID (__not__ display name!), the long number, " \
                    "or just link to your profile.\n**PS4** – Use your player tag (may be case-sensitive).\n" \
                    "**XBOX** – Use your player tag. If it has spaces, surround it with quotes."
    INFO_FOOTER = "If any input is invalid though it should be valid, please reach out to the developer!"
    # Assertion error constants.
    ASSERT_INT = "LaFusee: Invalid int for tier: {n} is not an integer between 0 and 22 inclusive."
    ASSERT_ROLE_CONFIG = "LaFusee: The role for tier {n} is not configured."
    ASSERT_ROLE_EXISTS = "LaFusee: The role with ID {r_id} ({tier_n}) does not exist."
    # Embed row constants. Padding character (\u2800) is a Braille space, and spacing is an en space (\u2002).
    E_ROW_ONLY_MMR = "`{:\u2800<{}}`\u2002**{:0.2f}**"
    E_ROW_RANKED = "`{ls:\u2800<{p}}`\u2002**{n:0.2f}**\u2002({bold}{tier_div}{bold})"
    E_ROW_NO_MATCHES = "`{:\u2800<{}}`\u2002*No matches played*"
    # Other constants.
    STEAM_PROFILE_URL = "https://steamcommunity.com/profiles/{}"
    STEAM_APP_URL = "steam://url/SteamIDPage/{}"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/account_registrations.db"
        self.config = Config.get_conf(self, identifier=80590423, force_registration=True)
        self.config.register_global(psy_token=None, steam_token=None)
        # Structure of rankrole_dict: {tier_n: role_id}
        self.config.register_guild(rankrole_enabled=False, rankrole_dict={}, ignore_special=False)
        self.psy_api = PsyonixCalls(self.config)
        self.steam_api = SteamCalls(self.config)
        self.link_db = DbQueries(self.PATH_DB)
        self.json_conv = GetJsonData()

    # Events
    async def cog_command_error(self, ctx, error):
        if isinstance(error, LaFuseeError):
            await ctx.send(str(error))
        else:
            await ctx.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    # Configuration commands.
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="rlset", invoke_without_command=True)
    async def _rl_setup(self, ctx):
        """Configure the cog's configuration for this server"""
        await ctx.send_help()

    @checks.mod_or_permissions(administrator=True)
    @_rl_setup.group(name="api", invoke_without_command=True)
    async def _api_setup(self, ctx):
        """Configure the API keys needed for the RL commands"""
        await ctx.send_help()

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
    async def set_psyonix_token(self, ctx, token):
        """Configures the token required to query the Psyonix API

        Only the hexadecimal code is needed."""
        await self.check_token_fmt(ctx, token, self.PSY_TOKEN_LEN)
        str_token = "Token {}".format(token)
        await self.config.psy_token.set(str_token)
        await ctx.send(self.TOKEN_ADDED.format("Psyonix"))

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
    async def delete_psyonix_token(self, ctx):
        """Removes the currently set token from the config"""
        token = await self.config.psy_token()
        if token is None:
            raise TokenError(self.TOKEN_NOT_SET)
        await self.config.psy_token.clear()
        await ctx.send(self.TOKEN_DELETED.format("Psyonix"))

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
    async def set_steam_token(self, ctx, token):
        """Configures the token required to query the Steam API

        Only the hexadecimal code is needed."""
        await self.check_token_fmt(ctx, token, self.STEAM_TOKEN_LEN)
        await self.config.steam_token.set(str(token))
        await ctx.send(self.TOKEN_ADDED.format("Steam"))

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
    async def delete_steam_token(self, ctx):
        """Removes the currently set token from the config"""
        token = await self.config.steam_token()
        if token is not None:
            await self.config.steam_token.clear()
            notice = self.TOKEN_DELETED.format("Steam")
        else:
            notice = self.TOKEN_NOT_SET
        await ctx.send(notice)

    @_rl_setup.command(name="toggle_roles")
    @checks.admin_or_permissions(administrator=True)
    async def toggle_rl_role(self, ctx):
        """Toggles the RL rank role functionality"""
        is_enabled = await self.config.guild(ctx.guild).rankrole_enabled()
        if is_enabled:
            to_send = self.R_CONF_DISABLED
        else:
            to_send = self.R_CONF_ENABLED
        # Set rankrole_enabled as the inverse of is_enabled (as this command is a toggle).
        await self.config.guild(ctx.guild).rankrole_enabled.set(not is_enabled)
        await ctx.send(to_send)

    @_rl_setup.command(name="toggle_special")
    @checks.admin_or_permissions(administrator=True)
    async def toggle_ignore_special(self, ctx):
        """Toggle whether the rank role should ignore the special playlists"""
        is_enabled = await self.config.guild(ctx.guild).ignore_special()
        if is_enabled:
            to_send = self.R_SPECIAL_UNIGNORE
        else:
            to_send = self.R_SPECIAL_IGNORE
        # Set rankrole_enabled as the inverse of is_enabled (as this command is a toggle).
        await self.config.guild(ctx.guild).ignore_special.set(not is_enabled)
        await ctx.send(to_send)

    @_rl_setup.command(name="set_roles")
    @checks.admin_or_permissions(administrator=True)
    async def set_rl_roles(self, ctx, mode: str):
        """Toggles the RL rank role functionality

        There are two possible modes:
        **generate** - creates new rank roles and automatically saves them
        **detect** - detects existing roles based on their name.

        For `detect`, the role names must have proper capitalisation and roman numerals, like \"Diamond III\"."""
        gld = ctx.guild
        low_mode = mode.lower()
        if low_mode == "generate":
            role_dict = {}
            if gld.me.guild_permissions.manage_roles is False:
                to_say = self.R_GENERATE_NO_PERMS
            else:
                for i in reversed(range(1, 20)):  # Reversed because of hierarchy.
                    role_colour = discord.Colour(self.json_conv.get_tier_colour(i))
                    role_name = self.json_conv.get_tier_name(i)
                    new_role = await gld.create_role(name=role_name, colour=role_colour, hoist=True)
                    role_dict[i] = new_role.id
                    progress_n = 20 - i
                    if progress_n % 5 == 0:
                        await ctx.send(self.R_GENERATE_PROGRESS.format(n=progress_n))
                to_say = self.R_CONF_SUCCESS
            await self.config.guild(gld).rankrole_dict.set(role_dict)
        elif low_mode == "detect":
            role_dict = {}
            say_list = []
            matches = 0
            for i in range(1, 23):
                tier_str = self.json_conv.get_tier_name(i)
                role = discord.utils.get(gld.roles, name=tier_str)
                if role:
                    matches += 1
                    role_id = role.id
                    role_dict[i] = role_id
                    say_list.append(self.R_DETECT_SUCCESS.format(role_id=role_id, tier_str=tier_str))
                else:  # No role found.
                    role_dict[i] = None
                    say_list.append(self.R_DETECT_FAIL.format(tier_str=tier_str))
            if matches < 22:
                comment = self.R_CONF_INCOMPLETE.format("`SoonTM`")  # TODO: add manual command.
            elif await self.config.guild(gld).rankrole_enabled() is False:
                comment = self.R_CONF_NOT_ENABLED.format(com(ctx, self.toggle_rl_role))
            else:
                comment = self.R_CONF_SUCCESS
            to_say = self.R_DETECT_TOTAL.format(match_count=matches, note=comment, rest="\n".join(say_list))
            await self.config.guild(gld).rankrole_dict.set(role_dict)
        else:
            to_say = self.R_CONF_INVALID_MODE
        await ctx.send(to_say)

    # Main command group.
    @commands.group(name="rl", invoke_without_command=True)
    async def _rl(self, ctx):
        """Commands related to Rocket League stats"""
        rankrole_enabled = await self.config.guild(ctx.guild).rankrole_enabled()
        embed = discord.Embed(title="Rocket League stats: Overview", colour=discord.Colour.red())
        embed.description = "Need help with input? Try {}".format(com(ctx, self.rl_help))
        # View stats.
        stat_lines = ("Compact ranks: {}".format(com(ctx, self._lfg_embed)),
                      "General stats: {}".format(com(ctx, self._rocket_embed)),
                      "Playlist stats: {}".format(com(ctx, self._plist_embed)))
        embed.add_field(name="View stats", value="\n".join(stat_lines))
        # Link account etc.
        link_lines = ("Link account: {}".format(com(ctx, self.register_tag)),
                      "Remove link: {}".format(com(ctx, self.de_register_tag)),
                      "Update rank role: {}".format(com(ctx, self.update_rank_role)))
        t_slice = None if rankrole_enabled else 2
        embed.add_field(name="Linking your account", value="\n".join(link_lines[:t_slice]))
        embed.set_footer(text=self.GROUP_FOOTER)
        await ctx.send(embed=embed)

    @_rl.command(name="howto")
    async def rl_help(self, ctx):
        """Show information about input for the ranking commands"""
        embed = discord.Embed(title="Rocket League stats: Input help", colour=discord.Colour.red())
        embed.add_field(name="Platform input", value=self.PLATFORM_EXAMPLES, inline=False)
        embed.add_field(name="Profile input", value=self.PROFILE_INPUT)
        embed.add_field(name="Playlist input", value=self.PLAYLIST_INPUT)
        embed.set_footer(text=self.INFO_FOOTER)
        await ctx.send(embed=embed)

    # Registration commands.
    @_rl.command(name="link")
    async def register_tag(self, ctx, platform, profile_id):
        """Register your gamer account for use in other commands"""
        author = ctx.author
        gld = ctx.guild
        rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
        db_platform, db_id = await self.link_db.select_user(author.id)
        if db_platform or db_id:
            overwrite_error = self.ALREADY_REGISTERED.format(com(ctx, self.de_register_tag))
            if rankrole_enabled:
                overwrite_error += "\nTo update your rank role, try {}.\n".format(com(ctx, self.update_rank_role))
            raise CustomNotice(overwrite_error)
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        msg = await ctx.send("Linking your account...")
        try:  # Check their rankings to see if their platform + ID pair gives an error.
            response = await self.psy_api.player_skills(url_platform, url_id)
        except PsyonixCallError as e:
            edit_say = str(e)
        else:
            await self.link_db.insert_user(author.id, str(author), url_platform, url_id)
            cap_platform = url_platform.capitalize()
            link_say = self.LINK_SUCCESS.format(cap_platform)
            if rankrole_enabled is False:
                edit_say = link_say
            else:  # Rank roles are enabled.
                # Check their highest roles, and give a role if this is not unranked.
                player_skills = response.get("player_skills")  # Value is a list.
                ignore_special = await self.config.guild(ctx.guild).ignore_special()
                best_tier, best_list_id, played_lists = best_playlist(player_skills, ignore_special)
                if best_tier == 0:  # Unranked, so no actual highest rank.
                    role_say = self.LINK_ROLE_UNRANKED  # Keep roles in the event one's ranks got inactive.
                else:  # Does have a rank.
                    role_say = await self.update_member_rankroles(gld, author, best_tier)
                edit_say = "\n".join((link_say, role_say))
        await msg.edit(content=edit_say)

    @_rl.command(name="update")
    async def update_rank_role(self, ctx):
        """Update your rank role based on the current best rank of your linked account"""
        gld = ctx.guild
        rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
        if rankrole_enabled is False:
            raise CustomNotice(self.RANK_ROLE_DISABLED)
        author = ctx.author
        url_platform, url_id = await self.link_db.select_user(author.id)
        if url_platform is None and url_id is None:
            raise CustomNotice(self.AUTHOR_NOT_REGISTERED)
        response = await self.psy_api.player_skills(url_platform, url_id)
        player_skills = response.get("player_skills")  # Value is a list.
        ignore_special = await self.config.guild(ctx.guild).ignore_special()
        best_tier, best_list_id, played_lists = best_playlist(player_skills, ignore_special)
        if best_tier == 0:  # Unranked, so no actual highest rank.
            to_say = self.RANK_ROLE_UPDATE_UNRANKED  # Keep roles in the event one's ranks got inactive.
        else:  # Does have a rank.
            role_say = await self.update_member_rankroles(ctx.guild, author, best_tier)
            to_say = "{}{}".format(self.DONE, role_say)
        await ctx.send(to_say)

    @_rl.command(name="unlink")
    async def de_register_tag(self, ctx, confirmation: bool = False):
        """De-register your gamer account for use in other commands"""
        gld = ctx.guild
        author = ctx.author
        author_id = author.id

        url_platform, url_id = await self.link_db.select_user(author_id)
        if url_platform is None and url_id is None:
            to_say = self.AUTHOR_NOT_REGISTERED
        else:
            cap_platform = url_platform.capitalize()
            rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
            if not confirmation:
                role_note = self.LINK_REMOVE_ROLE_NOTE if rankrole_enabled else ""
                to_say = self.LINK_REMOVE_PROMPT.format(role_note, cap_platform, author.mention)
            else:
                await self.link_db.delete_user(author_id)
                if rankrole_enabled is False:
                    to_say = self.LINK_REMOVED.format(cap_platform)
                else:
                    # Remove any leftover rank roles.
                    await self.update_member_rankroles(gld, author)
                    to_say = self.LINK_AND_RANKROLE_REMOVED.format(cap_platform)
        await ctx.send(to_say)

    # Rank lookup commands.
    @_rl.group(name="lfg", invoke_without_command=True)
    async def _lfg_embed(self, ctx, platform: str, profile_id: str):
        """Show a player's ranks in LFG embed format"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)
        embeds = self.make_lfg_embed(response, url_platform)
        await red_menu.menu(ctx, embeds, red_menu.DEFAULT_CONTROLS, timeout=30.0)

    @_lfg_embed.command(name="user", aliases=["me"])
    async def lfg_user(self, ctx, user: discord.Member = None):
        """Show the LFG embed of a member on this server

        If no user is provided, it will show your own."""
        if user is None:
            user = ctx.author
        url_platform, url_id = await self.link_db.select_user(user.id)
        self.check_registration_complete(url_platform, url_id, user, ctx)  # Valid registration or error raised.
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)
        embeds = self.make_lfg_embed(response, url_platform, user)
        await red_menu.menu(ctx, embeds, red_menu.DEFAULT_CONTROLS, timeout=30.0)

    @_rl.group(name="stats", aliases=["rocket"], invoke_without_command=True)
    async def _rocket_embed(self, ctx, platform: str, profile_id: str):
        """Show a player's stats in standard embed format"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)
        gas_od = await self.psy_api.player_stat_values(url_platform, url_id)
        await ctx.send(embed=self.make_rocket_embed(response, gas_od, url_platform))

    @_rocket_embed.command(name="user", aliases=["me"])
    async def rocket_user(self, ctx, user: discord.Member = None):
        """Show the rocket embed of a member on this server

        If no user is provided, it will show your own."""
        if user is None:
            user = ctx.author
        url_platform, url_id = await self.link_db.select_user(user.id)
        self.check_registration_complete(url_platform, url_id, user, ctx)  # Valid registration or error raised.
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)
        gas_od = await self.psy_api.player_stat_values(url_platform, url_id)
        await ctx.send(embed=self.make_rocket_embed(response, gas_od, url_platform, user))

    @_rl.group(name="lstats", aliases=["liststats", "list"], invoke_without_command=True)
    async def _plist_embed(self, ctx, platform: str, profile_id: str, playlist: str):
        """Show a player's stats of a specific playlist"""
        # Validate playlist input.
        list_id = self.json_conv.get_input_playlist(playlist)
        if list_id is None:  # Can be 0, so None should be explicit.
            raise CustomNotice(self.PLAYLIST_INVALID)
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)  # Get platform / ID.
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)  # Get player skills.
        content, embed = self.make_plist_embed(response, list_id, url_platform)
        await ctx.send(content, embed=embed)

    @_plist_embed.command(name="user", aliases=["me"])
    async def plist_user(self, ctx, playlist: str, user: discord.Member = None):
        """Show a server member's stats of a specific playlist

        If no user is provided, it will show your own."""
        # Validate playlist input.
        list_id = self.json_conv.get_input_playlist(playlist)
        if list_id is None:  # Can be 0, so None should be explicit.
            raise CustomNotice(self.PLAYLIST_INVALID)
        if user is None:
            user = ctx.author
        url_platform, url_id = await self.link_db.select_user(user.id)  # Get user from DB.
        self.check_registration_complete(url_platform, url_id, user, ctx)  # Valid registration or error raised.
        response = await self.psy_api.player_skills(url_platform, url_id, ensure_played=True)
        content, embed = self.make_plist_embed(response, list_id, url_platform, user)
        await ctx.send(content, embed=embed)

    # Extra commands.
    @commands.command(name="steamadd", aliases=["add"])
    async def send_steam_link(self, ctx, profile_id: str = None):
        """Send a direct link to your steam account in chat

        This allows others to open up your account directly in the steam client.
        If no account is provided, it will try to use your linked account."""
        if not profile_id:
            url_platform, url_id = await self.link_db.select_user(ctx.author.id)
            if None in (url_platform, url_id):
                raise CustomNotice(self.AUTHOR_REGISTER_PROMPT.format(com(ctx, self.register_tag)))
        else:
            url_platform, url_id = await self.platform_id_bundle("steam", profile_id)
        await ctx.send(self.STEAM_APP_URL.format(url_id))

    # Debug commands.
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="rltest", invoke_without_command=True)
    async def _tests(self, ctx):
        """Debug commands for the RL module"""
        await ctx.send_help()

    @_tests.command(name="skills")
    @checks.admin_or_permissions(administrator=True)
    async def skills_test(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerSkills query"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        response = await self.psy_api.player_skills(url_platform, url_id)
        str_list = []
        for k, v in response.items():
            str_row = "`{}`: {}".format(k, v)
            str_list.append(str_row)
        await ctx.send("\n".join(str_list))

    @_tests.command(name="titles")
    @checks.admin_or_permissions(administrator=True)
    async def titles_test(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerTitles query"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        response = await self.psy_api.player_titles(url_platform, url_id)
        await ctx.send(response)

    @_tests.command(name="raw")
    @checks.admin_or_permissions(administrator=True)
    async def raw_skills(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerSkills query"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        response = await self.psy_api.player_skills(url_platform, url_id)
        await ctx.send("```json\n{}```".format(dumps(response, sort_keys=True, indent=1)))

    @_tests.command(name="gas")
    @checks.admin_or_permissions(administrator=True)
    async def gas_test(self, ctx, platform, profile_id):
        """Test the loop query for gas-stats"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        gas_od = await self.psy_api.player_stat_values(url_platform, url_id)
        await ctx.send("\n".join(f"{k.title()}: {v}" for k, v in gas_od.items()))

    @_tests.command(name="vanity")
    @checks.admin_or_permissions(administrator=True)
    async def test_vanity(self, ctx, vanity_id):
        """Used for testing the Steam API vanity id conversion"""
        response = await self.steam_api.vanity_to_id64(vanity_id)
        await ctx.send(response)

    @_tests.command(name="user_bundle")
    @checks.admin_or_permissions(administrator=True)
    async def test_platform_id_bundle(self, ctx, platform, profile_id):
        """Used for testing the platform - gamerID bundle"""
        url_platform, url_id = await self.platform_id_bundle(platform, profile_id)
        await ctx.send("{} - {}".format(url_platform, url_id))

    @_tests.command(name="re")
    @checks.admin_or_permissions(administrator=True)
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

    # Utilities
    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        author_id: int,
    ):
        """Delete someone's linked account (only info stored)

        This does not take care of any rank roles that the user may have."""
        url_platform, url_id = await self.link_db.select_user(author_id)
        if url_platform or url_id:  # Nothing linked.
            await self.link_db.delete_user(author_id)

    async def check_token_fmt(self, ctx: commands.Context, token: str, expected_token_length: int) -> None:
        """Check if a token is hexadecimal and a proper length. Return None if so, raise error otherwise"""
        msg = ctx.message
        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            try:
                await msg.delete()  # Delete message immediately if not sent in DMs.
            except discord.errors.Forbidden:
                print("No perms to delete message")
            raise TokenError(self.TOKEN_NOT_PRIVATE)
        if len(token) != expected_token_length:
            raise TokenError(self.TOKEN_LEN_ERROR.format(expected_token_length))
        try:
            int(token, 16)  # Token is a valid hexadecimal string.
        except ValueError:
            raise TokenError(self.TOKEN_HEX_ERROR)

    def check_registration_complete(self, url_platform, url_id, user: discord.User, ctx: commands.Context = None):
        """Check if registration is complete, raise error otherwise"""
        if None in (url_platform, url_id):  # User is not properly registered.
            if ctx and user == ctx.author:
                raise CustomNotice(self.AUTHOR_REGISTER_PROMPT.format(com(ctx, self.register_tag)))
            raise CustomNotice(self.USER_NOT_REGISTERED)

    async def update_member_rankroles(self, gld: discord.Guild, mem: discord.Member, add_tier: int = None) -> str:
        """Update the rank roles of a user

        add_tier must be either an int between 0-22 inclusive, or None.
        If add_tier is None, all rank roles will be removed.
        Otherwise, the add_tier will be kept, or added in case the member did not have it."""
        assert add_tier is None or (type(add_tier) == int and 0 <= add_tier <= 22), self.ASSERT_INT.format(n=add_tier)
        rankrole_dict = await self.config.guild(gld).rankrole_dict()
        rankrole_ids = {r_id for r_id in rankrole_dict.values() if r_id is not None}

        roles = mem.roles
        member_r_roles = [r for r in roles if r.id in rankrole_ids]

        if add_tier is None or add_tier == 0:  # All member rank roles should be deleted.
            if len(member_r_roles) > 0:
                await mem.remove_roles(*member_r_roles)
                to_return = self.RANK_ROLE_REMOVED
            else:
                to_return = self.RANK_ROLE_NULL
        else:
            exempt_role_id = rankrole_dict.get(str(add_tier), None)
            assert exempt_role_id is not None, self.ASSERT_ROLE_CONFIG.format(n=add_tier)
            role_to_add = discord.utils.get(gld.roles, id=exempt_role_id)
            assert role_to_add is not None, self.ASSERT_ROLE_EXISTS.format(r_id=exempt_role_id, tier_n=add_tier)

            tier_name = self.json_conv.get_tier_name(add_tier)
            if len(member_r_roles) == 0:  # No current rank roles.
                await mem.add_roles(role_to_add)
                to_return = self.RANK_ROLE_ADDED.format(r_role=tier_name)
            elif member_r_roles == [role_to_add]:
                # Author already has the exact rank role he should have, and no other rank roles.
                to_return = self.RANK_ROLE_INTACT.format(r_role=tier_name)
            else:
                if role_to_add in member_r_roles:
                    # Keep the role supposed to be added, remove the rest later.
                    to_remove = [r for r in member_r_roles if r != role_to_add]
                else:
                    await mem.add_roles(role_to_add)  # Add the role, remove the current ones later.
                    to_remove = member_r_roles
                await mem.remove_roles(*to_remove)
                to_return = self.RANK_ROLE_UPDATED.format(r_role=tier_name)
        return to_return

    async def platform_id_bundle(self, platform_in: str, id_in: str):
        """Verify the input of a platform and gamer id

        By default, number input for id_in (for Steam) will be treated as an ID3/ID64.
        In order to use vanity id that consists solely of digits, it must be prefixed with /id/"""
        platform_out = self.json_conv.get_input_platform(platform_in)
        if not platform_out:
            raise AccountInputError(self.PLATFORM_INVALID)
        if platform_out == "switch":
            raise AccountInputError(self.SWITCH_UNSUPPORTED)
        # Valid platform.
        if platform_out == "steam":
            if id_in.lstrip("-").isdigit():
                id_out = self.int_to_steam_id64(int(id_in))
            elif re.match(r"^\[U:1:\d{1,10}\]$", id_in):  # Convert value inside steamID3 to ID64.
                id_out = self.int_to_steam_id64(int(id_in.lstrip("[U:1:").rstrip("]")))
            else:  # Do regex checks for /id/ and /profiles/.
                re_split_a = re.split(r'/profiles/', id_in, maxsplit=1)
                re_split_b = re.split(r'/id/', id_in, maxsplit=1)
                if len(re_split_a) == 2:  # Successful split, so a match.
                    clean_id = re_split_a[-1].rstrip("/")
                    try:
                        id_out = self.int_to_steam_id64(int(clean_id))
                    except ValueError:
                        raise AccountInputError(self.ID64_NON_NUMERIC)
                elif len(re_split_b) == 2:
                    clean_id = re_split_b[-1].rstrip("/")
                    id_out = await self.steam_api.vanity_to_id64(clean_id)
                else:
                    id_out = await self.steam_api.vanity_to_id64(id_in)
        else:
            id_out = id_in
        return platform_out, id_out

    @staticmethod
    def int_to_steam_id64(id_64: int) -> int:
        """Converts a SteamID64 to the one that the Psyonix API recognises

        The reason for this is that Valve accepts multiple ID64s for the same account.
        As a consequence, Discord Steam links use an ID64 that is not recognised by the Rocket League API."""
        return (id_64 % (2 ** 32)) + 76561197960265728

    def rank_summary_str(self, player_skills: Optional[list], best_list_id: int, unplayed_lists: set,
                         drop_casual: bool = False) -> (str, str):
        """
        :param player_skills: list that is extracted from the API response dict, or None if there are no stats.
        :param best_list_id: The number of the playlist in which the user has the highest ranking.
        :param unplayed_lists: A set of the playlists which the user has not played in.
        :param drop_casual: (Optional) Whether to drop casual ranking. Defaults to False.
        :return: A string with a player's summarised rank in a given playlist
        """
        desc_rows = {}
        pad = 8
        mode_int = 2
        for i in player_skills:
            rating = float_sr(i)
            playlist_id = i["playlist"]
            list_name = self.json_conv.get_playlist_name(playlist_id, mode_int)
            if playlist_id == 0 and drop_casual:
                playlist_str = None
            elif playlist_id == 0:
                playlist_str = self.E_ROW_ONLY_MMR.format(list_name, pad, rating)
            else:
                tier_div = self.json_conv.tier_div_str(i)
                bold = "**" if playlist_id == best_list_id else ""  # Embolden best playlist.
                playlist_str = self.E_ROW_RANKED.format(ls=list_name, p=pad, n=rating, bold=bold, tier_div=tier_div)
            if playlist_str:
                desc_rows[playlist_id] = playlist_str
        for n in unplayed_lists:
            list_name = self.json_conv.get_playlist_name(n, mode_int)
            desc_rows[n] = self.E_ROW_NO_MATCHES.format(list_name, pad)
        # Split list into normal and special (to make menu-embed possible).
        normal_lists, special_lists = [], []
        for k, v in sorted(desc_rows.items()):
            normal_lists.append(v) if k < 20 else special_lists.append(v)
        return "\n".join(normal_lists), "\n".join(special_lists)

    def make_lfg_embed(self, response: dict, url_platform: str, user: discord.Member = None) -> List[discord.Embed]:
        """Make the embed for the LFG commands"""
        player_name = response["user_name"]
        player_skills = response.get("player_skills")  # Note: value is a list!
        assert player_skills, "lfg -> No player skills! Check the presence of player skills first."
        best_tier, best_list_id, played_lists = best_playlist(player_skills)
        unplayed_lists = {n for n in self.PLAYLIST_IDS if n not in played_lists}
        # Create rows for each playlist.
        summary_tuple = self.rank_summary_str(player_skills, best_list_id, unplayed_lists)
        # Get author URL. Profile links only exist for Steam.
        player_url = self.STEAM_PROFILE_URL.format(response["user_id"]) \
            if url_platform == "steam" else discord.Embed.Empty
        # Create embed, and use the highest tier's colour.
        return_list = []
        for summary in summary_tuple:
            embed = discord.Embed()
            embed.colour = self.json_conv.get_tier_colour(best_tier)
            embed.set_author(name="Rocket League Stats - {}".format(player_name), url=player_url)
            embed.description = summary
            if user:
                embed.set_footer(text=f"ID: {user.id}", icon_url=user.avatar_url_as(static_format="png"))
            return_list.append(embed)
        return return_list

    def make_rocket_embed(self, response: dict, gas_od: OrderedDict, url_platform: str,
                          user: discord.Member = None) -> discord.Embed:
        """Make the embed for the general stat commands"""
        player_name = response["user_name"]
        player_skills = response.get("player_skills")  # Note: value is a list!
        assert player_skills, "rocket -> No player skills! Check the presence of player skills first."
        best_tier, best_list_id, played_lists = best_playlist(player_skills)
        unplayed_lists = {n for n in self.PLAYLIST_IDS if n not in played_lists}
        # Create rows for each playlist.
        summary_tuple = self.rank_summary_str(player_skills, best_list_id, unplayed_lists, drop_casual=True)
        # Get stats for casual (unranked) separately.
        casual_rating = None
        if 0 not in unplayed_lists:  # Thus, casual is played.
            zero_dict = next(d for d in player_skills if d["playlist"] == 0)
            casual_rating = float_sr(zero_dict)
        casual_str = "\nCasual SR: **{}**".format(f"{casual_rating:0.2f}" if casual_rating else "*N/A*")
        # Make strings for GAS.
        gas_list = [f"{k.title()}: **{v}**" for k, v in gas_od.items()]
        # Get author URL. Profile links only exist for Steam.
        player_url = self.STEAM_PROFILE_URL.format(response["user_id"]) \
            if url_platform == "steam" else discord.Embed.Empty
        # Create embed, and use the highest tier's colour.
        embed = discord.Embed()
        embed.colour = self.json_conv.get_tier_colour(best_tier)
        embed.description = "Reward level: {}".format(self.json_conv.reward_level_str(response))
        embed.set_thumbnail(url=self.json_conv.get_tier_icon(best_tier))
        embed.set_author(name="Rocket League Stats - {}".format(player_name), url=player_url)
        if user:
            embed.set_footer(text=f"ID: {user.id}", icon_url=user.avatar_url_as(static_format="png"))
        # Add stat fields.
        embed.add_field(name="General", value="\n".join((*gas_list, casual_str)))
        embed.add_field(name="Competitive", value="\n".join(summary_tuple))
        return embed

    def make_plist_embed(self, response: dict, list_id: int, url_platform: str,
                         user: discord.Member = None) -> (Optional[str], Optional[discord.Embed]):
        """Create a playlist-specific embed

        Returns message content (if applicable) and an embed (if there is one)."""
        player_skills = response.get("player_skills")
        assert player_skills, "plist -> No player skills! Check the presence of player skills first."
        list_name = self.json_conv.get_playlist_name(list_id, mode=3)
        p_dict = next((d for d in player_skills if d["playlist"] == list_id), None)  # No fixed order.
        if not p_dict:
            content, embed = self.PLAYLIST_NOT_PLAYED.format(plist=list_name), None
        elif list_id == 0:
            content, embed = ("**{} stats**\nRating: {}\nMu/MMR: {}\nSigma:{}"
                              .format(list_name, float_sr(p_dict), p_dict["mu"], p_dict["sigma"])), None
        else:  # Embed can be made.
            player_name = response["user_name"]
            # Unpack rating values.
            tier_div = self.json_conv.tier_div_str(p_dict)
            sr = float_sr(p_dict)
            matches = p_dict["matches_played"]
            streak = p_dict["win_streak"]
            tier_n = p_dict["tier"]  # Needed for thumb and colour.
            # Get author URL. Profile links only exist for Steam.
            player_url = self.STEAM_PROFILE_URL.format(response["user_id"]) \
                if url_platform == "steam" else discord.Embed.Empty
            # Create embed.
            content, embed = None, discord.Embed(description=tier_div)
            embed.colour = self.json_conv.get_tier_colour(tier_n)
            embed.set_thumbnail(url=self.json_conv.get_tier_icon(tier_n))
            embed.set_author(name="{} stats - {}".format(list_name, player_name), url=player_url)
            embed.add_field(name="Rating", value=f"{sr:0.2f}")
            embed.add_field(name="Matches played", value="{} (Streak: {})".format(matches, streak))
            misc = "Mu/MMR: {} | Sigma: {}".format(p_dict["mu"], p_dict["sigma"])
            if user:
                embed.set_footer(text=f"ID: {user.id} | {misc}", icon_url=user.avatar_url_as(static_format="png"))
            else:
                embed.set_footer(text=misc)
        return content, embed

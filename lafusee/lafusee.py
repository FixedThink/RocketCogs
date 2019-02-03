# Default libraries.
import re
from json import dumps  # Only used for debug output formatting.

# Used by Red.
import discord
from redbot.core import commands  # Changed from discord.ext
from redbot.core import checks, Config, data_manager
from redbot.core.bot import Red
import redbot.core.utils.menus as red_menu

# Local files.
from .conversions import best_playlist, com, get_tier_colour, get_tier_name, get_url_platform
from .psyonix_calls import PsyonixCalls
from .steam_calls import SteamCalls
from .db_queries import DbQueries


class LaFusee(commands.Cog):
    """Rocket League rank commands."""
    # Constants.
    PSY_TOKEN_LEN = 40
    STEAM_TOKEN_LEN = 32
    # Playlist tuples, sets, and dicts.
    PLAYLIST_ID_TO_NAME = {0: "Casual", 10: "Ranked Duel 1v1", 11: "Ranked Doubles 2v2",
                           12: "Ranked Solo Standard 3v3", 13: "Ranked Standard 3v3", 27: "Ranked Hoops",
                           28: "Ranked Rumble", 29: "Ranked Dropshot", 30: "Ranked Snowday"}
    PLAYLIST_ID_MINIMAL = {0: "Casual", 10: "Duels", 11: "Doubles", 12: "Solo 3s", 13: "Standard",
                           27: "Hoops", 28: "Rumble", 29: "Dropshot", 30: "Snowday"}
    PLAYLIST_ID_SHORT = {0: "Casual", 10: "1s", 11: "2s", 12: "s3s", 13: "3s", 27: "H🏀", 28: "R🥊", 29: "D⚡", 30: "S❄"}
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
    R_CONF_DISABLED = BIN + "Successfully disabled the RL rank role functionality for this server."
    R_CONF_ENABLED = DONE + "Successfully enabled the RL rank role functionality for this server."
    R_CONF_SUCCESS = DONE + "Successfully added all roles!"
    R_CONF_NOT_ENABLED = "Don't forget to enable the RL rank role functionality by doing `{}{}`"
    R_CONF_INVALID_MODE = ERROR + "Invalid mode."
    R_CONF_INCOMPLETE = "You can either add each missing role individually using {}, " \
                        "or rerun this command when all roles are set up."
    R_GENERATE_NO_PERMS = ERROR + "I do not have sufficient permissions to add roles"
    R_GENERATE_PROGRESS = "{n} out of 19 roles done."
    R_DETECT_SUCCESS = DONE + "Detected `{role_id}` for {tier_str}"
    R_DETECT_FAIL = ":x: Did not find a role for {tier_str}"
    R_DETECT_TOTAL = "**Total matches:** {match_count} out of 19\n{note}\n\n{rest}"
    # Account registration + rank role update constants.
    LINKED_UNRANKED = "Your linked account is (currently) unranked in every playlist."
    RANK_ROLE_ADDED = "You received the {r_role} role, which is the highest rank of your linked account."
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
    LINK_REMOVE_PROMPT = "**Are you sure you want to unlink your account?**\n" \
                         "Keep in mind that you __don't__ have to unlink your account to update it.\n" \
                         "If you are sure, resend this command, but with `yes` at the end, to unlink your {} ID. " \
                         "No action needed otherwise. {}"
    # General user link errors.
    USER_NOT_REGISTERED = ERROR + "This user has not registered their account!"
    ALREADY_REGISTERED = ":no_entry_sign: You have already linked your account!\n" \
                         "To change your account, first *unlink* the current account with {}, then link a new one."
    AUTHOR_NOT_REGISTERED = ERROR + "You do not have a registered account."
    AUTHOR_REGISTER_PROMPT = AUTHOR_NOT_REGISTERED + "\nUse `{}{}` to register one."
    # Platform-tag validation constants.
    ID64_NON_NUMERIC = ERROR + "`/profiles/` links must have a fully numeric ID!"
    SWITCH_UNSUPPORTED = ERROR + "Psyonix does not (yet) support rank queries for the Nintendo Switch.\n" \
                                 "When they do, this command will support it as soon as possible."
    PLATFORM_INVALID = ERROR + "That platform does not exist."
    # Assertion error constants.
    ASSERT_INT = "LaFusee: Invalid int for tier: {n} is not an integer between 0 and 19 inclusive."
    ASSERT_ROLE_CONFIG = "LaFusee: The role for tier {n} is not configured."
    ASSERT_ROLE_EXISTS = "LaFusee: The role with ID {r_id} ({tier_n}) does not exist."
    # Minimal embed constants. Padding character (\u2800) is a Braille space.
    MINIMAL_ONLY_MMR = "`{:\u2800<8}`  **{:0.2f}**"
    MINIMAL_RANKED = "`{ls:\u2800<8}`  **{n:0.2f}**  ({bold}{tier_div}{bold})"
    MINIMAL_NO_MATCHES = "`{:\u2800<8}`  *No matches played*"
    # Other constants.
    STEAM_PROFILE_URL = "https://steamcommunity.com/profiles/{}"

    def __init__(self, bot: Red):
        super().__init__()
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
    @commands.group(name="rl", invoke_without_command=True)
    async def _rl(self, ctx):
        """Commands related to Rocket League stats"""
        # TODO: add platform/tag and stat value explanations to command group.
        # await ctx.send("Placeholder. There should be a custom embed here soon.")
        await ctx.send_help()

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
        msg = ctx.message
        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            try:
                await msg.delete()  # Delete message immediately if not sent in DMs.
            except discord.errors.Forbidden:
                print("No perms to delete message")
            notice = self.TOKEN_NOT_PRIVATE
        elif len(token) == self.PSY_TOKEN_LEN:
            try:
                int(token, 16)  # Token is a valid hexadecimal string.
            except ValueError:
                notice = self.TOKEN_HEX_ERROR
            else:
                str_token = "Token {}".format(token)
                await self.config.psy_token.set(str_token)
                notice = self.TOKEN_ADDED.format("Psyonix")
        else:
            notice = self.TOKEN_LEN_ERROR.format(self.PSY_TOKEN_LEN)
        await ctx.send(notice)

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
    async def delete_psyonix_token(self, ctx):
        """Removes the currently set token from the config"""
        token = await self.config.psy_token()
        if token is not None:
            await self.config.psy_token.clear()
            notice = self.TOKEN_DELETED.format("Psyonix")
        else:
            notice = self.TOKEN_NOT_SET
        await ctx.send(notice)

    @_api_setup.command()
    @checks.admin_or_permissions(administrator=True)
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
        elif len(token) == self.STEAM_TOKEN_LEN:
            try:
                int(token, 16)  # Token is a valid hexadecimal string.
            except ValueError:
                notice = self.TOKEN_HEX_ERROR
            else:
                await self.config.steam_token.set(str(token))
                notice = self.TOKEN_ADDED.format("Steam")
        else:
            notice = self.TOKEN_LEN_ERROR.format(self.STEAM_TOKEN_LEN)
        await ctx.send(notice)

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

    @_rl_setup.command(name="set_roles")
    @checks.admin_or_permissions(administrator=True)
    async def set_rl_roles(self, ctx, mode: str):
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
                to_say = self.R_GENERATE_NO_PERMS
            else:
                for i in reversed(range(1, 20)):  # Reversed because of hierarchy.
                    role_colour = discord.Colour(get_tier_colour(i))
                    role_name = get_tier_name(i)
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
            for i in range(1, 20):
                tier_str = get_tier_name(i)
                role = discord.utils.get(gld.roles, name=tier_str)
                if role:
                    matches += 1
                    role_id = role.id
                    role_dict[i] = role_id
                    say_list.append(self.R_DETECT_SUCCESS.format(role_id=role_id, tier_str=tier_str))
                else:  # No role found.
                    role_dict[i] = None
                    say_list.append(self.R_DETECT_FAIL.format(tier_str=tier_str))
            if matches < 19:
                comment = self.R_CONF_INCOMPLETE.format("`SoonTM`")  # TODO: add manual command.
            elif await self.config.guild(gld).rankrole_enabled() is False:
                comment = self.R_CONF_NOT_ENABLED.format(ctx.prefix, self.toggle_rl_role.qualified_name)
            else:
                comment = self.R_CONF_SUCCESS
            to_say = self.R_DETECT_TOTAL.format(match_count=matches, note=comment, rest="\n".join(say_list))
            await self.config.guild(gld).rankrole_dict.set(role_dict)
        else:
            to_say = self.R_CONF_INVALID_MODE
        await ctx.send(to_say)

    # Registration commands.
    @_rl.command(name="link")
    async def register_tag(self, ctx, platform, profile_id):
        """Register your gamer account for use in other commands"""
        author = ctx.author
        gld = ctx.guild
        rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
        db_platform, db_id = await self.link_db.select_user(author.id)
        if db_platform or db_id:
            notice = self.ALREADY_REGISTERED.format(com(ctx, self.de_register_tag))
            if rankrole_enabled:
                notice = notice + "\nTo update your rank role, try {}.\n".format(com(ctx, self.update_rank_role))
        else:
            url_platform, url_id, bundle_error = await self.platform_id_bundle(platform, profile_id)
            if bundle_error:
                notice = bundle_error
            else:  # Platform and ID valid!
                notice = None
                msg = await ctx.send("Linking your account...")
                # Check their rankings to see if their platform + ID pair gives an error.
                response, api_error = await self.psy_api.player_skills(url_platform, url_id)
                if api_error:
                    edit_say = api_error
                else:
                    username = "{}#{}".format(author.name, author.discriminator)
                    await self.link_db.insert_user(author.id, username, url_platform, url_id)
                    cap_platform = url_platform.capitalize()
                    link_say = self.LINK_SUCCESS.format(cap_platform)
                    if rankrole_enabled is False:
                        edit_say = link_say
                    else:  # Rank roles are enabled.
                        # Check their highest roles, and give a role if this is not unranked.
                        player_skills = response.get("player_skills")
                        best_tier, best_list_id, played_lists = best_playlist(player_skills)
                        if best_tier == 0:  # Unranked, so no actual highest rank.
                            role_say = self.LINK_ROLE_UNRANKED  # Keep roles in the event one's ranks got inactive.
                        else:  # Does have a rank.
                            role_say = await self.update_member_rankroles(gld, author, best_tier)
                        edit_say = "\n".join((link_say, role_say))
                await msg.edit(content=edit_say)
        if notice:  # Notice may occur before msg is created.
            await ctx.send(notice)

    @_rl.command(name="update")
    async def update_rank_role(self, ctx):
        """Update your rank role based on the current best ranked of your linked account"""
        gld = ctx.guild
        rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
        if rankrole_enabled is False:
            to_say = self.RANK_ROLE_DISABLED
        else:
            author = ctx.author
            url_platform, url_id = await self.link_db.select_user(author.id)
            if url_platform is None and url_id is None:
                to_say = self.AUTHOR_NOT_REGISTERED
            else:
                response, notice = await self.psy_api.player_skills(url_platform, url_id)
                if notice:
                    to_say = notice
                else:
                    player_skills = response.get("player_skills")
                    best_tier, best_list_id, played_lists = best_playlist(player_skills)
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
            if not confirmation:
                to_say = self.LINK_REMOVE_PROMPT.format(cap_platform, author.mention)
            else:
                await self.link_db.delete_user(author_id)
                rankrole_enabled = await self.config.guild(gld).rankrole_enabled()
                if rankrole_enabled is False:
                    to_say = self.LINK_REMOVED.format(cap_platform)
                else:
                    # Remove any leftover rank roles.
                    await self.update_member_rankroles(gld, author)
                    to_say = self.LINK_AND_RANKROLE_REMOVED.format(cap_platform)
        await ctx.send(to_say)

    # Rank lookup commands.
    @_rl.group(name="lfg", invoke_without_command=True)
    async def _lfg_embed(self, ctx, platform, profile_id):
        """Show a ranking in LFG embed format"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            response, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                embeds = self.make_lfg_embed(response, url_platform)
                await red_menu.menu(ctx, embeds, red_menu.DEFAULT_CONTROLS, timeout=30.0)
        if notice:
            await ctx.send(notice)

    @_lfg_embed.command(name="user", aliases=["me"])
    async def lfg_user(self, ctx, user: discord.Member = None):
        """Show the LFG embed of a member on this server

        If no user is provided, it will show your own."""
        if user is None:
            user = ctx.author
        url_platform, url_id = await self.link_db.select_user(user.id)
        if None in (url_platform, url_id):  # User is not properly registered.
            if user == ctx.author:
                notice = self.AUTHOR_REGISTER_PROMPT.format(ctx.prefix, self.register_tag.qualified_name)
            else:
                notice = self.USER_NOT_REGISTERED
        else:  # Valid registration.
            response, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                embeds = self.make_lfg_embed(response, url_platform, user)
                await red_menu.menu(ctx, embeds, red_menu.DEFAULT_CONTROLS, timeout=30.0)
        if notice:
            await ctx.send(notice)

    # Debug commands.
    @checks.mod_or_permissions(administrator=True)
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
        if notice:  # Send a notice if the call was invalid.
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
        if notice:  # Send a notice if the call was invalid.
            await ctx.send(notice)

    @_tests.command(name="raw")
    @checks.mod_or_permissions(administrator=True)
    async def raw_skills(self, ctx, platform, profile_id):
        """Used for seeing the response of a PlayerSkills query"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            response, notice = await self.psy_api.player_skills(url_platform, url_id)
            if not notice:
                await ctx.send("```json\n{}```".format(dumps(response, sort_keys=True, indent=1)))
        if notice:  # Send a notice if the call was invalid.
            await ctx.send(notice)

    @_tests.command(name="gas")
    @checks.mod_or_permissions(administrator=True)
    async def gas_test(self, ctx, platform, profile_id):
        """Test the loop query for gas-stats"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        if not notice:
            gas_od, notice = await self.psy_api.player_stat_values(url_platform, url_id)
            if not notice:
                await ctx.send("\n".join(f"{k.title()}: {v}" for k, v in gas_od.items()))
        if notice:  # Send a notice if the call was invalid.
            await ctx.send(notice)

    @_tests.command(name="vanity")
    @checks.mod_or_permissions(administrator=True)
    async def test_vanity(self, ctx, vanity_id):
        """Used for testing the Steam API vanity id conversion"""
        response, notice = await self.steam_api.vanity_to_id64(vanity_id)
        await ctx.send("{}\n{}".format(response, notice))

    @_tests.command(name="user_bundle")
    @checks.mod_or_permissions(administrator=True)
    async def test_platform_id_bundle(self, ctx, platform, profile_id):
        """Used for testing the platform - gamerID bundle"""
        url_platform, url_id, notice = await self.platform_id_bundle(platform, profile_id)
        await ctx.send("{} - {} \n{}".format(url_platform, url_id, notice))

    @_tests.command(name="re")
    @checks.mod_or_permissions(administrator=True)
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
    @checks.mod_or_permissions(administrator=True)
    async def test_embed_colour(self, ctx, hex_code):
        """Test embed colours"""
        embed = discord.Embed(title="Tell me, black or white?", colour=int(hex_code, 16))
        embed.description = "This is just a description\nthat is split in two lines for some reason."
        embed.set_footer(text="Hex code: {}".format(hex_code))
        await ctx.send(embed=embed)

    # Utilities
    async def update_member_rankroles(self, gld: discord.Guild, mem: discord.Member, add_tier: int = None) -> str:
        """Update the rank roles of a user

        add_tier must be either an int between 0-19 inclusive, or None.
        If add_tier is None, all rank roles will be removed.
        Otherwise, the add_tier will be kept, or added in case the member did not have it."""
        assert add_tier is None or (type(add_tier) == int and 0 <= add_tier <= 19), self.ASSERT_INT.format(n=add_tier)
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

            tier_name = get_tier_name(add_tier)
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
        notice = None
        platform_out = get_url_platform(platform_in)
        if not platform_out:
            notice = self.PLATFORM_INVALID
        elif platform_out == "switch":
            platform_out = False
            notice = self.SWITCH_UNSUPPORTED
        if notice:
            id_out = False
        else:  # Valid platform.
            if platform_out == "steam":
                # TODO: convert [U:1:{n}] to just {n}, to support ID3 in their original format.
                if id_in.lstrip("-").isdigit():
                    id_out = self.int_to_steam_id64(int(id_in))
                else:  # Do regex checks for /id/ and /profiles/.
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

    @staticmethod
    def int_to_steam_id64(id_64: int) -> int:
        """Converts a SteamID64 to the one that the Psyonix API recognizes

        The reason for this is that Valve accepts multiple ID64s for the same account."""
        return (id_64 % (2 ** 32)) + 76561197960265728

    def rank_summary_str(self, player_skills: dict, best_list_id: int, unplayed_lists: set) -> (str, str):
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
                tier = get_tier_name(tier_n)
                div = i["division"] + 1
                # Embolden best playlist.
                bold = "**" if playlist_id == best_list_id else ""
                tier_div = "{} Div. {}".format(tier, div) if tier_n not in (0, 19) else tier
                playlist_str = self.MINIMAL_RANKED.format(ls=playlist, n=rating, bold=bold, tier_div=tier_div)
            desc_rows[playlist_id] = playlist_str
        for n in unplayed_lists:
            playlist = self.PLAYLIST_ID_MINIMAL[n]
            desc_rows[n] = self.MINIMAL_NO_MATCHES.format(playlist)
        # Split list into normal and special (to make menu-embed possible).
        normal_lists, special_lists = [], []
        for k, v in sorted(desc_rows.items()):
            normal_lists.append(v) if k < 20 else special_lists.append(v)
        return "\n".join(normal_lists), "\n".join(special_lists)

    def make_lfg_embed(self, response: dict, url_platform: str, user: discord.Member = None) -> list:
        """Make the embed for the LFG commands."""
        player_name = response["user_name"]
        player_skills = response.get("player_skills")
        if not player_skills:  # Debug exception.
            raise Exception("lfg -> No player skills")
        best_tier, best_list_id, played_lists = best_playlist(player_skills)
        unplayed_lists = {n for n in self.PLAYLIST_IDS if n not in played_lists}
        # Create rows for each playlist.
        summary_tuple = self.rank_summary_str(player_skills, best_list_id, unplayed_lists)
        # Set author and description. Profile links only exist for Steam.
        player_url = self.STEAM_PROFILE_URL.format(response["user_id"]) \
            if url_platform == "steam" else discord.Embed.Empty
        # Create embed, and use the highest tier's colour.
        return_list = []
        for summary in summary_tuple:
            embed = discord.Embed()
            embed.colour = get_tier_colour(best_tier)
            embed.set_author(name="Rocket League Stats - {}".format(player_name), url=player_url)
            embed.description = summary
            if user:
                embed.set_footer(text=f"ID: {user.id}", icon_url=user.avatar_url_as(static_format="png"))
            return_list.append(embed)
        return return_list

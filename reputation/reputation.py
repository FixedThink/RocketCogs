# Default Library.
import asyncio
import datetime as dt
from asyncio import sleep
from typing import Literal, Optional, Tuple, Set

# Used by Red.
import discord
import redbot.core.utils.menus as red_menu
from redbot.core import commands, checks, Config, data_manager
from redbot.core.bot import Red  # For type hints.
from redbot.core.commands.context import Context  # For type hints.

# Local files.
from .db_queries import DbQueries


class Reputation(commands.Cog):
    """Give people reputation and reward reputable members"""
    __author__ = "#s#8059, HRAND5#0101"

    # Defaults.
    DEFAULT_COOLDOWN = 60 * 60 * 24 * 7  # 1 week (cooldown for user A to give user B rep).
    DEFAULT_DECAY = 60 * 60 * 24 * 7 * 5  # 5 weeks (35 days, time before the reputation role will decay).
    DEFAULT_LOG_MESSAGE = "{user} has received the reputation role."
    LOOP_SLEEP_TIME = 60 * 60 * 12  # 12 hours.

    # Notice emote prefixes.
    BIN = ":put_litter_in_its_place: "
    ERROR = ":x: Error: "
    DONE = ":white_check_mark: "
    # Notices.
    DEL_REQUEST = ":information_source: `reputation`: Data removal request for userID {} of type `{}`.\n" \
                  "Please consider deleting unnecessary data (such as usernames, and the reputation message itself), " \
                  "whilst not deleting data necessary for the operation of the reputation system."
    BAD_CHANNEL = ERROR + "Reputation not added, please use the correct channel for reputations!"
    REP_CHANNEL_CLEARED = BIN + "Cleared the channel configuration. Reputation can now be given in any channel."
    LOG_CHANNEL_CLEARED = BIN + "Cleared the channel configuration. Logs are disabled."
    CHANNEL_SET = DONE + "Set the channel to {}."
    COOLDOWN_CLEARED = BIN + "Set the reputation cooldown back to the default settings."
    COOLDOWN_REMOVED = BIN + "Disabled the reputation cooldown."
    COOLDOWN_SET = DONE + "Set the reputation cooldown to {}."
    DECAY_CLEARED = BIN + "Set the reputation decay back to the default settings."
    DECAY_REMOVED = BIN + "Disabled reputation decay."
    DECAY_SET = DONE + "Set the reputation decay to {}"
    DECAY_THRESHOLD_CLEARED = BIN + "Successfully set the decay threshold to the default: `2`"
    DECAY_THRESHOLD_SET = DONE + "Successfully set the decay threshold to {}"
    LOG_MSG_RESET = BIN + "Log message reset to default."
    MANUAL_CHECK = DONE + "Performed the manual server check!\n" \
                          "**{add_n}** member{s} received a role, **{del_n}** lost a role."
    REP_BAD_INPUT = ERROR + "Your input was not fully valid! Note that a username is case-sensitive.\n" \
                            "This message (and yours) will self-destruct after 30 seconds."
    REP_NOT_COOL = ERROR + "You have given that user a reputation too recently!"
    REP_COMMENT_HAS_AT = ERROR + "Please do not tag any people in the rep reason!\n" \
                                 "If you must mention someone, use their name instead."
    REP_YOURSELF = ERROR + "Loving yourself is great, but giving yourself reputation is a bit extreme."
    ROLE_CONFIG_CLEARED = BIN + "Cleared the role configuration.\n" \
                                "You can configure the role by including it at the end of the command."
    ROLE_CONFIG_SET = DONE + "Successfully configured the role."
    ROLE_THRESHOLD_CLEARED = BIN + "Successfully set the role threshold to the default value: `10`"
    ROLE_THRESHOLD_SET = DONE + "Successfully set the role threshold to {}"
    USER_OPT_IN = DONE + "You will now receive a reputation role when eligible."
    USER_OPT_OUT = BIN + "You will no longer receive a reputation role, even when eligible."
    # Audit log reasons.
    ONE_ADD = "Single reputation role check"
    GLD_ADD = "Guild reputation role check"
    # Other constant strings.
    COUNT_DESC = "{} has received **{}** reputation{} from **{}** user{}."
    COUNT_NO_REPS = "{} has not received any reputations."
    LEADERBOARD_NO_REPS = ERROR + "No reputations in the database."
    LEADERBOARD_DESC = "Users with at least 1 reputation: **{}**"
    LEADERBOARD_ROW = "`{:0{}d}` {} • **{}**"
    OFF = "Disabled"
    TIME_FMT = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/reputation.db"
        self.config = Config.get_conf(self, identifier=5006, force_registration=True)
        self.config.register_guild(cooldown_period=self.DEFAULT_COOLDOWN, decay_period=self.DEFAULT_DECAY,
                                   reputation_role=None, role_threshold=10, decay_threshold=2,
                                   reputation_channel=None, shadow_role=None, log_channel=None,
                                   log_message=self.DEFAULT_LOG_MESSAGE)
        self.config.register_user(opt_out=False)
        self.rep_db = DbQueries(self.PATH_DB)
        self.decay_loop = asyncio.ensure_future(self.periodical_decay_check())

    # Loops
    async def periodical_decay_check(self):
        """Periodically perform the decay check for all guilds the bot is in"""
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog(self.__class__.__name__):
            for gld in self.bot.guilds:
                await self.guild_role_check(gld)
            await asyncio.sleep(self.LOOP_SLEEP_TIME)

    # Commands
    @commands.guild_only()  # Group not restricted to admins so that abstain can be used.
    @commands.group(name="repset", invoke_without_command=True)
    async def _reputation_settings(self, ctx: Context):
        """Configure the reputation commands

        Note that the `channel` command does not take parameters and will use the current channel when called."""
        await ctx.send_help()

    # TODO: Update for added config options.
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="view")
    async def view_current_config(self, ctx: Context):
        """Shows the current configuration of the module"""
        gld = ctx.guild
        config_dict = await self.config.guild(gld).all()
        embed = discord.Embed(title="Current Reputation configuration", colour=discord.Colour.lighter_grey())
        # Log message
        log_message = config_dict["log_message"]
        embed.description = f"```{log_message}```" if log_message else "`log message not set`"
        # Channel ID.
        chn_id = config_dict["reputation_channel"]
        embed.add_field(name="Reputation channel", value=f"<#{chn_id}>" if chn_id else self.OFF)
        # Reputation role.
        rep_role_obj = await self.get_reputation_role_obj(gld)
        rep_role_str = rep_role_obj.mention if rep_role_obj else self.OFF
        embed.add_field(name="Reputation role", value=rep_role_str)
        # Reputation cooldown.
        cooldown = config_dict["cooldown_period"]
        embed.add_field(name="Cooldown period", value=str(dt.timedelta(seconds=cooldown)) if cooldown else self.OFF)
        # Log channel.
        log_channel: discord.TextChannel = discord.utils.get(gld.channels, id=config_dict["log_channel"])
        embed.add_field(name="Log channel", value=log_channel.mention if log_channel else self.OFF)
        # Shadow role.
        shadow_role_obj = await self.get_shadow_role_obj(gld)
        shadow_role_str = shadow_role_obj.mention if shadow_role_obj else self.OFF
        embed.add_field(name="Shadow role", value=shadow_role_str)
        # Reputation decay.
        decay = config_dict["decay_period"]
        embed.add_field(name="Decay period", value=str(dt.timedelta(seconds=decay)) if decay else self.OFF)
        # Reputation threshold.
        role_min = str(config_dict["role_threshold"])
        embed.add_field(name="Role threshold", value=role_min if role_min else self.OFF)
        # Decay threshold.
        decay_min = str(config_dict["decay_threshold"])
        embed.add_field(name="Decay threshold", value=decay_min if decay_min else self.OFF)
        # Send embed.
        await ctx.send(embed=embed)

    @commands.guild_only()
    @_reputation_settings.command(name="opt_out", aliases=["abstain"])
    async def role_opt_out(self, ctx: Context):
        """Opt in/out of receiving a reputation role

        If you opt out, you will not receive a role even if you are eligible for it."""
        aut = ctx.author
        current_opt_out = await self.config.user(aut).opt_out()
        # Set opt_out as the inverse of current_opt_out (as this command is a toggle).
        await self.config.user(aut).opt_out.set(not current_opt_out)
        if current_opt_out:
            to_send = self.USER_OPT_IN
            await self.user_role_check(ctx)  # TODO: modify the opt-in message if role is granted.
        else:
            to_send = self.USER_OPT_OUT
            rep_role_obj = await self.get_reputation_role_obj(ctx.guild)
            if rep_role_obj and rep_role_obj in aut.roles:
                await aut.remove_roles(rep_role_obj)
        await ctx.send(to_send)

    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="decay_threshold")
    async def set_decay_threshold(self, ctx: Context, threshold: int = None):
        """Configure the decay threshold

        A user must have received at least this amount of reputation during the decay period to be eligible for a role.
        """
        gld = ctx.guild
        if not threshold:  # Clear config.
            await self.config.guild(gld).decay_threshold.clear()
            msg = self.DECAY_THRESHOLD_CLEARED
        else:  # Set decay threshold to int provided.
            await self.config.guild(gld).decay_threshold.set(threshold)
            msg = self.DECAY_THRESHOLD_SET.format(str(threshold))
        await ctx.send(msg)

    @_reputation_settings.command(name="log_message")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def set_log_message(self, ctx: Context, *, message_text=None):
        """Set the message to be used when a member gets the reputation role for the first time

        In order to specify a user mention, please use `{user}` inside the text.
        Please avoid the usage of any other curly brackets."""
        if message_text is None:
            await self.config.guild(ctx.guild).log_message.clear()
            await ctx.send(self.LOG_MSG_RESET)
        else:
            await self.config.guild(ctx.guild).log_message.set(message_text)
            await ctx.tick()

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="role")
    async def set_reputation_role(self, ctx: Context, role: discord.Role = None):
        """Configure the reputation role to be given

        If no role is provided, the role functionality will be disabled."""
        gld = ctx.guild
        if not role:  # Clear config.
            await self.config.guild(gld).reputation_role.clear()
            msg = self.ROLE_CONFIG_CLEARED
        else:  # Set reputation role to role provided.
            await self.config.guild(gld).reputation_role.set(role.id)
            msg = self.ROLE_CONFIG_SET
        await ctx.send(msg)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="shadow_role")
    async def set_shadow_role(self, ctx: Context, role: discord.Role = None):
        """Configure the shadow reputation role

        This role is for everyone who fulfils the base reputation threshold,
        including those whose main role has decayed, or those who abstained from the main role."""
        gld = ctx.guild
        if not role:  # Clear config.
            await self.config.guild(gld).shadow_role.clear()
            msg = self.ROLE_CONFIG_CLEARED
        else:  # Set reputation role to role provided.
            await self.config.guild(gld).shadow_role.set(role.id)
            msg = self.ROLE_CONFIG_SET
        await ctx.send(msg)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="log_channel")
    async def set_log_channel(self, ctx: Context):
        """Set the current channel as the reputation channel

        If this channel is already the reputation channel, the config will be cleared."""
        channel = ctx.channel
        gld = ctx.guild
        if channel.id == await self.config.guild(gld).log_channel():
            await self.config.guild(gld).log_channel.clear()
            msg = self.LOG_CHANNEL_CLEARED
        else:
            await self.config.guild(gld).log_channel.set(channel.id)
            msg = self.CHANNEL_SET.format(channel.mention)
        await ctx.send(msg)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="reputation_channel")
    async def set_rep_channel(self, ctx: Context):
        """Set the current channel as the reputation channel

        If this channel is already the reputation channel, the config will be cleared."""
        channel = ctx.channel
        gld = ctx.guild
        if channel.id == await self.config.guild(gld).reputation_channel():
            await self.config.guild(gld).reputation_channel.clear()
            msg = self.REP_CHANNEL_CLEARED
        else:
            await self.config.guild(gld).reputation_channel.set(channel.id)
            msg = self.CHANNEL_SET.format(channel.mention)
        await ctx.send(msg)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="cooldown")
    async def set_rep_cooldown(self, ctx: Context, days: int, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """Set the reputation cooldown

        If a cooldown is active, user A cannot give user B a reputation for the set period after the last rep pair.

        You must use the `days` argument. If the time provided equals zero, the cooldown will be disabled.
        If the time provided < 0, then the config will be reset to its default (1 week).
        """
        gld = ctx.guild
        delta = dt.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        delta_sec = int(delta.total_seconds())  # Float by default.
        if delta_sec < 0:  # Clear config.
            await self.config.guild(gld).cooldown_period.clear()
            msg = self.COOLDOWN_CLEARED
        elif delta_sec == 0:  # Set config to None.
            await self.config.guild(gld).cooldown_period.set(None)
            msg = self.COOLDOWN_REMOVED
        else:  # Set cooldown to time provided.
            await self.config.guild(gld).cooldown_period.set(delta_sec)
            msg = self.COOLDOWN_SET.format(str(delta))
        await ctx.send(msg)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="decay")
    async def set_rep_decay(self, ctx: Context, days: int, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """Set the decay period

        If the decay is active, a user will lose their role if they haven't received sufficient reputation \
        during the decay period.

        You must use the `days` argument. If the time provided equals zero, the decay will be disabled.
        If the time provided < 0, then the config will be reset to its default (5 weeks).
        """
        gld = ctx.guild
        delta = dt.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        delta_sec = int(delta.total_seconds())  # Float by default.
        if delta_sec < 0:  # Clear config.
            await self.config.guild(gld).decay_period.clear()
            msg = self.DECAY_CLEARED
        elif delta_sec == 0:  # Set config to None.
            await self.config.guild(gld).decay_period.set(None)
            msg = self.DECAY_REMOVED
        else:  # Set decay to time provided.
            await self.config.guild(gld).decay_period.set(delta_sec)
            msg = self.DECAY_SET.format(str(delta))
        await ctx.send(msg)

    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="role_threshold")
    async def set_role_threshold(self, ctx: Context, threshold: int = None):
        """Set the role threshold

        Role threshold is the amount of reputations you need to have received before getting the reputation role.
        """
        gld = ctx.guild
        if not threshold:  # Clear config.
            await self.config.guild(gld).role_threshold.clear()
            msg = self.ROLE_THRESHOLD_CLEARED
        else:  # Set role threshold to int provided.
            await self.config.guild(gld).role_threshold.set(threshold)
            msg = self.ROLE_THRESHOLD_SET.format(str(threshold))
        await ctx.send(msg)

    @_reputation_settings.command(name="full_check")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def manual_guild_check(self, ctx: Context):
        """Do a manual reputation eligibility check for all members on the server"""
        add_n, del_n = await self.guild_role_check(ctx.guild)
        await ctx.send(self.MANUAL_CHECK.format(add_n=add_n, s=self.plural_s(add_n), del_n=del_n))

    @commands.guild_only()
    @commands.command()
    async def rep(self, ctx: Context, user: discord.Member, *, comment: str = None):
        """Give someone reputation

        You may add a comment, but this is not necessary."""
        # TODO: Possibly restrict length of rep message.
        aut = ctx.author
        gld = ctx.guild
        channel = ctx.channel
        cooldown_secs = await self.config.guild(ctx.guild).cooldown_period()
        if user == ctx.author:
            notice = self.REP_YOURSELF
        elif comment and "@" in comment:
            notice = self.REP_COMMENT_HAS_AT
        else:
            rep_channel = await self.config.guild(gld).reputation_channel()
            if rep_channel is None or rep_channel == channel.id:
                rep_msg = None if not comment else comment  # Add message as NULL to db if empty string.
                is_added = await self.rep_db.insert_rep(aut.id, str(aut), user.id, str(user),
                                                        ctx.message.created_at, rep_msg, cooldown_secs)
                if is_added:
                    notice = None
                    await self.user_role_check(ctx, member=user)
                    await ctx.tick()
                else:
                    notice = self.REP_NOT_COOL
            else:
                notice = self.BAD_CHANNEL
        if notice:  # Delete after some seconds as to not clog the channel.
            await ctx.send(notice, delete_after=20)
            await sleep(20)
            try:  # Delete the original message at the same time.
                await ctx.message.delete()
            except discord.Forbidden:
                print("rep -> I lack manage messages permissions!")

    @rep.error
    async def rep_error(self, ctx, error):
        """Ensure that input errors cause message deletions"""
        if isinstance(error, commands.BadArgument):
            await ctx.send(self.REP_BAD_INPUT, delete_after=30)
        # Delete the original message.
        await sleep(20)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("rep_error -> I lack manage messages permissions!")

    @commands.command(name="reps", aliases=["rep_count"])
    async def rep_count(self, ctx: Context, user: discord.Member = None):
        """See the amount of reps given to a user"""
        if user is None:
            user = ctx.author
        embed = discord.Embed(title="User reputation count", colour=discord.Colour.purple())

        count, distinct_count, dt_str = await self.rep_db.user_rep_count(user.id)
        if count:
            cs, dcs = self.plural_s(count), self.plural_s(distinct_count)
            embed.description = self.COUNT_DESC.format(user.mention, count, cs, distinct_count, dcs)
            embed.timestamp = dt.datetime.strptime(dt_str, self.TIME_FMT)
            embed.set_footer(text="User ID: {} | Last rep given".format(user.id))
        else:
            embed.description = self.COUNT_NO_REPS.format(user.mention)
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lboard"])
    async def rep_leaderboard(self, ctx: Context):
        """See the reputation leaderboard

        Ties are broken based on who received a reputation the most recently."""
        board_list = await self.rep_db.rep_leaderboard()
        if board_list is None:
            await ctx.send(self.LEADERBOARD_NO_REPS)
        else:  # At least one rep given
            repped_count = len(board_list)
            width = len(str(repped_count))
            desc = self.LEADERBOARD_DESC.format(repped_count)
            # Split the leaderboard into fields with at most 10 rows each.
            field_list = []
            for i in range((repped_count // 10) + 1):
                start = 10 * i
                end = start + 10 if repped_count > (start + 10) else repped_count

                field_name = "{}-{}".format(start + 1, end)
                field_value = "\n".join((self.LEADERBOARD_ROW.format((i + 1), width, f"<@{t[0]}>", t[1])
                                         for i, t in enumerate(board_list[start:end], start=start)))
                field_list.append((field_name, field_value))

            field_count = len(field_list)
            if field_count == 1:  # If only 1 field, send as 1 embed.
                f_name = field_list[0][0]
                f_value = field_list[0][1]
                embed = discord.Embed(title="Reputation leaderboard", description=desc, colour=discord.Colour.purple())
                embed.add_field(name=f_name, value=f_value)
                footer = "1 of 1"
                embed.set_footer(text=footer)
                await ctx.send(embed=embed)
            else:  # If more than one field, send as a pagified menu.
                embed_list = []
                for n, (f_name, f_value) in enumerate(field_list, start=1):
                    embed = discord.Embed(title="Reputation leaderboard", colour=discord.Colour.purple())
                    embed.description = desc
                    embed.add_field(name=f_name, value=f_value)
                    footer = "{n} of {total}.".format(n=n, total=field_count)
                    embed.set_footer(text=footer)
                    embed_list.append(embed)
                await red_menu.menu(ctx, embed_list, red_menu.DEFAULT_CONTROLS, timeout=30.0)

    # Utilities
    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """Delete someone's linked account (only info stored)

        This does not take care of any rank roles that the user may have."""
        await self.bot.send_to_owners(self.DEL_REQUEST.format(user_id, requester))

    async def user_role_check(self, ctx: Context, member: discord.Member = None) -> None:
        """
        :param ctx: The Context object of the message that requests the check
        :param member: (Optional) The user to check. If not provided, the author of the command will be checked instead.
        :return: None

        Check whether a user is eligible for the reputation role

        If so, the role will be added if they do not have it. If not, the role will be removed if they have it.
        """
        gld = ctx.guild
        if member is None:
            member = ctx.author

        rep_role = await self.get_reputation_role_obj(gld)
        user_opt_out = await self.config.user(member).opt_out()
        if rep_role and not user_opt_out:  # Don't check if the role is not configured.
            has_role: bool = rep_role in member.roles  # Check if user has the reputation role.
            # Check whether a user's total reputations exceed the threshold.
            u_total_reps: int = (await self.rep_db.user_rep_count(member.id))[0]
            gld_config = await self.config.guild(gld).all()
            role_threshold = gld_config["role_threshold"]
            if u_total_reps >= role_threshold:
                # Get decay period, decay threshold, and use those for comparisons.
                decay_secs = gld_config["decay_period"]
                if decay_secs:  # Decay threshold configured.
                    decay_min = gld_config["decay_threshold"]
                    decay_dt = ctx.message.created_at - dt.timedelta(seconds=decay_secs)
                    recent_rep_count = await self.rep_db.recent_reps(user_id=member.id, start_time=decay_dt)
                    if not has_role and recent_rep_count >= decay_min:
                        await self.give_reputation_role(member, rep_role, gld, gld_config, reason=self.ONE_ADD)
                    elif has_role and recent_rep_count < decay_min:
                        await member.remove_roles(rep_role)
                elif not has_role:  # No decay, but above rep threshold.
                    await self.give_reputation_role(member, rep_role, gld, gld_config, reason=self.ONE_ADD)
            elif has_role:
                await member.remove_roles(rep_role)

    async def give_reputation_role(self, member: discord.Member, rep_role: discord.Role,
                                   guild: discord.Guild, guild_config: dict, reason: str = None) -> bool:
        """
        :param member: The member to which a reputation role should be added
        :param rep_role: The role to be given.
        :param guild: The guild on which the role should be given.
        :param guild_config: Configuration of this module for guild.
        :param reason: (Optional) The reason in the audit log for adding the role(s).
        :return: Boolean determining whether a user has received a role.

        Give a user the reputation role, and perform other operations if need be

        The reputation role will only be added if they did not opt out for it.
        """
        to_return, should_log = False, False
        shadow_role = await self.get_shadow_role_obj(guild)
        opt_out = await self.config.user(member).opt_out()

        roles_to_add = []
        if shadow_role:
            if shadow_role not in member.roles:
                should_log = True
                roles_to_add.append(shadow_role)
                if not opt_out:
                    roles_to_add.append(rep_role)
            elif not opt_out:
                roles_to_add.append(rep_role)
        elif not opt_out:
            should_log = True
            roles_to_add.append(rep_role)

        if roles_to_add:  # First add role(s), then log (if needed).
            to_return = True
            await member.add_roles(*roles_to_add, reason=reason)
            if should_log:
                log_channel_id, log_message = guild_config["log_channel"], guild_config["log_message"]
                log_channel = discord.utils.get(guild.channels, id=log_channel_id)
                assert log_channel or not log_channel_id, "Log channel is configured but does not exist!"
                if log_channel:
                    await log_channel.send(log_message.format(user=member.mention))
        return to_return

    async def guild_role_check(self, gld: discord.Guild) -> Tuple[int, int]:
        """
        Check which users on a guild should or shouldn't have the rep role

        Roles will be edited accordingly.
        """
        rep_role = await self.get_reputation_role_obj(gld)
        if rep_role:
            gld_config = await self.config.guild(gld).all()
            db_args = gld_config["decay_threshold"], gld_config["role_threshold"], gld_config["decay_period"]
            eligible_set = await self.rep_db.all_eligible_users(*db_args)
            current_list = [member for member in gld.members if rep_role in member.roles]
            current_id_set = {m.id for m in current_list}
            # Get list of users which should gain the role, and list which should lose the role.
            give_set: Set[int] = {i for i in eligible_set if i not in current_id_set}
            give_tup: Tuple[discord.Member, ...] = tuple(m for m in gld.members if m.id in give_set)
            take_tup: Tuple[discord.Member, ...] = tuple(m for m in current_list if m.id not in eligible_set)

            remove_count = len(take_tup)
            add_count = 0  # Accumulator.
            for member in give_tup:
                is_given = await self.give_reputation_role(member, rep_role, gld, gld_config, reason=self.GLD_ADD)
                add_count += bool(is_given)
            for member in take_tup:
                await member.remove_roles(rep_role, reason=self.GLD_ADD)
            return add_count, remove_count

    async def get_reputation_role_obj(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Get the reputation role object if a role ID is set, None otherwise

        If a role ID is set but no role is found, this will return an error"""
        rep_role = None
        rep_role_id = await self.config.guild(guild).reputation_role()
        if rep_role_id:
            rep_role = discord.utils.get(guild.roles, id=rep_role_id)
            assert rep_role, "The reputation role ID is configured, but the role does not exist!"
        return rep_role

    async def get_shadow_role_obj(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Get the shadow role object if a role ID is set, None otherwise

        If a role ID is set but no role is found, this will return an error"""
        rep_role = None
        rep_role_id = await self.config.guild(guild).shadow_role()
        if rep_role_id:
            rep_role = discord.utils.get(guild.roles, id=rep_role_id)
            assert rep_role, "The shadow role ID is configured, but the role does not exist!"
        return rep_role

    @staticmethod
    def plural_s(n: int) -> str:
        """Returns an 's' if n is not 1, otherwise returns an empty string"""
        return "" if n == 1 else "s"

# Default Library.
import datetime as dt

# Used by Red.
import discord
from redbot.core import commands
from redbot.core import checks, Config, data_manager
from redbot.core.bot import Red
import redbot.core.utils.menus as red_menu

# Local files.
from .db_queries import DbQueries


class Reputation(commands.Cog):
    """Give people reputation and reward reputable members"""
    # TODO: Add leaderboard command, which shows the users with the most reputation. Make a menu if possible.
    __author__ = "#s#8059, HRAND5#0101"

    BIN = ":put_litter_in_its_place: "
    ERROR = ":x: Error: "
    DONE = ":white_check_mark: "

    DEFAULT_COOLDOWN = 60 * 60 * 24 * 7  # 1 week (cooldown for user A to give user B rep).
    DEFAULT_DECAY = 60 * 60 * 24 * 7 * 5  # 5 weeks (35 days, time before the reputation role will decay).
    BAD_CHANNEL = ERROR + "Reputation not added, please use the correct channel for reputations!"
    CHANNEL_CLEARED = BIN + "Cleared the channel configuration. Reputation can now be given in any channel."
    CHANNEL_SET = DONE + "Set the reputation channel to {}."
    COOLDOWN_CLEARED = BIN + "Set the reputation cooldown back to the default settings."
    COOLDOWN_REMOVED = BIN + "Disabled the reputation cooldown."
    COOLDOWN_SET = DONE + "Set the reputation cooldown to {}."
    REP_NOT_COOL = ERROR + "You have given that user a reputation too recently!"
    REP_COMMENT_HAS_AT = ERROR + "Please do not tag any people in the rep reason!\n" \
                                 "If you must mention someone, use their name instead."
    REP_YOURSELF = ERROR + "Loving yourself is great, but giving yourself reputation is a bit extreme."
    COUNT_DESC = "{} has received **{}** reputation{} from **{}** user{}."
    COUNT_NO_REPS = "{} has not received any reputations."
    LEADERBOARD_NO_REPS = ERROR + "No reputations in the database."
    LEADERBOARD_ROW = "`{}` {} - {} reps"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/reputation.db"
        self.config = Config.get_conf(self, identifier=5006, force_registration=True)
        # TODO: Make decay period configurable with a command (like cooldown).
        # TODO: Make active/decayed roles configurable with command.
        # TODO: Make role/decay threshold configurable with a command, where < 0 resets and == 0 gives error.
        self.config.register_guild(cooldown_period=self.DEFAULT_COOLDOWN, decay_period=self.DEFAULT_DECAY,
                                   active_role=None, decayed_role=None, decay_threshold=2,
                                   role_threshold=10, reputation_channel=None)
        self.rep_db = DbQueries(self.PATH_DB)

    # Events

    # Commands
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="repset", invoke_without_command=True)
    async def _reputation_settings(self, ctx):
        """Configure the reputation commands"""
        await ctx.send_help()  # TODO: Add codeblock that shows current config.

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="channel")
    async def set_rep_channel(self, ctx):
        """Set the reputation channel
        The reputation channel will be set to the channel in which this command is executed.
        If this channel is already the reputation channel, the config will be cleared."""
        channel = ctx.channel
        gld = ctx.guild
        if channel.id == await self.config.guild(gld).reputation_channel():
            await self.config.guild(gld).reputation_channel.clear()
            msg = self.CHANNEL_CLEARED
        else:
            await self.config.guild(gld).reputation_channel.set(channel.id)
            msg = self.CHANNEL_SET.format(channel.mention)
        await ctx.send(msg)

    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="cooldown")
    async def set_rep_cooldown(self, ctx, days: int, hours: int = 0, minutes: int = 0, seconds: int = 0):
        """Set the reputation cooldown
        If a cooldown is active, user A cannot give user B a reputation for the set period after the last rep pair.
        You must use the days argument. If the time provided equals zero, the config will be set to None.
        If the time provided < 0, then the config will be reset to its default (1 week).
        """
        gld = ctx.guild
        delta = dt.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        delta_sec = int(delta.total_seconds())  # float by default.
        if delta_sec < 0:  # Clear config.
            await self.config.guild(gld).cooldown_period.clear()
            msg = self.COOLDOWN_CLEARED
        elif delta_sec == 0:  # Set config to None.
            await self.config.guild(gld).cooldown_period.set(None)
            msg = self.COOLDOWN_REMOVED
        else:  # Set time provided.
            await self.config.guild(gld).cooldown_period.set(delta_sec)
            msg = self.COOLDOWN_SET.format(str(delta))
        await ctx.send(msg)

    @commands.guild_only()
    @commands.command()
    async def rep(self, ctx, user: discord.Member, *, comment: str = None):
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
                is_added = await self.rep_db.insert_rep(aut.id, str(aut), user.id, str(user), rep_msg, cooldown_secs)
                if is_added:
                    notice = None
                    await ctx.tick()
                else:
                    notice = self.REP_NOT_COOL
            else:
                notice = self.BAD_CHANNEL
        if notice:  # Delete after some seconds as to not clog the channel.
            await ctx.send(notice, delete_after=20)

    @commands.command(name="reps", aliases=["rep_count"])
    async def rep_count(self, ctx, user: discord.Member = None):
        """See the amount of reps given to a user"""
        if user is None:
            user = ctx.author
        embed = discord.Embed(title="User reputation count", colour=discord.Colour.purple())

        count, distinct_count, dt_str = await self.rep_db.user_rep_count(user.id)
        if count:
            cs, dcs = self.plural_s(count), self.plural_s(distinct_count)
            embed.description = self.COUNT_DESC.format(user.mention, count, cs, distinct_count, dcs)
            embed.timestamp = dt.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
            embed.set_footer(text="User ID: {} | Last rep given".format(user.id))
        else:
            embed.description = self.COUNT_NO_REPS.format(user.mention)
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard")
    async def rep_leaderboard(self, ctx):
        lb_data = await self.rep_db.rep_leaderboard()

        if lb_data is None:
            await ctx.send(self.LEADERBOARD_NO_REPS)
        else:  # At least one rep given
            lb_length = len(lb_data)
            desc = "Total users that have received at least 1 reputation: **{}**".format(lb_length)

            # Split the leaderboard into fields with under 10 rows
            field_list = []
            for i in range((lb_length // 10) + 1):
                start = 10 * i
                end = start + 10 if lb_length > (start + 10) else lb_length

                field_name = "{}-{}".format(start + 1, end)
                field_value = "\n".join((self.LEADERBOARD_ROW.format((i + 1), self.mention_from_id(t[0]), t[1])
                                         for i, t in enumerate(lb_data[start:end], start = start)))
                field_list.append((field_name, field_value))

            embed_list = []
            field_count = len(field_list)
            if field_count == 1:  # If only 1 field, send as 1 embed
                f_name = field_list[0][0]
                f_value = field_list[0][1]
                embed = discord.Embed(title="Reputation leaderboard", description=desc, colour=discord.Colour.purple())
                embed.add_field(name=f_name, value=f_value)
                footer = "Page 1 out of 1."
                embed.set_footer(text=footer)
                await ctx.send(embed=embed)
            else:  # If more than one field, send as a pagified menu.
                for n, (f_name, f_value) in enumerate(field_list, start=1):
                    embed = discord.Embed(title="Reputation leaderboard", description=desc, colour=discord.Colour.purple())
                    embed.add_field(name=f_name, value=f_value)
                    footer = "Page {n} out of {total}.".format(n=n, total=field_count)
                    embed.set_footer(text=footer)
                    embed_list.append(embed)
                await red_menu.menu(ctx, embed_list, red_menu.DEFAULT_CONTROLS, timeout=30.0)

    # Utilities
    @staticmethod
    def plural_s(n: int) -> str:
        """Returns an 's' if n is not 1, otherwise returns an empty string"""
        return "" if n == 1 else "s"

    @staticmethod
    def mention_from_id(user_id: int) -> str:
        return "<@" + str(user_id) + ">"

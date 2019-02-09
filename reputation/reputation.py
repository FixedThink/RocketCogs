# Default Library.
import datetime as dt

# Used by Red.
import discord
from redbot.core import commands
from redbot.core import checks, Config, data_manager
from redbot.core.bot import Red

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
    REP_WHY_MISSING = ERROR + "Please include a reason to why this user deserves a rep."
    REP_WHY_HAS_MENTION = ERROR + "Please do not tag any people in the rep reason!\n" \
                                  "If you must mention someone, use their name instead."
    COUNT_DESC = "{} has received **{}** reputations{} from **{}** user{}."
    COUNT_NO_REPS = "{} has not received any reputations."
    
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/reputation.db"
        self.config = Config.get_conf(self, identifier=5006, force_registration=True)
        # TODO: Make decay period configurable with a command (like cooldown).
        # TODO: Make active/decayed roles configurable with command.
        self.config.register_guild(cooldown_period=self.DEFAULT_COOLDOWN, decay_period=self.DEFAULT_DECAY,
                                   active_role=None, decayed_role=None, reputation_channel=None)
        self.rep_db = DbQueries(self.PATH_DB)

    # Events

    # Commands
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="repset", invoke_without_command=True)
    async def _reputation_settings(self, ctx):
        """Configure the reputation commands"""
        await ctx.send_help()  # TODO: Add codeblock that shows current config.

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

    @commands.command()
    async def rep(self, ctx, user: discord.Member, *, why: str = None):
        """Give someone reputation"""
        # TODO: Possibly restrict length of rep message.
        aut = ctx.author
        gld = ctx.guild
        channel = ctx.channel
        cooldown_secs = await self.config.guild(ctx.guild).cooldown_period()
        if why and "@" in why:
            notice = self.REP_WHY_HAS_MENTION
        else:
            rep_channel = await self.config.guild(gld).reputation_channel()
            if rep_channel is None or rep_channel == channel.id:
                rep_msg = None if not why else why  # Add message as NULL to db if empty string.
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

    # Utilities
    @staticmethod
    def plural_s(n: int) -> str:
        """Returns an 's' if n is not 1, otherwise returns an empty string"""
        return "" if n == 1 else "s"

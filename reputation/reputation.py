# Default Library.

# Used by Red.
import discord
from redbot.core import commands
from redbot.core import checks, Config, data_manager
from redbot.core.bot import Red

# Local files.
from .db_queries import DbQueries


class Reputation(commands.Cog):
    """Give people reputation and reward reputable members"""
    __author__ = "#s#8059, HRAND5#0101"

    BIN = ":put_litter_in_its_place: "
    ERROR = ":x: Error: "
    DONE = ":white_check_mark: "

    DEFAULT_COOLDOWN = 60 * 60 * 24 * 7  # 1 week (cooldown for user A to give user B rep).
    REP_SUCCESS = DONE + "Rep added!"
    REP_NOT_COOL = ERROR + "You have given that user a reputation too recently!"
    REP_BAD_CHANNEL = ERROR + "Reputation not added, please use the correct channel for reputations!"
    REP_CHANNEL_SET = DONE + "Set the reputation channel to {}."
    REP_CHANNEL_SET_ALL = BIN + "Cleared the channel configuration. Reputation can now be given in any channel."
    REP_WHY_MISSING = ERROR + "Please include a reason to why this user deserves a rep."
    REP_WHY_HAS_MENTION = ERROR + "Please do not tag any people in the rep reason!\n" \
                                  "If you must mention someone, use their name instead."
    
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/reputation.db"
        self.config = Config.get_conf(self, identifier=5006, force_registration=True)
        self.config.register_guild(reputation_channel=None, reputation_cooldown=self.DEFAULT_COOLDOWN)
        self.rep_db = DbQueries(self.PATH_DB)

    # Events

    # Commands
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="repset", invoke_without_command=True)
    async def _reputation_settings(self, ctx):
        """Configure the reputation commands"""
        await ctx.send_help()

    @checks.admin_or_permissions(administrator=True)
    @_reputation_settings.command(name="channel")
    async def set_rep_channel(self, ctx):
        """Set the reputations channel

        The reputation channel will be set to the channel in which this command is executed.
        If this channel is already the reputation channel, the config will be cleared."""
        channel = ctx.channel
        gld = ctx.guild
        if channel.id == await self.config.guild(gld).reputation_channel():
            await self.config.guild(gld).reputation_channel.clear()
            msg = self.REP_CHANNEL_SET_ALL
        else:
            await self.config.guild(gld).reputation_channel.set(channel.id)
            msg = self.REP_CHANNEL_SET.format(channel.mention)
        await ctx.send(msg)

    @commands.command()
    async def rep(self, ctx, who: discord.Member, *, why: str):
        """Give someone reputation"""
        # TODO: Add check to see whether someone does reputation in the right channel. Give a notice otherwise.
        # TODO: Possibly restrict length of rep message.
        aut = ctx.author
        gld = ctx.guild
        channel = ctx.channel
        cooldown_secs = await self.config.guild(ctx.guild).reputation_cooldown()
        if "@" in why:
            notice = self.REP_WHY_HAS_MENTION
        else:
            rep_channel = await self.config.guild(gld).reputation_channel()
            if rep_channel is None or rep_channel == channel.id:
                is_added = await self.rep_db.insert_rep(aut.id, str(aut), who.id, str(who), why, cooldown_secs)
                notice = self.REP_SUCCESS if is_added else self.REP_NOT_COOL
            else:
                notice = self.REP_BAD_CHANNEL
        await ctx.send(notice)

    # Utilities

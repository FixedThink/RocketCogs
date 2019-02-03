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

    DEFAULT_COOLDOWN = 60 * 60 * 24 * 7  # 1 week (cooldown for user A to give user B rep).
    REP_SUCCESS = ":white_check_mark: Rep added!"
    REP_NOT_COOL = ":x: Error: You have given that user a reputation too recently!"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.FOLDER = str(data_manager.cog_data_path(self))
        self.PATH_DB = self.FOLDER + "/reputation.db"
        self.config = Config.get_conf(self, identifier=5006)
        self.config.register_guild(reputation_channel=None, reputation_cooldown=self.DEFAULT_COOLDOWN)

        self.rep_db = DbQueries(self.PATH_DB)

    # Events

    # Commands
    @commands.command()
    async def rep(self, ctx, who: discord.Member, *, why: str):
        """Give someone reputation"""
        # TODO: Add check to see whether someone does reputation in the right channel. Give a notice otherwise.
        # TODO: Clean the rep message (why), to ensure no mentions are in it. Possibly restrict length.
        aut = ctx.author
        cooldown_secs = await self.config.guild(ctx.guild).reputation_cooldown()

        is_added = await self.rep_db.insert_rep(aut.id, str(aut), who.id, str(who), why, cooldown_secs)
        notice = self.REP_SUCCESS if is_added else self.REP_NOT_COOL
        await ctx.send(notice)

    # Utilities

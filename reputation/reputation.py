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
    REP_NOT_ADDED = ":x: Error: Reputation not added, please use the correct channel for reputations!"
    REP_CHANNEL_SET = ":white_check_mark: Rep channel set to "
    REP_CHANNEL_SET_ALL = ":white_check_mark: Rep channel removed. All channels now function as a rep channel."
    REP_WHY_MISSING = ":x: Error: Please include a reason to why this user deserves a rep."
    REP_WHY_HAS_MENTION = ":x: Error: Please do not tag any people in the rep reason! If you must mention someone, do not tag them, but mention them by name."
    
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
    @checks.admin_or_permissions(administrator=True)
    async def set_rep_channel(self, ctx, *all_toggle):
        """Set the reputations channel"""
        channel = ctx.channel
        gld = ctx.guild

        if len(all_toggle) == 1 and all_toggle[0] == "all":
            await self.config.guild(gld).reputation_channel.clear()
            msg = self.REP_CHANNEL_SET_ALL
        else:
            if channel.id == await self.config.guild(gld).reputation_channel():
                msg = self.REP_CHANNEL_SET_ALL
                await self.config.guild(gld).reputation_channel.clear()
            else:
                await self.config.guild(gld).reputation_channel_all.set(False)
                msg = self.REP_CHANNEL_SET + channel.mention
                await self.config.guild(gld).reputation_channel.set(channel.id)

        await ctx.send(msg)

    @commands.command()
    async def rep(self, ctx, who: discord.Member, *, why: str):
        """Give someone reputation"""
        # TODO: Add check to see whether someone does reputation in the right channel. Give a notice otherwise.
        # TODO: Clean the rep message (why), to ensure no mentions are in it. Possibly restrict length.
        aut = ctx.author
        gld = ctx.guild
        channel = ctx.channel
        cooldown_secs = await self.config.guild(ctx.guild).reputation_cooldown()
        if "@" not in why:
            if await self.config.guild(gld).reputation_channel() is None:
                is_added = await self.rep_db.insert_rep(aut.id, str(aut), who.id, str(who), why, cooldown_secs)
                notice = self.REP_SUCCESS if is_added else self.REP_NOT_COOL
            elif channel.id == await self.config.guild(gld).reputation_channel():
                is_added = await self.rep_db.insert_rep(aut.id, str(aut), who.id, str(who), why, cooldown_secs)
                notice = self.REP_SUCCESS if is_added else self.REP_NOT_COOL
            else:
                notice = self.REP_NOT_ADDED
        else:
            await ctx.send(self.REP_WHY_HAS_MENTION)

        await ctx.send(notice)

    # Utilities

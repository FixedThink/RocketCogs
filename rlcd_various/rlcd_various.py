# Default Library.
import asyncio
from typing import List

# Used by Red.
import discord
from redbot.core import commands
from redbot.core import checks, Config
from redbot.core.bot import Red


RLCD_GLD_ID = 317323644961554434


def is_in_rlcd():
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == RLCD_GLD_ID

    return commands.check(predicate)


class RlcdVarious(commands.Cog):
    """A collection of commands tailored to the needs of RLCD

    Some of these commands may be moved to a separate cog later on.
    """
    __author__ = "#s#8059"

    ERROR = ":x: Error: "
    DONE = ":white_check_mark: "
    BIN = ":put_litter_in_its_place: "
    # Notices.
    INHOUSES_CHANNEL_CLEARED = BIN + "Cleared the inhouses channel configuration." \
                                     "Effectively the lobby command functionality is disabled as well."
    INHOUSES_CHANNEL_SET = DONE + "Successfully set the inhouses channel to {c}."
    INHOUSES_NO_CHANNEL = ERROR + "The inhouses channel is not configured!"
    INHOUSES_WRONG_CHANNEL = ERROR + "This is not the channel for inhouses! Go to <#{}> instead."
    LTC_ROLE_CLEARED = BIN + "Successfully cleared the LTC role."
    LTC_ROLE_SET = DONE + "Successfully set the LTC role."
    NICKNAME_TOO_LONG = ERROR + "Your provided nickname is too long!\n" \
                                "To fit your nickname along with the region tag, it can be at most 27 characters."
    NICKNAME_NO_ROLE = ERROR + "You do not have any region roles! Please set one before applying for a nickname."
    NICKNAME_SET = DONE + "Nickname set."
    NICKNAME_PERMISSIONS = ERROR + "I cannot give you a nickname!"
    SUGGESTION_CHANNEL_SET = DONE + "Successfully set the suggestions channel to {c}."
    SUGGESTION_CHANNEL_CLEARED = BIN + "Cleared the suggestions channel configuration."
    # Other constants.
    LOBBY_EMBED_TITLE = "Inhouses invite by {}."
    LTC_SLEEP_TIME = 28 * 60  # 28 minutes.
    SUGGEST_EMOTES = "👍👎❌"
    REGION_ROLE_TAG = {"Africa": "AF", "Asia Central": "AS", "Europe": "EU", "North America": "NA",
                       "Middle East": "ME", "Oceania": "OC", "South America": "SA"}
    CONVERT_REGION = {"eu": "Europe", "europe": "Europe", "use": "US-East", "us-e": "US-East",
                      "nae": "US-East", "us-east": "US-East", "us east": "US-East", "usw": "US-West",
                      "us-w": "US-West", "naw": "US-West", "us-west": "US-West", "us wast": "US-West"}

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7509)
        self.config.register_guild(inhouses_channel_id=None, suggest_channel_id=None, ltc_role_id=None)
        self.ltc_loop = asyncio.ensure_future(self.check_ltc())

    # Loops
    async def check_ltc(self):
        """Remove the LTC role from whoever has the role and is offline"""
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog(self.__class__.__name__):
            gld: discord.Guild = self.bot.get_guild(RLCD_GLD_ID)
            ltc_id = await self.config.guild(gld).ltc_role_id()
            if ltc_id:  # Role ID is configured.
                role_obj: discord.Role = discord.utils.get(gld.roles, id=ltc_id)
                assert role_obj, "No role object!"
                # Get all members with the LTC role.
                ltc_members: List[discord.Member] = [m for m in gld.members if role_obj in m.roles]
                for member in ltc_members:
                    if member.status == discord.Status.offline:  # Only remove it when they're offline.
                        await member.remove_roles(role_obj)
            await asyncio.sleep(self.LTC_SLEEP_TIME)

    # Events
    async def on_message(self, msg: discord.Message):
        """Add suggestion reactions"""
        gld = msg.guild
        channel = msg.channel
        suggest_id = await self.config.guild(gld).suggest_channel_id()
        if suggest_id and channel.id == suggest_id:
            aut = msg.author
            perms = dict(aut.permissions_in(channel))
            if not (perms["manage_channels"] or perms["manage_messages"]):
                for emote in self.SUGGEST_EMOTES:
                    await msg.add_reaction(emote)

    # Config commands
    @commands.group(name="rlcdset", invoke_without_command=True)
    async def _rlcd_various_settings(self, ctx):
        """Configure the settings for this module."""
        await ctx.send_help()

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_rlcd_various_settings.command(name="inhouses_channel")
    async def set_inhouses_channel(self, ctx):
        """Set the inhouses channel to the current channel

        If the current channel is already the inhouses channel, the config gets cleared."""
        gld = ctx.guild
        channel = ctx.channel
        if channel.id == await self.config.guild(gld).inhouses_channel_id():
            await self.config.guild(gld).inhouses_channel_id.clear()
            to_send = self.SUGGESTION_CHANNEL_CLEARED
        else:
            await self.config.guild(gld).inhouses_channel_id.set(channel.id)
            to_send = self.SUGGESTION_CHANNEL_SET.format(c=channel.mention)
        await ctx.send(to_send)

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_rlcd_various_settings.command(name="suggestions_channel")
    async def set_suggestions_channel(self, ctx):
        """Set the suggestions channel to the current channel

        If the current channel is already the suggestions channel, the config gets cleared."""
        gld = ctx.guild
        channel = ctx.channel
        if channel.id == await self.config.guild(gld).suggest_channel_id():
            await self.config.guild(gld).suggest_channel_id.clear()
            to_send = self.INHOUSES_CHANNEL_CLEARED
        else:
            await self.config.guild(gld).suggest_channel_id.set(channel.id)
            to_send = self.INHOUSES_CHANNEL_SET.format(c=channel.mention)
        await ctx.send(to_send)

    @_rlcd_various_settings.command(name="ltc_role")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def set_ltc_role(self, ctx, role: discord.Role = None):
        """Set the role to perform the LTC check on

        If no role is provided, the currently set role will be deleted."""
        if not role:
            to_send = self.LTC_ROLE_CLEARED
            await self.config.guild(ctx.guild).ltc_role_id.clear()
        else:
            to_send = self.LTC_ROLE_SET
            await self.config.guild(ctx.guild).ltc_role_id.set(role.id)
        await ctx.send(to_send)

    # Main commands.
    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 60 * 10, type=commands.cooldowns.BucketType.channel)  # 1 message per 10 minutes.
    async def lobby(self, ctx, region: str, lobby_name: str, password: str, *, optional_text=None):
        """Create an invite message for an inhouses lobby

        This invite will ping `@here`. Note that there is a 10-minute cooldown on the command."""
        chn = ctx.channel
        inhouses_id = await self.config.guild(ctx.guild).inhouses_channel_id()
        if not inhouses_id or chn.id != inhouses_id:
            await ctx.send(self.INHOUSES_NO_CHANNEL if not inhouses_id
                           else self.INHOUSES_WRONG_CHANNEL.format(inhouses_id))
        else:
            region_str = self.CONVERT_REGION.get(region.lower(), region)
            embed = discord.Embed(colour=discord.Colour.purple(), description=optional_text)
            embed.title = "Inhouses invite by {}".format(str(ctx.author))
            embed.add_field(name="Region", value=region_str)
            embed.add_field(name="Lobby name", value=lobby_name)
            embed.add_field(name="Password", value=password)
            await ctx.send("New inhouses invite. @here", embed=embed, filter=None)

    @is_in_rlcd()
    @commands.command(name="nickname", aliases=["nick"])
    async def user_set_nickname(self, ctx, *, nickname: str):
        """Set your own nickname

        Your nickname will be automatically prefixed with your region, like [EU]."""
        user = ctx.author
        region_tag = next((self.REGION_ROLE_TAG[r.name] for r in user.roles if r.name in self.REGION_ROLE_TAG), None)
        if not region_tag:
            to_say = self.NICKNAME_NO_ROLE
        elif len(nickname) > 27:
            to_say = self.NICKNAME_TOO_LONG
        else:
            to_set = f"[{region_tag}] {nickname}"
            try:
                await user.edit(nick=to_set, reason="RLCD nickname command.")
            except discord.Forbidden:
                to_say = self.NICKNAME_PERMISSIONS
            else:
                to_say = self.NICKNAME_SET
        await ctx.send(to_say)

    # Utilities

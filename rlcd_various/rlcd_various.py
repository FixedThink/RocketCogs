# Default Library.
import asyncio
from textwrap import shorten
from typing import List, Optional

# Used by Red.
import discord
from redbot.core import checks, Config
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

RLCD_GLD_ID = 317323644961554434


def is_in_rlcd():
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == RLCD_GLD_ID

    return commands.check(predicate)


class RlcdVarious(Cog):
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
    LTC_ROLE_U_DEL = BIN + "Removed your LTC role."
    LTC_NOT_ONLINE = ERROR + "You are not online (green bulb)!\nPlease set yourself to online first."
    LTC_NOT_SET = ERROR + "No LTC role is configured! Please contact an admin."
    NICKNAME_TOO_LONG = ERROR + "Your provided nickname is too long!\n" \
                                "To fit your nickname along with the region tag, it can be at most 27 characters."
    NO_REGION_ROLE = ERROR + "You do not have a region role! Please set one first."
    NICKNAME_SET = DONE + "Nickname set."
    NICKNAME_PERMISSIONS = ERROR + "I cannot give you a nickname!"
    SUGGESTION_CHANNEL_SET = DONE + "Successfully set the suggestions channel to {c}."
    SUGGESTION_CHANNEL_CLEARED = BIN + "Cleared the suggestions channel configuration."
    TWITCH_ROLES_CLEARED = BIN + "Successfully cleared the Twitch roles configuration."
    TWITCH_NO_SUB = ERROR + "You are not subscribed to the Twitch channel!"
    TWITCH_NOT_CONFIGURED = ERROR + "The Twitch roles are not configured!"

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
        # TODO: Make role toggles for inhouses and meme (low-priority).
        self.config.register_guild(inhouses_channel_id=None, suggest_channel_id=None,
                                   ltc_role_id=None, twitch_role_id=None, hoist_twitch_id=None)
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
    @Cog.listener()
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

    @Cog.listener()
    async def on_member_update(self, m_old: discord.Member, m_new: discord.Member):
        """Give a member a nickname if they set a region, and do the Twitch sub check"""
        gld = m_new.guild
        twitch_role_id = await self.config.guild(gld).twitch_role_id()
        added_role: Optional[discord.Role] = next((r for r in m_new.roles if r not in m_old.roles), None)
        if added_role:
            region_tag = self.REGION_ROLE_TAG.get(added_role.name, None)
            if region_tag:  # Region role added, give nickname.
                # Create the nickname to set. Shorten to 32 if it would exceed 32 chars.
                to_set = shorten(f"[{region_tag}] {m_new.name}", 32, placeholder="...")
                try:
                    await m_new.edit(nick=to_set, reason="RLCD region addition.")
                except discord.Forbidden:
                    pass
            else:
                if twitch_role_id and added_role.id == twitch_role_id:
                    hoist_twitch_id = await self.config.guild(gld).hoist_twitch_id()
                    hoist_role = discord.utils.get(gld.roles, id=hoist_twitch_id)
                    assert hoist_role, "Somehow, the twitch role is configured, but not the hoist role."
                    await m_new.add_roles(hoist_role, reason="Received the Twitch sub role.")
        elif twitch_role_id:  # Check role removals.
            removed_role: Optional[discord.Role] = next((r for r in m_old.roles if r not in m_new.roles), None)
            if removed_role.id == twitch_role_id:
                hoist_twitch_id = await self.config.guild(gld).hoist_twitch_id()
                hoist_role = discord.utils.get(gld.roles, id=hoist_twitch_id)
                assert hoist_role, "Somehow, the twitch role is configured, but not the hoist role."
                if hoist_role in m_new.roles:
                    await m_new.remove_roles(hoist_role, reason="Twitch sub ended.")

    # Config commands
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @commands.group(name="rlcdset", invoke_without_command=True)
    async def _rlcd_various_settings(self, ctx: commands.Context):
        """Configure the settings for this module."""
        await ctx.send_help()

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @_rlcd_various_settings.command(name="inhouses_channel")
    async def set_inhouses_channel(self, ctx: commands.Context):
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
    async def set_suggestions_channel(self, ctx: commands.Context):
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
    async def set_ltc_role(self, ctx: commands.Context, role: discord.Role = None):
        """Set the role to perform the LTC check on

        If no role is provided, the currently set role will be deleted."""
        if not role:
            await self.config.guild(ctx.guild).ltc_role_id.clear()
            await ctx.send(self.LTC_ROLE_CLEARED)
        else:
            await self.config.guild(ctx.guild).ltc_role_id.set(role.id)
            await ctx.tick()

    @_rlcd_various_settings.command(name="twitch")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def set_twitch_roles(self, ctx: commands.Context, role_1: discord.Role, role_2: discord.Role):
        """Set the pair of Twitch roles

        The first role must be the integration role, the second one the role to be added.
        Config can be cleared by using the same role for both arguments"""
        gld = ctx.guild
        if role_1 == role_2:
            # twitch_role_id=None, hoist_twitch_id=None)
            await self.config.guild(gld).twitch_role_id.clear()
            await self.config.guild(gld).hoist_twitch_id.clear()
            await ctx.send(self.TWITCH_ROLES_CLEARED)
        else:
            await self.config.guild(ctx.guild).twitch_role_id.set(role_1.id)
            await self.config.guild(ctx.guild).hoist_twitch_id.set(role_2.id)
            await ctx.tick()

    # Main commands.
    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 60 * 10, type=commands.cooldowns.BucketType.channel)  # 1 message per 10 minutes.
    async def lobby(self, ctx: commands.Context, region: str, lobby_name: str, password: str, *, optional_text=None):
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
    @commands.guild_only()
    @commands.command(name="ltc")
    async def looking_to_coach(self, ctx: commands.Context):
        """Give yourself the Looking to Coach role

        You must have set a region and you must be in online status.
        If you already have the role, this command will remove it."""
        notice = None
        user = ctx.author
        gld = ctx.guild
        ltc_id = await self.config.guild(gld).ltc_role_id()

        if ltc_id:  # Role ID is configured.
            role_obj: discord.Role = discord.utils.get(gld.roles, id=ltc_id)
            assert role_obj, "No role object!"
            if role_obj in user.roles:
                await user.remove_roles(role_obj)
                notice = self.LTC_ROLE_U_DEL
            elif any(self.REGION_ROLE_TAG.get(r.name, False) for r in user.roles):
                if user.status == discord.Status.online:
                    await user.add_roles(role_obj)
                    await ctx.tick()
                else:
                    notice = self.LTC_NOT_ONLINE
            else:
                notice = self.NO_REGION_ROLE
        else:
            notice = self.LTC_NOT_SET
        if notice:
            await ctx.send(notice)

    @is_in_rlcd()
    @commands.guild_only()
    @commands.command(name="nickname", aliases=["nick"])
    async def user_set_nickname(self, ctx: commands.Context, *, nickname: str):
        """Set your own nickname

        Your nickname will be automatically prefixed with your region, like [EU]."""
        user = ctx.author
        region_tag = next((self.REGION_ROLE_TAG[r.name] for r in user.roles if r.name in self.REGION_ROLE_TAG), None)
        if not region_tag:
            to_say = self.NO_REGION_ROLE
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

    @is_in_rlcd()
    @commands.guild_only()
    @commands.command(name="toggle_twitch")
    async def toggle_twitch_role(self, ctx: commands.Context):
        """Remove the hoisted twitch role if you have it, otherwise add it

        Obviously, you must be subscribed to Twitch in order to do this."""
        gld = ctx.guild
        t_id = await self.config.guild(gld).twitch_role_id()
        h_id = await self.config.guild(gld).hoist_twitch_id()
        if t_id and h_id:
            t_role = discord.utils.get(gld.roles, id=t_id)
            h_role = discord.utils.get(gld.roles, id=h_id)
            assert t_role and h_role, "Twitch roles do not exist!"
            aut: discord.Member = ctx.author
            if t_role in aut.roles:  # Toggle.
                if h_role in aut.roles:
                    await aut.remove_roles(h_role, reason="Twitch toggle command")
                else:
                    await aut.add_roles(h_role, reason="Twitch toggle command")
                await ctx.tick()
                notice = None
            else:
                notice = self.TWITCH_NO_SUB
        else:
            notice = self.TWITCH_NOT_CONFIGURED
        if notice:
            await ctx.send(notice)

    # Utilities

# RocketCogs

This repository is for Rocket-League related cogs for [RedBot V3](https://github.com/Twentysix26/Red-DiscordBot), 
which is a bot using the latest version of discord.py.


# About the cogs

## LaFusee

La Fusée (French for "The Rocket") is the project name for the cog that contains various commands related to Rocket League user stats. 
The cog's core functions are similar to RankCog and SetProfile cogs (both on V2 of RedBot), used on the 
Rocket League Coaching Discord. However, it is rewritten from scratch, and unified in order to make additional features possible.

This cog allows users to check their ranks (or those of others), by either specifying someone's platform and ID. 
Additionally, users can register their gamer ID (Steam, PlayStation 4, or Xbox), and use that to get their Rocket League stats.

#### Stat checking
Various ways of displaying one's stats are planned. As the cog is currently in development, only one of them is ready thus far.

- **lfg** - This command displays a player's current rank (tier, division, and rating) in each playlist using a 
compact embed. This embed is split in two views; one view for the "normal" playlists, and one for the 
"special" playlists such as Rumble. A user can switch between these two views by reactions added beneath the embed.

Other planned commands include:

- **stats [playlist]** - if no playlist is provided, display someone's ranking performance, as well as general online 
stats (goals, assists, etc). If a playlist is provided, it displays more specific stats of the player in that playlist, 
such as their amount of matches played.

- *more to follow*


#### Rank roles
In addition to the account registration, this cog has a built-in rank role feature. 
This feature allows a guild to automatically assign a rank role to its members when they register their account. 
For this, the guild staff can either manually create the roles, and make the bot automatically detect them, 
or let the bot make the roles needed for them. The rank role functionality is optional, and is turned off by default.

## Reputation
Reputation allows users to give recommendations about other users in the form of a reputation. 
Although this cog is made to facilitate coach reputation on the Rocket League Coaching Discord 
(where the reputation is obviously for one's coaching), 
the cog was made as versatile as possible so that it can be used in other circumstances as well.

Configuration options include:

- **Reputation role** - When a user receives a certain amount of reputation (configurable!), they become eligible for a
reputation role. The role is optional, and if not provided no role will be given.
- **Reputation role threshold** - Allows you so set the threshold for the role.
- **Cooldown** - By default, one user can give another user reputation more than once. 
However, this is restricted by a cooldown: by default there must be at least 1 week between to consequent reputations to the same user.
As of now this cannot be configured to be forbidden (yet), but this is planned before the stable release.
Until then, the cooldown can be set sufficiently high (e.g. 10000 days), which will effectively give the same result.
- **Role decay** After a set period, a user may use their reputation role if they haven't received enough reputation
in that period. This period is configurable, as well as the amount of reputations needed in that period (see below).
- **Decay threshold** If role decay is enabled (and the role is enabled in the first place),
this configuration option determines the reputation threshold needed in the decay period.

 

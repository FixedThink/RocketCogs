# RocketCogs

This repository is for Rocket-League related cogs for [RedBot V3](https://github.com/Twentysix26/Red-DiscordBot), 
which is a bot using the latest version of discord.py.


# About the cogs

## LaFusee

La Fusée (French for *The Rocket*) is the project name for the cog that contains various commands related to Rocket League user stats. 
The cog is based on two RedBot V2 modules used on the [Rocket League Coaching Discord](https://www.rlcd.gg/) (RankCog and SetProfile). 
However, it is rewritten from scratch, and unified in order to make additional features possible.

This cog allows users to check their ranks (or those of others), by specifying someone's platform and ID. 
Additionally, users can register their gamer ID (Steam, PlayStation 4, or Xbox), and use that to get their Rocket League stats.

#### Stat checking

- **lfg** – This command displays a player's current rank (tier, division, and rating) in each playlist using a 
compact embed. This embed is split in two views; one view for the "normal" playlists, and one for the 
"special" playlists such as Rumble. A user can switch between these two views by reactions added beneath the embed.

- **stats** – Displays someone's ranking performance, as well as general online stats (goals, assists, etc). 
Also shows someone's progress for Season Rewards.

- **lstats** or **list** – Displays more specific stats of a player in a provided playlist.
These stats include the amount of matches played, values that are not shown by any other trackers (mu, sigma), and more.

Each of these commands have a subcommand **user** (alias **me**) that, instead of platform and ID input, 
allows a user to show stats via a user mention (given that the user has linked their account). 
If no user is mentioned, this will default to the stats of the message author. 


#### Rank roles
In addition to the account registration, this cog has a built-in rank role feature. The feature is optional and turned off by default.
The rank role functionality allows a guild to automatically assign a rank role to its members when they register their account. 
To set this up, the guild staff can either manually create the roles and make the bot automatically detect them, 
or let the bot make the roles needed for them.

It is also possible to ignore special playlists (e.g. rumble) when determining the highest role, but this is turned off by default.


## Reputation
Reputation allows users to give recommendations about other users in the form of a reputation. 
Although this cog is made to facilitate coach reputation on the Rocket League Coaching Discord 
(where the reputation is obviously for one's coaching), 
the cog was made as versatile as possible so that it can be used in other circumstances as well.

Configuration options include:

- **Reputation role** – When a user receives a certain amount of reputation (configurable!), they become eligible for a
reputation role. The role is optional, and if not provided no role will be given.
- **Reputation role threshold** – Allows the threshold for the role to be set.
- **Cooldown** – By default, one user can give another user reputation more than once. 
However, this is restricted by a cooldown: by default there must be at least 1 week between to consequent reputations to the same user.
As of now this cannot be configured to be forbidden (yet), but this is planned before the stable release.
Until then, the cooldown can be set sufficiently high (e.g. 10000 days), which will effectively give the same result.
- **Role decay** – After a set period, a user may lose their reputation role if they haven't received enough reputation
in that period. This period is configurable, as well as the amount of reputations needed in that period (see below).
- **Decay threshold** – If role decay is enabled (and the role is enabled in the first place),
this configuration option determines the reputation threshold needed in the decay period.
- **Role abstention** – Some users may not want to get a role for their reputation for example to not be prominent.
For that reason, users will be able to opt-out from receiving a role, while still be able to receive and give reputation.

 

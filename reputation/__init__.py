from .reputation import Reputation


def setup(bot):
    bot.add_cog(Reputation(bot))

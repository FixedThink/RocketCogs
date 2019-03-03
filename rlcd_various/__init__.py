from .rlcd_various import RlcdVarious


def setup(bot):
    bot.add_cog(RlcdVarious(bot))

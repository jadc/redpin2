import discord
from discord.ext import commands

from helper import Helper

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config
        self.helper = Helper(bot)
        print('Events init')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        #print(payload)

        # Ignore reaction events that bots trigger
        if payload.member.bot:
            return

        channel = self.bot.get_channel(payload.channel_id)
        guild = channel.guild
        cfg = self.config.get(guild.id)

        # NSFW check
        if not cfg['nsfw'] and channel.is_nsfw():
            print('nsfw channel, skipping')
            return

        pin_channel_id = self.config.get(guild.id)['channel']

        # Prevent pinning in pin channel
        if payload.channel_id == pin_channel_id:
            return

        pin_channel = self.bot.get_channel(pin_channel_id)

        msg = await channel.fetch_message(payload.message_id)

        # Never pin messages by bot
        if msg.author.id == self.bot.user.id:
            return

        # Ignore messages that are already pinned
        if any(x.me for x in msg.reactions):
            return

        # If any reaction fulfill count
        for reaction in msg.reactions:
            count = reaction.count

            # If emoji filters on, check it
            filt = cfg['filter']
            if len(filt['unicode']) > 0 or len(filt['custom']) > 0:
                if hasattr(reaction.emoji, 'id'):
                    if reaction.emoji.id not in filt['custom']:
                        continue
                else:
                    # unicode emojis have no id, emoji is a str
                    if reaction.emoji not in filt['unicode']:
                        continue

            # self pinning
            if not cfg['selfpin']:
                for user in [user async for user in reaction.users()]:
                    if user.id == msg.author.id:
                        count -= 1

            if count >= self.config.get(guild.id)['count']:
                await self.helper.pin_message(msg, pin_channel) 
                await msg.add_reaction(reaction)  # Marked as pinned
                return

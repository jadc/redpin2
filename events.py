import discord
from discord.ext import commands
from discord.ui import View, Button

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config
        print('Events init')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        #print('---')
        #print(payload)

        # Ignore DMs
        if payload.guild_id is None:
            print('Reaction in DMs, ignored.')
            return

        # Ignore reaction events that bots trigger
        if payload.member.bot:
            print('Reaction from bot, ignored.')
            return

        channel = self.bot.get_channel(payload.channel_id)
        guild = channel.guild

        cfg = self.config.get(guild.id)

        if cfg['channel'] is None:
            print('Reaction from guild with no pin channel, ignored.')
            return

        # NSFW check
        if not cfg['nsfw'] and channel.is_nsfw():
            print('Reaction in NSFW channel, ignored.')
            return

        pin_channel_id = self.config.get(guild.id)['channel']

        # Prevent pinning in pin channel
        if payload.channel_id == pin_channel_id:
            print('Reaction in pin channel, ignored.')
            return

        pin_channel = self.bot.get_channel(pin_channel_id)

        msg = await channel.fetch_message(payload.message_id)

        # Cannot pin messages with stickers
        if len(msg.stickers) > 0:
            print('Reaction on sticker, ignored.')
            return

        # Never pin messages by bot
        if msg.author.id == self.bot.user.id:
            print('Reaction created by a bot, ignored.')
            return

        # If any reaction fulfill count
        for reaction in msg.reactions:
            # Ignore messages that are already pinned
            if any(x.me for x in msg.reactions):
                print('Message already pinned, ignored.')
                return

            count = reaction.count

            # If emoji filters on, check it
            filt = cfg['filter']
            if len(filt['unicode']) > 0 or len(filt['custom']) > 0:
                if hasattr(reaction.emoji, 'id'):
                    if reaction.emoji.id not in filt['custom']:
                        print('Reaction not in custom filter, ignored.')
                        return
                else:
                    # unicode emojis have no id, emoji is a str
                    if reaction.emoji not in filt['unicode']:
                        print('Reaction not in unicode filter, ignored.')
                        return

            # self pinning
            if not cfg['selfpin']:
                for user in [user async for user in reaction.users()]:
                    if user.id == msg.author.id:
                        print('Selfpin subtracted from total')
                        count -= 1

            print('Reaction count:', count)
            if count >= self.config.get(guild.id)['count']:
                await msg.add_reaction(reaction)  # Marked as pinned
                print('Marked a message as pinned.')
                pinned_msg = await self.pin_message(msg, pin_channel) 
                print('Pinned a message.')
                await self.clone_reactions(msg, pinned_msg)
                print('Cloned all reactions')
                return

    async def get_webhook(self, pin_channel):
        for hook in await pin_channel.webhooks():
            if hook.user.id == self.bot.user.id:
                return hook

        # if no webhook, create one
        return await pin_channel.create_webhook(name = 'redpin', reason = 'redpin functionality')

    async def pin_message(self, message, pin_channel):
        hook = await self.get_webhook(pin_channel)

        # Convert all attachments that can fit into files, and reupload them
        files = [ await x.to_file( use_cached=True, spoiler=x.is_spoiler() ) for x in message.attachments if x.size < hook.guild.filesize_limit ]

        # If attachment is greater than bot is allowed, append link instead
        attachments = [ x for x in message.attachments if x.size >= hook.guild.filesize_limit ]
        content_w_files = message.content
        for att in attachments:
            if att.is_spoiler():
                content_w_files += f'\n|| {att.url} ||'
            else:
                content_w_files += f'\n{att.url}'

        return await hook.send(
            wait = True,
            content = content_w_files,
            username = message.author.display_name,
            avatar_url = message.author.display_avatar.url,
            allowed_mentions = discord.AllowedMentions.none(),
            files = files,

            # jump to msg button
            view = View().add_item( Button(label="Jump", url=message.jump_url) )
        )

    async def clone_reactions(self, source, target):
        for reaction in source.reactions:
            try:
                await target.add_reaction(reaction)
            except discord.errors.HTTPException:
                print('Attempted to react with an unknown emoji. Skipping...')

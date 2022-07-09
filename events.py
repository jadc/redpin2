import discord
from discord.ext import commands
from discord.ui import View, Button

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config
        self.pinning = set()
        print('Events init')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        #print('---')
        #print(payload)

        # Message is being pinned
        if payload.message_id in self.pinning:
            print('Message is in queue to be pinned, ignoring reactions.')
            return

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

        pin_channel_id = cfg['channel']

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

        # Ignore messages that are already pinned
        if any(x.me for x in msg.reactions):
            print('Message already pinned, ignored.')
            return

        # Filters
        pin_reactions = [x for x in msg.reactions if await self.get_real_count(x) >= cfg['count'] and self.is_emoji_allowed(x)]

        if pin_reactions:
            # Does not matter which reaction is selected
            reaction = pin_reactions[0]

            # This 'queue' system prevents the same message
            # being posted multiple times when reactions come in
            # quickly. add_reaction is not instant, the queue is.
            self.pinning.add(payload.message_id)

            await msg.add_reaction(reaction)  # Marked as pinned
            print('Marked a message as pinned.')
            pinned_msg = await self.pin_message(msg, pin_channel) 
            print('Pinned a message.')
            await self.clone_reactions(msg, pinned_msg)
            print('Cloned all reactions')

            self.pinning.discard(payload.message_id)

    # Filtering process
    def is_emoji_allowed(self, reaction):
        allow = self.config.get(reaction.message.guild.id)['filter']
        return len(allow) <= 0 or str(reaction) in allow

    async def get_real_count(self, reaction):
        if self.config.get(reaction.message.guild.id)['selfpin']:
            return reaction.count
        else:
            reactions_by_author = [user async for user in reaction.users() if user.id == reaction.message.author.id]
            return reaction.count - len(reactions_by_author)


    # Pinning process
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

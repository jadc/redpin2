import discord
from discord.ext import commands
from discord.ui import View, Button

class Helper():
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print('Helper init')

    async def get_webhook(self, pin_channel):
        for hook in await pin_channel.webhooks():
            if hook.user.id == self.bot.user.id:
                return hook

        # if no webhook, create one
        return await pin_channel.create_webhook(name = 'redpin', reason = 'redpin functionality')

    async def pin_message(self, message, pin_channel):
        hook = await self.get_webhook(pin_channel)

        # convert all attachments to urls, append to message content
        content_w_files = message.content
        for att in message.attachments:
            content_w_files += '\n' + att.url

        await hook.send(
            content = content_w_files,
            username = message.author.display_name,
            avatar_url = message.author.display_avatar.url,
            allowed_mentions = discord.AllowedMentions.none(),

            # jump to msg button
            view = View().add_item( Button(label="Jump", url=message.jump_url) )
        )

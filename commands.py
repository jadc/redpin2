import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from config import Config

@app_commands.default_permissions(administrator=True)
class Commands(commands.GroupCog, name='redpin'):
    def __init__(self, bot: commands.Bot, config) -> None:
        self.bot = bot
        self.config = config
        super().__init__()
        print('Commands init')

    @app_commands.command(name = 'channel', description = 'Set which channel to send pins to.')
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # if channel was set before
        if self.config.get(interaction.guild_id)['channel'] is not None:
            # remove webhook from old channel
            old_channel = interaction.guild.get_channel( self.config.get(interaction.guild_id)['channel'] )
            if old_channel is not None:
                for hook in await old_channel.webhooks():
                    if hook.user.id == self.bot.user.id:
                        await hook.delete(reason = 'Pin channel changed, webhook automatically removed')

        # update config
        self.config.get(interaction.guild_id)['channel'] = channel.id
        self.config.save()

        # response
        await interaction.response.send_message(f'Pins will now be sent in <#{channel.id}>.', ephemeral = True)

    @app_commands.command(name = 'count', description = 'Set the number of reactions to pin a message.')
    async def count(self, interaction: discord.Interaction, count: int):

        # No negative or zero reaction count
        if count < 1:
            count = 1

        # update config
        self.config.get(interaction.guild_id)['count'] = count
        self.config.save()

        plural = 's'
        if count == 1: plural = ''

        # response
        await interaction.response.send_message(f'Pins will now require **{count} reaction{plural}**.', ephemeral = True)

    @app_commands.command(name = 'nsfw', description = 'Toggle whether messages from NSFW channels can be pinned.')
    async def nsfw(self, interaction: discord.Interaction):
        # update config
        self.config.get(interaction.guild_id)['nsfw'] = not self.config.get(interaction.guild_id)['nsfw']
        self.config.save()

        # response
        if self.config.get(interaction.guild_id)['nsfw']:
            await interaction.response.send_message(f'Messages from NSFW channels can now be pinned.', ephemeral = True)
        else:
            await interaction.response.send_message(f'Messages from NSFW channels can no longer be pinned.', ephemeral = True)

    @app_commands.command(name = 'selfpin', description = 'Toggle whether messages can be pinned by their author.')
    async def selfpin(self, interaction: discord.Interaction):
        # update config
        self.config.get(interaction.guild_id)['selfpin'] = not self.config.get(interaction.guild_id)['selfpin']
        self.config.save()

        # response
        if self.config.get(interaction.guild_id)['selfpin']:
            await interaction.response.send_message(f'Messages can now be pinned by their author.', ephemeral = True)
        else:
            await interaction.response.send_message(f'Messages can no longer be pinned by their author.', ephemeral = True)

    # EMOJI COMMAND
    @app_commands.command(name = 'filter', description = 'Customize which emojis can pin messages. Run this command in a private channel!')
    async def filter(self, interaction: discord.Interaction):
        view = EmojiPrompt()

        await interaction.response.send_message('**Customize which emojis can pin messages.**\nReact to this message with the emojis you want to be able to pin messages with.\nSubmit with no reactions to allow any emoji to pin messages.', view=view)
        await view.wait()

        if view.value:
            prompt = await interaction.original_message()
            self.config.get(interaction.guild_id)['filter'] = [str(x) for x in prompt.reactions]
            self.config.save()
            await interaction.delete_original_message()

class EmojiPrompt(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Saved changes.', ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Cancelled. Nothing was changed.', ephemeral=True)
        self.value = False
        self.stop()

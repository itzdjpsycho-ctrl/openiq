"""Optional Discord transport. Not started by demo setup or web server."""
import json,os
import discord
from discord import app_commands
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.models import User
from guilds.models import Guild,Access
from guilds.modules.commands import COMMANDS
from guilds.discord_auth import role_for
from guilds.services import execute

class Command(BaseCommand):
    help='Connect the optional Discord bot. Requires credentials and explicit delivery enablement.'
    def add_arguments(self,parser):
        sync=parser.add_mutually_exclusive_group();sync.add_argument('--sync',action='store_true');sync.add_argument('--sync-guild',type=int)
        parser.add_argument('--check',action='store_true')
    def handle(self,*args,**options):
        sync_global=options['sync'] or os.getenv('DISCORD_SYNC_GLOBAL')=='1'
        sync_guild=options['sync_guild'];configured_guild=os.getenv('DISCORD_SYNC_GUILD','').strip()
        if sync_guild is None and configured_guild:
            try:sync_guild=int(configured_guild)
            except ValueError:raise CommandError('DISCORD_SYNC_GUILD must be a positive numeric Discord server ID.')
        if sync_guild is not None and sync_guild<=0:raise CommandError('Discord sync guild ID must be positive.')
        if sync_global and sync_guild is not None:raise CommandError('Choose global sync or guild sync, not both.')
        intents=discord.Intents.default()
        output=self.stdout
        class Bot(discord.Client):
            def __init__(self):super().__init__(intents=intents);self.tree=app_commands.CommandTree(self)
            async def setup_hook(self):
                if not sync_global and sync_guild is None:return
                scope=f'server {sync_guild}' if sync_guild is not None else 'global'
                try:
                    if sync_guild is not None:
                        target=discord.Object(id=sync_guild);self.tree.copy_global_to(guild=target);registered=await self.tree.sync(guild=target)
                    else:
                        registered=await self.tree.sync()
                except discord.HTTPException as exc:
                    raise CommandError(f'Discord command sync failed ({scope}, HTTP {exc.status}). Check application installation and permissions.') from exc
                output.write(f'Synced {len(registered)} top-level commands ({scope}).')
        bot=Bot();groups={}
        def make_callback(command):
            async def callback(interaction:discord.Interaction,arguments:str='{}',guild_name:str=''):
                if interaction.guild is None:await interaction.response.send_message('Use this command in a server.',ephemeral=True);return
                await interaction.response.defer(ephemeral=True)
                @sync_to_async
                def run():
                    candidates=Guild.objects.filter(server_id=str(interaction.guild_id))
                    if guild_name:candidates=candidates.filter(name__iexact=guild_name)
                    if candidates.count()!=1:raise ValueError('Specify guild_name to select a configured BDO guild.')
                    g=candidates.get();user,created=User.objects.get_or_create(username='discord_'+str(interaction.user.id))
                    if created:user.set_unusable_password();user.save()
                    tier=role_for(g,{'owner':interaction.guild.owner_id==interaction.user.id,'permissions':str(interaction.user.guild_permissions.value)},[r.id for r in interaction.user.roles])
                    if not tier:
                        Access.objects.filter(guild=g,user=user).delete();raise ValueError('Your Discord roles do not grant access.')
                    Access.objects.update_or_create(guild=g,user=user,defaults={'role':tier})
                    channel=g.config.get('channels',{}).get('gear' if command in ['gear','gearupdate','gearlist','gearping','deletegear'] else 'bot')
                    if channel and str(channel)!=str(interaction.channel_id):raise ValueError('Use the configured command channel.')
                    return execute(user,g.pk,'commands','run',{'command':command,'arguments':json.loads(arguments)})
                try:result=await run();content=json.dumps(result,indent=2,ensure_ascii=False)
                except Exception as exc:content=str(exc)
                await interaction.followup.send(content[:1900],ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
            return callback
        @bot.event
        async def on_interaction(interaction):
            custom_id=(interaction.data or {}).get('custom_id','')
            if not custom_id.startswith(('signup:','welcome:')):return
            await interaction.response.defer(ephemeral=True)
            @sync_to_async
            def apply_component():
                from guilds.discord_components import process
                user=User.objects.get(username='discord_'+str(interaction.user.id))
                gid=custom_id.split(':')[1];g=Guild.objects.get(pk=gid)
                if g.server_id!=str(interaction.guild_id):raise ValueError('Wrong server')
                tier=role_for(g,{'owner':interaction.guild.owner_id==interaction.user.id,'permissions':str(interaction.user.guild_permissions.value)},[r.id for r in interaction.user.roles])
                if not tier:Access.objects.filter(guild=g,user=user).delete();raise ValueError('No guild access')
                Access.objects.update_or_create(guild=g,user=user,defaults={'role':tier})
                process(user,custom_id,deliver_roles=True)
            try:await apply_component();text='Welcome role updated.' if custom_id.startswith('welcome:') else 'Signup updated.'
            except Exception as exc:text=str(exc)
            await interaction.followup.send(text[:1900],ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
        for name in COMMANDS:
            pieces=name.split(' ',1)
            if len(pieces)==2:
                if pieces[0] not in groups:
                    groups[pieces[0]]=app_commands.Group(name=pieces[0],description='OpenIQ '+pieces[0]);bot.tree.add_command(groups[pieces[0]])
                groups[pieces[0]].add_command(app_commands.Command(name=pieces[1],description='Run '+name,callback=make_callback(name)))
            else:bot.tree.add_command(app_commands.Command(name=name,description='Run '+name,callback=make_callback(name)))
        if options['check']:
            self.stdout.write(f'{len(COMMANDS)} commands built locally; no Discord connection.');return
        token=os.getenv('DISCORD_BOT_TOKEN')
        if not token or os.getenv('ENABLE_DISCORD_DELIVERY')!='1':raise CommandError('Set DISCORD_BOT_TOKEN and ENABLE_DISCORD_DELIVERY=1 to connect. Nothing was sent.')
        bot.run(token)

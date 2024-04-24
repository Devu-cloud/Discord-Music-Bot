import asyncio
import discord
from discord.ext import commands, tasks
import youtube_dl
from collections import deque

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since IPv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    def __str__(self):
        return self.title

    @classmethod
    async def create_source(cls, ctx, search_term, loop=None, download=False):
        loop = loop or asyncio.get_event_loop()
        data = await cls.extract_info(ctx, search_term, loop, download)

        if data.get('entries'):
            # for playlists
            sources = [cls(discord.FFmpegPCMAudio(entry['url'], **ctx.cog.ffmpeg_options), data=entry) for entry in data['entries']]
            return sources
        else:
            source = discord.FFmpegPCMAudio(data.get('url'), **ctx.cog.ffmpeg_options)
            return cls(source, data=data)

    @staticmethod
    async def extract_info(ctx, search_term, loop, download):
        with youtube_dl.YoutubeDL(ctx.cog.ytdl_format_options) as ydl:
            try:
                if search_term.startswith(("http", "www")):
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_term, download=download))
                else:
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch:{search_term}", download=download))
                info = info.get('entries', [])[0]
            except Exception as e:
                raise Exception(f"An error occurred while searching: {e}")
            return info

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.current_song = None
        self.playing_song = None
        self.queue = deque()
        self.ytdl_format_options = ytdl_format_options
        self.ffmpeg_options = ffmpeg_options
        self.idle_since = None
        self.idle_timeout.start()

    @tasks.loop(minutes=15)
    async def idle_timeout(self):
        if self.voice_client and not self.voice_client.is_playing():
            await self.voice_client.disconnect()
            try:
                await self.voice_client.guild.text_channels[0].send(embed=discord.Embed(
                    title="Goodbye!",
                    description="Bot has been disconnected due to inactivity.",
                    color=discord.Color.red()
                ))
            except:
                pass
            self.voice_client = None
            self.queue.clear()
            self.current_song = None
    
    async def check_queue(self, ctx, error=None):
        if error:
            print(f"Error occurred during playback: {error}")
            try:
                await ctx.send(f"Error occurred during playback: {error}")
            except:
                pass

        if self.queue:
            self.current_song = self.queue.popleft()
            self.voice_client = ctx.voice_client
            self.voice_client.play(self.current_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.check_queue(ctx, e), self.bot.loop))
            await ctx.send(f"Now playing: **{self.current_song.title}**")
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.current_song.title))
            self.idle_since = None
        else:
            self.current_song = None
            self.voice_client.stop()
            await self.bot.change_presence(activity=None)
            self.idle_since = ctx.message.created_at
    
    
    @commands.command()
    async def join(self, ctx):
            if ctx.author.voice is None:
                await ctx.send("You're not connected to a voice channel.")
                return

            voice_channel = ctx.author.voice.channel

            if self.voice_client and self.voice_client.channel == voice_channel:
                await ctx.send(embed=discord.Embed(
                    description=f"Already joined in {voice_channel.mention}.",
                    color=discord.Color.blue()
                ))
                return

            if self.voice_client and self.voice_client.channel != voice_channel:
                if not self.voice_client.is_playing() and len(self.voice_client.channel.members) == 1:
                    await self.voice_client.move_to(voice_channel)
                else:
                    await ctx.send("Bot is currently playing in another voice channel. Please use the `!!stop` command to stop playback first.")
                    return

            if self.voice_client is None:
                self.voice_client = await voice_channel.connect()

    @commands.command()
    async def play(self, ctx, *, search_term):
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
            self.voice_client = ctx.voice_client

        if not ctx.voice_client.is_playing():
            sources = await YTDLSource.create_source(ctx, search_term, loop=self.bot.loop, download=False)
            if isinstance(sources, list):
                self.queue.extend(sources)
                source = self.queue[0]
                ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.check_queue(ctx, e), self.bot.loop))
                await ctx.send(f"Playing **{source.title}** from the playlist :musical_note:")
            else:
                self.queue.append(sources)
                ctx.voice_client.play(sources, after=lambda e: asyncio.run_coroutine_threadsafe(self.check_queue(ctx, e), self.bot.loop))
                await ctx.send(f"Playing **{sources.title}** :musical_note:")
        else:
            sources = await YTDLSource.create_source(ctx, search_term, loop=self.bot.loop, download=False)
            if isinstance(sources, list):
                self.queue.extend(sources)
                await ctx.send(f"Added playlist to queue.")
            else:
                self.queue.append(sources)
                await ctx.send(f"Added to queue: **{sources.title}**")



async def setup(bot):
    await bot.add_cog(Music(bot))
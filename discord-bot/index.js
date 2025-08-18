require('dotenv/config');
const { Client, GatewayIntentBits, EmbedBuilder, ActivityType, Events, Collection } = require('discord.js');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, StreamType, getVoiceConnection, VoiceConnectionStatus } = require('@discordjs/voice');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Create a new client instance
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers
  ]
});

// Music queue and player state
const queues = new Map(); // {guild_id: [songs]}
const currentPlayers = new Map(); // {guild_id: player}
const leaveTimers = new Map(); // {guild_id: timer}

// Function to get stream info using yt-dlp
function getStreamInfo(query) {
  try {
    // Check if query is a URL
    const isUrl = query.startsWith('http');
    
    // Use yt-dlp to get info
    let command;
    if (isUrl) {
      command = `npx yt-dlp -j --no-warnings "${query}"`;
    } else {
      command = `npx yt-dlp -j --no-warnings "ytsearch1:${query}"`;
    }
    
    const result = execSync(command, { encoding: 'utf-8' });
    const info = JSON.parse(result);
    
    // If it's a playlist, return the first entry
    if (info._type === 'playlist' && info.entries && info.entries.length > 0) {
      return info.entries[0];
    }
    
    return info;
  } catch (error) {
    console.error('Error getting stream info:', error);
    throw error;
  }
}

// Function to get stream URL
function getStreamUrl(url) {
  try {
    const command = `npx yt-dlp -g --no-warnings "${url}"`;
    const result = execSync(command, { encoding: 'utf-8' });
    return result.trim();
  } catch (error) {
    console.error('Error getting stream URL:', error);
    throw error;
  }
}

// Function to play the next song
async function playNext(guildId) {
  const queue = queues.get(guildId);
  if (!queue || queue.length === 0) {
    // Queue is empty, schedule bot to leave
    const connection = getVoiceConnection(guildId);
    if (connection) {
      const guild = client.guilds.cache.get(guildId);
      if (guild) {
        // Find notification channel
        let notificationChannel = guild.channels.cache.find(
          ch => (ch.name.includes('bot') || ch.name.includes('general')) && ch.isTextBased()
        );
        
        // If no specific channel found, use the first text channel
        if (!notificationChannel) {
          notificationChannel = guild.channels.cache.find(ch => ch.isTextBased());
        }
        
        if (notificationChannel) {
          const embed = new EmbedBuilder()
            .setTitle('✅ Queue Finished')
            .setDescription('No more songs in the queue. I\'ll leave the channel in 5 minutes if nothing is added.')
            .setColor(0xff0000);
          
          await notificationChannel.send({ embeds: [embed] });
        }
      }
      
      // Schedule leaving
      const timer = setTimeout(() => {
        const conn = getVoiceConnection(guildId);
        if (conn) {
          conn.destroy();
          queues.delete(guildId);
        }
      }, 300000); // 5 minutes
      
      leaveTimers.set(guildId, timer);
    }
    return;
  }
  
  // Cancel any existing leave timers
  if (leaveTimers.has(guildId)) {
    clearTimeout(leaveTimers.get(guildId));
    leaveTimers.delete(guildId);
  }
  
  const song = queue.shift();
  const connection = getVoiceConnection(guildId);
  
  if (!connection) {
    console.error('No voice connection found');
    return;
  }
  
  try {
    const streamUrl = getStreamUrl(song.webpage_url);
    
    // Create audio resource
    const resource = createAudioResource(streamUrl, {
      inputType: StreamType.Arbitrary,
    });
    
    // Create audio player
    const player = createAudioPlayer();
    currentPlayers.set(guildId, player);
    
    // Subscribe the connection to the audio player
    connection.subscribe(player);
    
    // Play the resource
    player.play(resource);
    
    // Update bot status
    client.user.setActivity(`${song.title} - ${song.uploader}`, { type: ActivityType.Playing });
    
    // Find notification channel
    const guild = client.guilds.cache.get(guildId);
    if (guild) {
      let notificationChannel = guild.channels.cache.find(
        ch => (ch.name.includes('bot') || ch.name.includes('general')) && ch.isTextBased()
      );
      
      // If no specific channel found, use the first text channel
      if (!notificationChannel) {
        notificationChannel = guild.channels.cache.find(ch => ch.isTextBased());
      }
      
      if (notificationChannel) {
        const embed = new EmbedBuilder()
          .setTitle('🎶 Now Playing')
          .setDescription(`[${song.title}](${song.webpage_url})
👤 ${song.uploader}`)
          .setColor(0x00ff00);
        
        await notificationChannel.send({ embeds: [embed] });
      }
    }
    
    // When the song finishes, play the next one
    player.on('stateChange', (oldState, newState) => {
      if (newState.status === 'idle') {
        playNext(guildId);
      }
    });
    
    player.on('error', error => {
      console.error('Error playing song:', error);
      playNext(guildId);
    });
  } catch (error) {
    console.error('Error playing song:', error);
    playNext(guildId);
  }
}

// Function to connect to voice channel
async function connectToVoiceChannel(interaction) {
  const channel = interaction.member.voice.channel;
  if (!channel) {
    await interaction.reply('❌ Você precisa estar em um canal de voz!');
    return null;
  }
  
  const connection = joinVoiceChannel({
    channelId: channel.id,
    guildId: channel.guild.id,
    adapterCreator: channel.guild.voiceAdapterCreator,
  });
  
  return connection;
}

// When the client is ready, run this code (only once)
client.once(Events.ClientReady, () => {
  console.log(`${client.user.tag} has logged in!`);
  client.user.setActivity('Ready to play music!', { type: ActivityType.Playing });
});

// Voice state update event
client.on(Events.VoiceStateUpdate, (oldState, newState) => {
  // Ignore bot users
  if (newState.member.user.bot) return;
  
  // Find a notification channel
  const guild = newState.guild;
  let notificationChannel = guild.channels.cache.find(
    ch => (ch.name.includes('bot') || ch.name.includes('general')) && ch.isTextBased()
  );
  
  // If no specific channel found, use the first text channel
  if (!notificationChannel) {
    notificationChannel = guild.channels.cache.find(ch => ch.isTextBased());
  }
  
  // User joined a voice channel
  if (!oldState.channelId && newState.channelId) {
    const embed = new EmbedBuilder()
      .setTitle('🔊 Voice Channel Joined')
      .setDescription(`${newState.member.user} joined ${newState.channel}`)
      .setColor(0x00ff00)
      .setFooter({ text: `User ID: ${newState.member.user.id}` });
    
    if (notificationChannel) {
      notificationChannel.send({ embeds: [embed] });
    }
  }
  
  // User left a voice channel
  else if (oldState.channelId && !newState.channelId) {
    const embed = new EmbedBuilder()
      .setTitle('🔇 Voice Channel Left')
      .setDescription(`${newState.member.user} left ${oldState.channel}`)
      .setColor(0xff0000)
      .setFooter({ text: `User ID: ${newState.member.user.id}` });
    
    if (notificationChannel) {
      notificationChannel.send({ embeds: [embed] });
    }
  }
  
  // User switched voice channels
  else if (oldState.channelId && newState.channelId && oldState.channelId !== newState.channelId) {
    const embed = new EmbedBuilder()
      .setTitle('🔄 Voice Channel Moved')
      .setDescription(`${newState.member.user} moved from ${oldState.channel} to ${newState.channel}`)
      .setColor(0x0000ff)
      .setFooter({ text: `User ID: ${newState.member.user.id}` });
    
    if (notificationChannel) {
      notificationChannel.send({ embeds: [embed] });
    }
  }
});

// Handle slash commands
client.on(Events.InteractionCreate, async interaction => {
  if (!interaction.isChatInputCommand()) return;
  
  const { commandName } = interaction;
  
  if (commandName === 'entrar_no_rubi') {
    const channel = interaction.member.voice.channel;
    if (!channel) {
      await interaction.reply('Você precisa estar em um canal de voz para usar este comando.');
      return;
    }
    
    try {
      await connectToVoiceChannel(interaction);
      await interaction.reply(`🔊 Conectado ao canal: ${channel.name}`);
    } catch (error) {
      console.error('Error connecting to voice channel:', error);
      await interaction.reply(`❌ Erro ao conectar: ${error.message}`);
    }
  }
  else if (commandName === 'play') {
    const query = interaction.options.getString('query');
    
    // Connect to voice channel
    const connection = await connectToVoiceChannel(interaction);
    if (!connection) return;
    
    const guildId = interaction.guildId;
    
    try {
      console.log(`🔎 Procurando: ${query}`);
      
      // Get stream info
      const info = getStreamInfo(query);
      
      // If it's a playlist
      if (info._type === 'playlist') {
        const playlistTitle = info.title || 'Unknown Playlist';
        let songsAdded = 0;
        
        // Initialize queue if needed
        if (!queues.has(guildId)) {
          queues.set(guildId, []);
        }
        
        for (const entry of info.entries || []) {
          try {
            const fullInfo = getStreamInfo(entry.url);
            const song = {
              title: fullInfo.title || 'Unknown Title',
              webpage_url: fullInfo.webpage_url || entry.url,
              uploader: fullInfo.uploader || 'Unknown Uploader'
            };
            
            // Add to queue
            queues.get(guildId).push(song);
            songsAdded++;
          } catch (error) {
            console.error('Error adding song to queue:', error);
          }
        }
        
        // Reply with playlist info
        const embed = new EmbedBuilder()
          .setTitle('📂 Playlist Added')
          .setDescription(`Adicionadas ${songsAdded} músicas de [${playlistTitle}](${info.webpage_url || ''})`)
          .setColor(0x0000ff);
        
        await interaction.reply({ embeds: [embed] });
        
        // Start playing if not already playing
        const player = currentPlayers.get(guildId);
        if (!player) {
          playNext(guildId);
        }
      } else {
        // Single song
        const song = {
          title: info.title || 'Unknown Title',
          webpage_url: info.webpage_url || query,
          uploader: info.uploader || 'Unknown Uploader'
        };
        
        // Add to queue
        if (!queues.has(guildId)) {
          queues.set(guildId, []);
        }
        queues.get(guildId).push(song);
        
        // Cancel any existing leave timers
        if (leaveTimers.has(guildId)) {
          clearTimeout(leaveTimers.get(guildId));
          leaveTimers.delete(guildId);
        }
        
        // Reply with added song info
        const player = currentPlayers.get(guildId);
        if (!player) {
          await interaction.reply(`🎶 Playing: [${song.title}](${song.webpage_url})`);
          playNext(guildId);
        } else {
          const embed = new EmbedBuilder()
            .setTitle('➕ Added to Queue')
            .setDescription(`[${song.title}](${song.webpage_url})`)
            .setColor(0x0000ff);
          
          await interaction.reply({ embeds: [embed] });
        }
      }
    } catch (error) {
      console.error('Error processing play command:', error);
      await interaction.reply(`❌ Erro ao processar: \`${error.message}\``);
    }
  }
  else if (commandName === 'stop') {
    const guildId = interaction.guildId;
    const connection = getVoiceConnection(guildId);
    
    if (connection) {
      // Clear queue
      if (queues.has(guildId)) {
        queues.delete(guildId);
      }
      
      // Cancel leave timer
      if (leaveTimers.has(guildId)) {
        clearTimeout(leaveTimers.get(guildId));
        leaveTimers.delete(guildId);
      }
      
      // Stop player and disconnect
      const player = currentPlayers.get(guildId);
      if (player) {
        player.stop();
        currentPlayers.delete(guildId);
      }
      
      connection.destroy();
      await interaction.reply('Stopped playing music and cleared the queue.');
    } else {
      await interaction.reply('I\'m not connected to a voice channel.');
    }
  }
  else if (commandName === 'skip') {
    const guildId = interaction.guildId;
    const player = currentPlayers.get(guildId);
    
    if (player) {
      player.stop(); // This will trigger the AudioPlayerStatus.Idle event which plays the next song
      await interaction.reply('Skipped the current song.');
    } else {
      await interaction.reply('There\'s no song currently playing.');
    }
  }
  else if (commandName === 'skipall') {
    const guildId = interaction.guildId;
    
    if (queues.has(guildId)) {
      const skippedCount = queues.get(guildId).length;
      queues.get(guildId).length = 0; // Clear the queue
      await interaction.reply(`Skipped ${skippedCount} songs from the queue.`);
    } else {
      await interaction.reply('The queue is currently empty.');
    }
  }
  else if (commandName === 'queue') {
    const guildId = interaction.guildId;
    
    if (queues.has(guildId) && queues.get(guildId).length > 0) {
      const queue = queues.get(guildId);
      let queueList = '';
      
      for (let i = 0; i < Math.min(queue.length, 10); i++) {
        const song = queue[i];
        queueList += `${i + 1}. [${song.title}](${song.webpage_url})
`;
      }
      
      const embed = new EmbedBuilder()
        .setTitle('Music Queue')
        .setDescription(queueList)
        .setColor(0x00ff00);
      
      if (queue.length > 10) {
        embed.setFooter({ text: `And ${queue.length - 10} more songs...` });
      }
      
      await interaction.reply({ embeds: [embed] });
    } else {
      await interaction.reply('The queue is currently empty.');
    }
  }
  else if (commandName === 'ping') {
    await interaction.reply('Pong!');
  }
  else if (commandName === 'hello') {
    await interaction.reply(`Hello ${interaction.user}!`);
  }
});

// Login to Discord with your client's token
client.login(process.env.DISCORD_TOKEN);
const { REST, Routes } = require('discord.js');
require('dotenv/config');

const commands = [
  {
    name: 'entrar_no_rubi',
    description: 'Conecta o bot ao canal de voz'
  },
  {
    name: 'play',
    description: 'Reproduz música do YouTube ou adiciona à fila',
    options: [
      {
        name: 'query',
        type: 3, // STRING
        description: 'Nome da música ou URL',
        required: true
      }
    ]
  },
  {
    name: 'stop',
    description: 'Para de tocar música e limpa a fila'
  },
  {
    name: 'skip',
    description: 'Pula a música atual'
  },
  {
    name: 'skipall',
    description: 'Pula todas as músicas na fila'
  },
  {
    name: 'queue',
    description: 'Mostra a fila de músicas atual'
  },
  {
    name: 'ping',
    description: 'Verifica se o bot está respondendo'
  },
  {
    name: 'hello',
    description: 'Diz olá'
  }
];

const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

(async () => {
  try {
    console.log('Started refreshing application (/) commands.');

    await rest.put(
      Routes.applicationCommands(process.env.DISCORD_CLIENT_ID),
      { body: commands }
    );

    console.log('Successfully reloaded application (/) commands.');
  } catch (error) {
    console.error(error);
  }
})();
import os
import discord
import discord.utils
from dotenv import load_dotenv
import requests
import json
from discord.ext import tasks
import pandas as pd
import asyncio  # Import asyncio module
import time

#READ EXISTING PLATE APPEARANCES SO WE DONT POST OLD STUFF, RUNS ONCE AT START TO POPULATE LIST
with open("paIDs.txt",mode='r') as f:
    read_paIDs = f.readlines()

existing_paIDs = []
for sub in read_paIDs:
    existing_paIDs.append(sub.replace("\n", ""))

player_ids = ['2997', '3028', '3029', '3044', '3057', '3045', '3009', '3061', '3032', '3001', '2981', '2992', '3021', '3051', '180', '2875', '2916']
sides = ['pitching','batting']
leagues = ['mlr','milr']
cid = '1236127238324224000'


# The script that pulls the data from the api and checks if there's new pitches
def get_new_pas():
    new_pas = []
    for player in player_ids:
        for side in sides:
            for league in leagues:
                print('checking ' + player + ' ' + side + ' in ' + league)
                api_url = 'https://www.rslashfakebaseball.com/api/plateappearances/' + side + '/' + league + '/' + player
                response = requests.get(api_url)
                if response.status_code == 200:
                    pas = response.json()
                    # print(pas)
                    for pa in pas:
                        if str(pa['paID']) not in existing_paIDs:
                            #do stuff
                            with open('paIDs.txt','a') as f:
                                f.write(str(pa['paID']) + '\n')
                            print('added pitch ' + str(pa['paID']))
                            existing_paIDs.append(str(pa['paID']))
                            new_pas.append(pa)
                        # else:
                        #     print('skipped pitch')
                else:
                    print(f"Failed to fetch data. Status code: {response.status_code}")
                    print(player)
    return new_pas

#responsible for formatting the message that goes out
def generate_disc_message(pa):
    #find who the cats are
    pitcher_cat = is_bobcat(str(pa['pitcherID']))
    batter_cat = is_bobcat(str(pa['hitterID']))
    #find home and away team
    if pa['inning'].startswith('T'):
        hometeam = pa['pitcherTeam']
        awayteam = pa['hitterTeam']
    else:
        hometeam = pa['hitterTeam']
        awayteam = pa['pitcherTeam']
    #generate top line of msg
    gameline = '**' + pa['league'] + " " + str(pa['season']) + '.' + str(pa['session']) + ' ' + awayteam + ' @ ' + hometeam + '**'

    #generate 2nd line (batter batting against pitcher)
    if batter_cat:
        batter = pa['hitterName'] + ' <:txs:1236123896399265884>'
    else:
        batter = pa['hitterName'] 
    if pitcher_cat:
        pitcher = pa['pitcherName'] + ' <:txs:1236123896399265884>'
    else:
        pitcher = pa['pitcherName'] 
    abline = pa['hitterTeam'] + ' ' + batter + ' batting against ' + pa['pitcherTeam'] + ' ' + pitcher
    #generate 3rd line (situation pre ab) (include a blank line after)
    if pa['outs'] == 0:
        firstout = '⚪'
        secondout = '⚪'
    elif pa['outs'] == 1:
        firstout = '🔴'
        secondout = '⚪'
    else:
        firstout = '🔴'
        secondout = '🔴'

    match pa['obc']: 
        case 0:
            firstbase = '○'
            secondbase = '○'
            thirdbase = '○'
        case 1:
            firstbase = '●'
            secondbase = '○'
            thirdbase = '○'
        case 2:
            firstbase = '○'
            secondbase = '●'
            thirdbase = '○'
        case 3:
            firstbase = '○'
            secondbase = '○'
            thirdbase = '●'
        case 4:
            firstbase = '●'
            secondbase = '●'
            thirdbase = '○'
        case 5:
            firstbase = '●'
            secondbase = '○'
            thirdbase = '●'
        case 6:
            firstbase = '○'
            secondbase = '●'
            thirdbase = '●'
        case 7:
            firstbase = '●'
            secondbase = '●' 
            thirdbase = '●'

    sit1 = awayteam + ' ' + str(pa['awayScore']) + '   ' + secondbase
    sit2 = hometeam + ' ' + str(pa['homeScore']) + '  ' + thirdbase + ' ' + firstbase
    sit3 = pa['inning'] +  ' ' + firstout + secondout
    situation = sit1 + '\n' + sit2 + '\n' + sit3
    #generate pitch, swing, diff and result line (include a blank line after)
    pitchline = 'P: ' + str(pa['pitch'])
    swingline = 'S: ' + str(pa['swing'])
    # Generate Result line (w RBIs)
    resultline = 'Diff: ' + str(pa['diff']) + ' -> ' + pa['exactResult']
    if pa['rbi'] == 1:
        resultline = resultline + ', 1 Run scores'
    elif pa['rbi'] > 1:
        resultline = resultline + ', ' + str(pa['rbi']) + ' Runs score'
    #combine and space
    swingsection = pitchline + ', ' + swingline + ', ' + resultline
    #TODO generate score and after ab situtation lines
    #smush them together and return
    msg_to_send = gameline + '\n' + abline + '\n```' + situation + '\n' + swingsection + '```'
    print(msg_to_send)
    return msg_to_send

#unused atm
def get_bases_text(obc):
    return 'Bases empty'


#find if player is a bobcat so we can denote it properly
def is_bobcat(id):
    if id in player_ids:
        return True
    else:
        return False

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

## ON READY
@client.event
async def on_ready():
    global channel
    for guild in client.guilds:
        if guild.name == GUILD:
            channel = discord.utils.get(guild.channels, id=int(cid))
            break

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    
    # Start the check_for_pas task after the bot is ready
    check_for_pas.start()

## Every 120s
@tasks.loop(seconds=120)
async def check_for_pas():
    print('e')
    new_pas = get_new_pas()
    print(new_pas)
    i=0
    if new_pas:
        for pa in new_pas:
            msg = generate_disc_message(pa)
            await channel.send(msg)
            time.sleep(10)
            
@check_for_pas.before_loop
async def before_checks():
    print('d')
    await client.wait_until_ready()

# Define a function to start the bot
async def start_bot():
    print('c')
    await client.start(TOKEN)

# Run the bot
async def main():
    print('b')
    await start_bot()

# Start the event loop and run the bot
if __name__ == "__main__":
    asyncio.run(main())
    print('a')
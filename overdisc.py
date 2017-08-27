"""Overwatch-Discord rank-role sync bot"""
# By Wolfie

import asyncio
import json

import discord
from overwatch_api.constants import *
from overwatch_api.core import AsyncOWAPI
from datetime import date, timedelta
import calendar
import traceback
import matplotlib.pyplot as plt
import numpy as np
from github import Github
from distutils.version import LooseVersion

try:
    with open("config.json", "r") as rawjson: #Load config file
        configfile = json.loads(rawjson.read())
except json.JSONDecodeError:
    print("Config file corrupted.  Recopy from template and try again.")
    exit()

debug = False  # Is debug mode on?
# development = True # Is this development code (If so only respond to calls from the debug channel)
version = "v2.78"  # What version is OverDisc?
builddate= "27/08/2017 18:05" #When was this version of OverDisc built
development = configfile['Development'] # Is this development code (If so only respond to calls from the debug channel)

def getrepo():
    g = Github(configfile['Github-token']) #Connect to GitHub with token authentication
    re = g.get_repo("Xalaxis/OverDisc")
    return re

async def checkupdate(message):
    updateavailable = False
    updateschecked = []
    releases = getrepo().get_releases() #Get releases from the repo
    for release in releases:
        if development:
            await discordprint(message, "Checking development releases...")
            if release.raw_data['target_commitish'] == "development":
                updateschecked = updateschecked + [release.tag_name]
                if LooseVersion(release.tag_name) > LooseVersion(version):
                    await discordprint(message, "Update Available")
                    await discordprint(message,"Current Version: " + version + "\nRemote version: " + release.tag_name)
                    updateavailable = True
                else:
                    print("Ignoring old release")
            if updateavailable == False:
                await discordprint(message, "No new release found")
                if debug:
                    await discordprint(message, "Releases checked:")
                    for i in updateschecked:
                        await discordprint(message, i)
        else:
            await discordprint(message, "Checking mainline releases...")
            if release.raw_data['target_commitish'] == "master":
                updateschecked = updateschecked + [release.tag_name]
                if LooseVersion(release.tag_name) > LooseVersion(version):
                    await discordprint(message, "Update Available")
                    await discordprint(message,"Current Version: " + version + "\nRemote version: " + release.tag_name)
                    updateavailable = True
                else:
                    print("Ignoring old release")
            if updateavailable == False:
                await discordprint(message, "No new release found")
                if debug:
                    await discordprint(message, "Releases checked:")
                    for i in updateschecked:
                        await discordprint(message, i)


client = discord.Client()  # Making local reference to the Discord client object
overclient = AsyncOWAPI()  # Making local reference to the Overwatch API client object

@client.event
async def on_ready(): #When bot is connected
    """Runs when the bot is first successfully connected"""
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print("Setting game")
    await client.change_presence(game=discord.Game(name='OverDisc ' + version))
    print('Invite: https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=402653184'.format(client.user.id))
    print('------')


async def srlog(message, text): #Send the contents of 'text' to the server channel #srlog from the server associated with 'message'
    print("Logging to #srlog")
    server = message.server
    await client.send_message(discord.utils.get(server.channels, name="srlog", type=discord.ChannelType.text), text)


async def discordprint(message, text): #Print the message 'text' and send it to the same channel we recieved our message from originally
    print(text)
    await client.send_message(message.channel, text)

async def candrop(oldrank):
    if oldrank == "Bronze" or "Silver" or "Gold" or "Platinum" or "Diamond": #Ranks that can't drop
        return False
    if oldrank == "": #We don't have any rank in the database
        return True
    else:
        if oldrank == "Master" or "Grandmaster": #Ranks that can drop
            return True

@client.event
async def on_message(message):
    """Runs when the bot recieves a message"""
    global debug
    server = message.server  # Localizing the server the message is from as 'server'
    if (development and message.channel == discord.utils.get(server.channels, name="temporarytesting", type=discord.ChannelType.text)) or (development != True and message.channel != discord.utils.get(server.channels, name="temporarytesting", type=discord.ChannelType.text)):
        if message.content.startswith('!updateroles'):  # If this is the update rank command
            if message.content.endswith('!dailyupdate'):
                dailyupdate = True
            else:
                dailyupdate = False
            with open("sr.json", "r") as rawjson:
                srdata = json.loads(rawjson.read())
            # print(srdata['Placeholder']['Current_SR'])
            await discordprint(message, "Beginning update... OverDisc version: " + version)
            ignored = 0
            total = 0
            timeout = 0
            for member in client.get_all_members():  # Get a list of all member and then pass the 'member' object one-by-one
                if member.nick not in srdata:  # If we don't have an entry yet for that user
                    srdata[member.nick] = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0, 'Friday': 0, 'Rank': ""}  # Create it with 0 values
                total = total + 1
                print("Checking " + member.name)
                if str(member.nick) != "None":  # As long as a nickname is set
                    try:
                        profile = await overclient.get_stats(str(member.nick), platform=PC, regions=EUROPE)  # Request stats from the Overwatch API
                        try:
                            if profile['eu']['competitive'] is not None:  # As long as the player currently has a rank
                                if profile['eu']['competitive']['overall_stats']['comprank'] is not None:
                                    comprank = profile['eu']['competitive']['overall_stats']['comprank']
                                    try:
                                        my_date = date.today()
                                        yesterday_date = date.today() - timedelta(days=1)
                                        srdata[member.nick][calendar.day_name[my_date.weekday()]] = comprank  # Record user's SR as their SR for the current day
                                        if srdata[member.nick][calendar.day_name[my_date.weekday()]] - srdata[member.nick][calendar.day_name[yesterday_date.weekday()]] >= 0:  # If user's rank is positive
                                            indicator = "+"  # Give the number a positive indicator
                                        else:
                                            indicator = ""  # A negative indicator is already part of the number so there is no need to add one
                                        srdiff = str(calendar.day_name[yesterday_date.weekday()]) + ": " + str(srdata[member.nick][calendar.day_name[yesterday_date.weekday()]]) + " -> " + str(calendar.day_name[my_date.weekday()]) + ": " + str(
                                            srdata[member.nick][calendar.day_name[my_date.weekday()]]) + " (" + indicator + str(
                                            srdata[member.nick][calendar.day_name[my_date.weekday()]] - srdata[member.nick][calendar.day_name[yesterday_date.weekday()]]) + ")"
                                        if dailyupdate:
                                            await srlog(message, member.nick + ": " + srdiff)
                                    except KeyError: #Entry doesn't exist
                                        await discordprint(message, "⚠ Database error: Wolfie dun goofed")
                                        print(traceback.print_exc())

                                    rank = srdata[member.nick]['Rank']# Collect rank from storage
                                    if comprank <= 1499:
                                        if candrop(rank): #If user can fall to Bronze
                                            rank = "Bronze"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Bronze"))
                                        else:
                                            ranklocked = True
                                    elif comprank <= 1999:
                                        if candrop(rank) or rank == "Bronze": #If user can fall to Silver or they are climbing from Bronze
                                            rank = "Silver"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Silver"))
                                        else:
                                            ranklocked = True
                                    elif comprank <= 2499:
                                        if candrop(rank) or rank == "Bronze" or rank == "Silver":
                                            rank = "Gold"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Gold"))
                                        else:
                                            ranklocked = True
                                    elif comprank <= 2999:
                                        if candrop(rank) or rank == "Bronze" or rank == "Silver" or rank == "Gold":
                                            rank = "Platinum"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Platinum"))
                                        else:
                                            ranklocked = True
                                    elif comprank <= 3499:
                                        if candrop(rank) or rank == "Bronze" or rank == "Silver" or rank == "Gold" or rank == "Platinum":
                                            rank = "Diamond"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Diamond"))
                                        else:
                                            ranklocked = True
                                    elif comprank <= 3999:
                                        if candrop(rank) or rank == "Bronze" or rank == "Silver" or rank == "Gold" or rank == "Platinum" or rank == "Diamond":
                                            rank = "Master"
                                            await client.replace_roles(member, discord.utils.get(server.roles, name="Master"))
                                        else:
                                            ranklocked = True
                                    else:
                                        rank = "Grandmaster" #No need to check as max rank
                                        await client.replace_roles(member, discord.utils.get(server.roles, name="Grandmaster"))
                                    if debug:
                                        await discordprint(message, str(member.nick) + ": " + str(comprank) + " | " + rank + " | " + srdiff)
                                        if ranklocked:
                                            await discordprint(message, "Rank locked")
                                    srdata[member.nick]['Rank'] = rank  # Assign current rank to storage
                                else:
                                    rank = "No current rank (But has played competitive)"
                                    srdata[member.nick]['Rank'] = rank  # Assign current rank to storage
                                    if debug:
                                        await discordprint(message, str(member.nick) + ": " + "####" + " | " + rank)
                                    await client.replace_roles(member, discord.utils.get(server.roles, name="In Placement"))  # Assign the 'In Placement' role as they are probably still placing
                            else:
                                rank = "No current rank (Has never played competitive)"
                                srdata[member.nick]['Rank'] = rank  # Assign current rank to storage
                                if debug:
                                    await discordprint(message, str(member.nick) + ": " + "####" + " | " + rank)
                                await client.replace_roles(member, discord.utils.get(server.roles, name="Newbie"))  # Assign the newbie role as they have never played competitive
                        except KeyError:
                            rank = "No EU rank or incorrect Battletag"
                            srdata[member.nick]['Rank'] = rank  # Assign current rank to storage
                            if debug:
                                await discordprint(message, str(member.nick) + ": " + "####" + " | " + rank)
                            await client.replace_roles(member, discord.utils.get(server.roles, name="Unknown SR"))  # Assign the unknown role to get around the current 'replace' hack
                        except discord.Forbidden:
                            await discordprint(message, "Unable to perform action.  Do I have enough permissions?  User: " + member.name)
                    except asyncio.TimeoutError:  # If the request times out
                        await discordprint(message, "Overwatch API timed out.  User " + member.nick + " skipped temporarily.")
                        timeout = timeout + 1
                elif member.id == "320884860564537354":  # Skip OverDisc user
                    print("Ignoring OverDisc user")
                    ignored = ignored + 1
                else:
                    if debug:
                        await discordprint(message, "Ignoring user " + member.name + " because no nickname was set.")
                    await client.replace_roles(member, discord.utils.get(server.roles, name="Unknown SR"))  # Assign the unknown role to get around the current 'replace' hack
                    ignored = ignored + 1

            await discordprint(message, "Update complete ✅")
            if dailyupdate:
                await discordprint(message, "#srlog updated ✅")
            await discordprint(message, "Total: " + str(total) + " Ignored: " + str(ignored) + "❓ Timeout: " + str(timeout) + "❌")
            print("Writing SR Data to Disk...")
            with open("sr.json", "w") as rawjson:
                rawjson.write(json.dumps(srdata, indent=4))
            print("Data written.")
        if message.content.startswith("!resetroles"):
            for member in client.get_all_members():
                if member.id != "320884860564537354":  # Skip OverDisc user
                    try:
                        if debug:
                            await discordprint(message, "Removing roles from " + str(member.name))
                        await client.replace_roles(member, discord.utils.get(server.roles, name="In Placement"))
                    except discord.Forbidden:
                        await discordprint(message, "Unable to perform action.  Do I have enough permissions?  User: " + member.name)
            await discordprint(message, "Removing all roles complete ✅")

        if message.content.startswith("!debugon"):
            debug = True
            await discordprint(message, "Debug mode ON ✅")

        if message.content.startswith("!debugoff"):
            debug = False
            await discordprint(message, "Debug mode OFF ✅")

        if message.content.startswith("!ping"):
            await discordprint(message, "Pong!")

        if message.content.startswith("!graph"):
            with open("sr.json", "r") as rawjson:
                srdata = json.loads(rawjson.read())
            if message.content.endswith("rank pie"):
                # Pie chart, where the slices will be ordered and plotted counter-clockwise:
                bronze = 0
                silver = 0
                gold = 0
                platinum = 0
                diamond = 0
                master = 0
                grandmaster = 0
                with open("sr.json", "r") as rawjson:
                    srdata = json.loads(rawjson.read())
                for key, value in srdata.items():
                    if value['Rank'] == "Bronze":
                        bronze += 1
                    elif value['Rank'] == "Silver":
                        silver += 1
                    elif value['Rank'] == "Gold":
                        gold += 1
                    elif value['Rank'] == "Platinum":
                        platinum += 1
                    elif value['Rank'] == "Diamond":
                        diamond += 1
                    elif value['Rank'] == "Master":
                        master += 1
                    elif value['Rank'] == "Grandmaster":
                        grandmaster += 1
                labels = 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Grandmaster'
                sizes = [bronze, silver, gold, platinum, diamond, master, grandmaster]
                fig1, ax1 = plt.subplots()
                ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
                    shadow=True, startangle=90)
                ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                plt.savefig('rankpie.png')
                await client.send_file(message.channel, 'rankpie.png')
            if message.content.endswith("rank bar"):
                bronze = 0
                silver = 0
                gold = 0
                platinum = 0
                diamond = 0
                master = 0
                grandmaster = 0
                with open("sr.json", "r") as rawjson:
                    srdata = json.loads(rawjson.read())
                for key, value in srdata.items():
                    if value['Rank'] == "Bronze":
                        bronze += 1
                    elif value['Rank'] == "Silver":
                        silver += 1
                    elif value['Rank'] == "Gold":
                        gold += 1
                    elif value['Rank'] == "Platinum":
                        platinum += 1
                    elif value['Rank'] == "Diamond":
                        diamond += 1
                    elif value['Rank'] == "Master":
                        master += 1
                    elif value['Rank'] == "Grandmaster":
                        grandmaster += 1
                labels = 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'GMaster'
                y_pos = np.arange(len(labels))
                sizes = [bronze, silver, gold, platinum, diamond, master, grandmaster]

                plt.bar(y_pos, sizes, align='center', alpha=0.5)
                plt.xticks(y_pos, labels)
                plt.ylabel('Number of users')
                plt.title('Ranks')
                plt.savefig('rankbar.png')
                await client.send_file(message.channel, 'rankbar.png')

        if message.content.startswith("!memberlist"):
            totalmembers = 0
            for member in client.get_all_members():
                totalmembers = totalmembers + 1
                print(member.name)
            discordprint(message, "Total members " + str(totalmembers))

        if message.content.startswith("!changelog"):
            await client.send_message(message.channel, "Not yet implemented but will be eventually \n\n\n\nTest new lines")

        if message.content.startswith("!updatecheck"):
            await checkupdate(message)
    else:
        if (development and message.channel != discord.utils.get(server.channels, name="temporarytesting", type=discord.ChannelType.text)): #If we're in development mode and recieve a message from a non-authorized channel
            print("In development mode -- ignoring message from incorrect channel (#" + str(message.channel) + ")")

client.run(configfile['Discord-token'])

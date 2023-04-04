import disnake
from disnake import Button, ButtonStyle, Member, Role, TextInputStyle
from disnake.ext import commands
import asyncio
import re
import sqlite3

from config import TOKEN

bot = commands.Bot(command_prefix="/", intents=disnake.Intents.all())

con = sqlite3.connect('teams.db')
cur = con.cursor()

@bot.event
async def on_ready():
    game = disnake.Activity(name="Dota 2", type=disnake.ActivityType.playing)
    await bot.change_presence(status=disnake.Status.idle, activity=game)
    print("Bot is ready")

    cur.execute("""CREATE TABLE IF NOT EXISTS teams(
        team_name TEXT,
        description TEXT,
        id1 INT,
        name1 TEXT,
        id2 INT,
        name2 TEXT,
        id3 INT,
        name3 TEXT,
        id4 INT,
        name4 TEXT,
        id5 INT,
        name5 TEXT,
        wined_maps INT,
        is_open INT,
        invited_members TEXT
    )""")
    con.commit()

@bot.slash_command(description="Создайте свою команду!")
async def create_team(ctx, name, description):
    team_role = await ctx.guild.create_role(name=f"team {name}")
    await ctx.author.add_roles(team_role)

    overwrites = {
        ctx.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
        team_role: disnake.PermissionOverwrite(read_messages=True)
    }

    team_category = await ctx.guild.create_category(name=f"team {name}", overwrites=overwrites)

    team_channel = await team_category.create_text_channel(name=f"Team {name}-chat")
    await team_channel.set_permissions(team_role, read_messages=True, send_messages=True)

    team_voice_channel = await team_category.create_voice_channel(name=f"Team {name}-voice")
    await team_voice_channel.set_permissions(team_role, connect=True, speak=True, read_messages=True)

    if cur.execute(f"SELECT id1 FROM teams WHERE id1 = {ctx.author.id}").fetchone() is None:
        cur.execute(f'INSERT INTO teams VALUES ("{name}","{description}","{ctx.author.id}","{ctx.author.name}",0,"",0,"",0,"",0,"",0,1,"{team_role.id}")')
        con.commit()
        await ctx.send(f"Команда '{name}' создана")

    elif not cur.execute(f"SELECT team_name FROM teams WHERE team_name = '{name}'").fetchone() is None:
        await ctx.send(f"Команда под названием '{name}' уже создана")

    else:
        await ctx.send(f"Вы уже владелец или участник одной из команд")



@bot.slash_command(description="Пригласить участника в команду")
async def invite(ctx, member: disnake.Member):

    team_data = cur.execute(f"SELECT team_name, id1 FROM teams WHERE id1 = {ctx.author.id}").fetchone()
    if team_data is None:
        await ctx.send("Вы не являетесь лидером какой-либо команды")
        return

    team_name, leader_id = team_data

    if not cur.execute(f"SELECT team_name FROM teams WHERE id1 = {member.id}").fetchone() is None:
        await ctx.send(f"{member.mention} уже является участником команды")
        return

    if cur.execute(f"SELECT team_name FROM teams WHERE id1 = {member.id}").fetchone() is not None:
        await ctx.send(f"{member.mention} уже был приглашен в другую команду")
        return

    is_open = cur.execute(f"SELECT is_open FROM teams WHERE team_name = '{team_name}'").fetchone()[0]
    if not is_open:
        await ctx.send(f"Набор в команду '{team_name}' закрыт")
        return

    cur.execute(f"UPDATE teams SET invited_members = invited_members || '{member.id},' WHERE team_name = '{team_name}'")
    con.commit()

    await member.send(f"{ctx.author.mention} приглашает вас в команду '{team_name}'")
    await ctx.send(f"{ctx.author.mention} пригласил {member.mention} в команду '{team_name}'")


@bot.slash_command(description="Присоединиться к команде")
async def join_team(ctx, team_name):
    team_data = cur.execute(f"SELECT team_name, id1, id2, id3, id4, id5, is_open, invited_members FROM teams WHERE team_name = '{team_name}'").fetchone()

    if team_data:
        team_name, id1, id2, id3, id4, id5, is_open, invited_members = team_data
        member = ctx.author
        team_role_name = f"{team_name}"
        team_role = disnake.utils.get(ctx.guild.roles, name=team_role_name)

        if not team_role:
            team_role = await ctx.guild.create_role(name=team_role_name)
        
        if member.id in [id1, id2, id3, id4, id5]:
            await ctx.send("Вы уже являетесь участником этой команды")
        elif not any([id1, id2, id3, id4, id5]):
            await ctx.send("Команда еще не создана")
        elif not is_open and member.id not in invited_members:
            await ctx.send("Вы не приглашены в эту команду")
        elif any([id1 == 0, id2 == 0, id3 == 0, id4 == 0, id5 == 0]):
            for i in range(1, 6):
                if team_data[i] == 0:
                    cur.execute(f"UPDATE teams SET id{i} = {member.id}, name{i} = '{member.name}' WHERE team_name = '{team_name}'")
                    con.commit()
                    await member.add_roles(team_role)  # Выдача роли
                    await ctx.send(f"Вы успешно присоединились к команде '{team_name}'")
                    break
        else:
            await ctx.send("Команда уже заполнена")
    else:
        await ctx.send(f"Команда с названием '{team_name}' не найдена")




@bot.slash_command(description="Узнайте состав своей команды")
async def my_team(ctx):
    team_data = cur.execute(f"SELECT team_name, id1, id2, id3, id4, id5, wined_maps FROM teams WHERE id1 = {ctx.author.id} OR id2 = {ctx.author.id} OR id3 = {ctx.author.id} OR id4 = {ctx.author.id} OR id5 = {ctx.author.id}").fetchone()
    if team_data:
        team_name, id1, id2, id3, id4, id5, wined_maps = team_data
        team_members = []
        for member_id in [id1, id2, id3, id4, id5]:
            if member_id:
                member = await bot.fetch_user(member_id)
                team_members.append(member.mention)
        team_list = "\n".join(team_members)
        embed = disnake.Embed(title=f"Информация о команде {team_name}:", color=disnake.Color.green())
        embed.add_field(name="Участники", value=team_list)
        embed.add_field(name="Количество побед", value=wined_maps)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Пока что нет команды")


@bot.slash_command(description="Удалить команду")
async def delete_team(ctx):
    try:
        cur.execute(f"SELECT team_name, id1 FROM teams WHERE id1 = {ctx.author.id}")
        team_data = cur.fetchone()

        if team_data:
            team_name, id1 = team_data
            team_name = f"team {team_name}"
            category = disnake.utils.get(ctx.guild.categories, name=team_name)
            if category:
                for channel in category.channels:
                    await channel.delete()
                await category.delete()
            team_name, id1 = team_data
            role = disnake.utils.get(ctx.guild.roles, name=f"team {team_name}")
            if role:
                await role.delete()

            cur.execute(f"DELETE FROM teams WHERE team_name = '{team_name}'")
            con.commit()

            await ctx.send(f"Команда '{team_name}' успешно удалена")
        else:
            await ctx.send("Вы не являетесь владельцем команды")
    except Exception as e:
        print(e)
        await ctx.send("Ошибка при выполнении команды")


@bot.slash_command(description="Покинуть команду")
async def leave_team(ctx):
    member_id = ctx.author.id

    cur.execute(f"SELECT * FROM teams WHERE id1={member_id} OR id2={member_id} OR id3={member_id} OR id4={member_id} OR id5={member_id}")
    result = cur.fetchone()

    if result is None:
        await ctx.send("Вы не в команде")
    else:
        if member_id == result[2]:  # leader
            await ctx.send("Лидер не может покинуть команду")
        else:
            member_index = None
            for i in range(3, 11, 2):
                if result[i] == member_id:
                    member_index = i
                    break
            
            if member_index is not None:
                await ctx.send("Вы не в команде")
            else:
                team_name = result[0]
                cur.execute(f"UPDATE teams SET id{int((member_index-3)/2)+1} = NULL, name{int((member_index-3)/2)+1} = NULL WHERE team_name='{team_name}'")
                con.commit()

                role = disnake.utils.get(ctx.guild.roles, name=f"team {team_name}")
                await ctx.author.remove_roles(role)

                await ctx.send("Вы покинули команду")

@bot.slash_command(description="Открыть команду")
async def open_team(ctx):
    cur.execute(f"SELECT team_name, id1, is_open FROM teams WHERE id1 = {ctx.author.id}")
    team_data = cur.fetchone()

    if team_data:
        team_name, id1, is_open = team_data

        if is_open:
            await ctx.send("Команда уже открыта")
        else:
            cur.execute(f"UPDATE teams SET is_open = 1 WHERE team_name='{team_name}'")
            con.commit()
            await ctx.send(f"Команда '{team_name}' открыта")
    else:
        await ctx.send("Вы не являетесь владельцем команды")

@bot.slash_command(description="Закрыть команду")
async def close_team(ctx):
    cur.execute(f"SELECT team_name, id1, is_open FROM teams WHERE id1 = {ctx.author.id}")
    team_data = cur.fetchone()

    if team_data:
        team_name, id1, is_open = team_data

        if not is_open:
            await ctx.send("Команда уже закрыта")
        else:
            cur.execute(f"UPDATE teams SET is_open = 0 WHERE team_name='{team_name}'")
            con.commit()
            await ctx.send(f"Команда '{team_name}' закрыта")
    else:
        await ctx.send("Вы не являетесь владельцем команды")

@bot.slash_command(description="Добавить выигрыш команде")
@commands.has_permissions(administrator=True)
async def win(ctx, team_name: str, num_wins):
    num_wins = int(num_wins)
    if num_wins < 1 or num_wins > 3:
        await ctx.send("Некорректное количество выигрышей")
        return

    cur.execute(f"SELECT * FROM teams WHERE team_name='{team_name}'")
    team_data = cur.fetchone()

    if team_data:
        wins = int(team_data[11]) + num_wins
        cur.execute(f"UPDATE teams SET wined_maps={wins} WHERE team_name='{team_name}'")
        con.commit()
        await ctx.send(f"Команда '{team_name}' получила {num_wins} выигрышей")
    else:
        await ctx.send(f"Команда с названием '{team_name}' не найдена")
bot.run(TOKEN)
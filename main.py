import os
import dotenv
import lightbulb
import hikari
import dataset
import asyncio
import requests, json
from xml.dom.minidom import parseString
from easygoogletranslate import EasyGoogleTranslate

dotenv.load_dotenv()

translator = EasyGoogleTranslate(source_language="jp", target_language="en", timeout=10)
db = dataset.connect("sqlite:///alerts.db")
bot = lightbulb.BotApp(os.environ["BOT_TOKEN"])
bot.d.table = db["alerts"]
bot.d.synced = db["synced_alerts"]


async def check_alerts() -> None:
    while True:
        alerts = bot.d.table.all()

        for alert in alerts:
            print(f"Searching for {alert['name']}...")
            res = requests.post(
                f"https://zenmarket.jp/fr/yahoo.aspx/getProducts?q={alert['name']}&sort=new&order=desc",
                json={"page": 1},
            )

            content = json.loads(res.json()["d"])

            for item in content["Items"]:
                if bot.d.synced.find_one(name=item["AuctionID"]):
                    print("already synced — up to date")
                    continue

                embed = hikari.Embed()
                embed.color = hikari.Color(0x09B1BA)
                embed.title = (
                    translator.translate(item["Title"]) or item["Title"] or "Unknown"
                )

                if item["AuctionID"]:
                    embed.url = (
                        "https://zenmarket.jp/fr/auction.aspx?itemCode="
                        + item["AuctionID"]
                    )

                if item["Thumbnail"]:
                    embed.set_image(item["Thumbnail"])

                if item["PriceBidOrBuyTextControl"]:
                    dom = parseString(item["PriceBidOrBuyTextControl"])
                    price = dom.getElementsByTagName("span")[0].getAttribute("data-eur")
                    embed.add_field("Instant price", price)

                if item["PriceTextControl"]:
                    dom = parseString(item["PriceTextControl"])
                    price = dom.getElementsByTagName("span")[0].getAttribute("data-eur")
                    embed.add_field("Bid price", price)

                await bot.rest.create_message(alert["channel_id"], embed=embed)
                bot.d.synced.insert({"name": item["AuctionID"]})

        print(
            f"Done checking alerts. Sleeping for {os.getenv('CHECK_INTERVAL', 60)}s..."
        )
        await asyncio.sleep(int(os.getenv("CHECK_INTERVAL", 60)))


@bot.listen()
async def on_ready(event: hikari.StartingEvent) -> None:
    print("Starting event loop...")
    asyncio.create_task(check_alerts())


@bot.command
@lightbulb.option("name", "Name of the item to register.", required=True)
@lightbulb.command(
    "register", "Register a new alert for a ZenMarket item.", pass_options=True
)
@lightbulb.implements(lightbulb.SlashCommand)
async def register(ctx: lightbulb.SlashContext, name: str) -> None:
    if any(True for _ in bot.d.table.find(name=name)):
        await ctx.respond(f"Alert for **{name}** already exists!")
        return

    bot.d.table.insert(
        {
            "user_id": ctx.author.id,
            "channel_id": ctx.channel_id,
            "name": name,
            "last_id_seen": None,
        }
    )
    await ctx.respond(f"Registered alert for **{name}**!")


@bot.command
@lightbulb.option("name", "Name of the item to delete.", required=True)
@lightbulb.command("unregister", "Delete an alert", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def unregister(ctx: lightbulb.SlashContext, name: str) -> None:
    if not bot.d.table.find_one(name=name):
        await ctx.respond(f"Alert for **{name}** does not exist!")
        return

    bot.d.table.delete(user_id=ctx.author.id, name=name)
    await ctx.respond(f"Unregistered alert for **{name}**!")


@bot.command
@lightbulb.command("alerts", "List alerts")
@lightbulb.implements(lightbulb.SlashCommand)
async def alerts(ctx: lightbulb.SlashContext) -> None:
    alerts = bot.d.table.find(user_id=ctx.author.id)
    if all(False for _ in alerts):
        await ctx.respond("You have no alerts!")
        return

    await ctx.respond("\n".join([f"{alert['name']}" for alert in alerts]) or "None")


if __name__ == "__main__":
    bot.run(
        activity=hikari.Activity(
            name="ZenMarket items", type=hikari.ActivityType.WATCHING
        )
    )

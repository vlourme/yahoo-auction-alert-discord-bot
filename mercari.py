import requests, json
from logging import info
from xml.dom.minidom import parseString
from lightbulb import BotApp
from hikari import Embed, Color


async def check_mercari(bot: BotApp, alert: dict) -> None:
    res = requests.post(
        f"https://zenmarket.jp/fr/mercari.aspx/getProducts?q={alert['name']}&sort=new&order=desc",
        json={"page": 1},
    )

    content = json.loads(res.json()["d"])

    for item in content["Items"]:
        if bot.d.synced.find_one(name=item["ItemCode"]):
            info("[mercari] already synced — up to date")
            continue

        embed = Embed()
        embed.color = Color(0x09B1BA)
        embed.title = item["ClearTitle"] or "Unknown"

        if item["ItemCode"]:
            embed.url = (
                "https://zenmarket.jp/fr/mercariproduct.aspx?itemCode="
                + item["ItemCode"]
            )

        if item["PreviewImageUrl"]:
            embed.set_image(item["PreviewImageUrl"])

        if item["PriceTextControl"]:
            dom = parseString(item["PriceTextControl"])
            price = dom.getElementsByTagName("span")[0].getAttribute("data-eur")
            embed.add_field("Price", price)

        await bot.rest.create_message(alert["channel_id"], embed=embed)
        bot.d.synced.insert({"name": item["ItemCode"]})

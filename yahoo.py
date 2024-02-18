import requests, json
from logging import info
from xml.dom.minidom import parseString
from easygoogletranslate import EasyGoogleTranslate
from lightbulb import BotApp
from hikari import Embed, Color


async def check_yahoo_auctions(
    bot: BotApp, translator: EasyGoogleTranslate, alert: dict
) -> None:
    res = requests.post(
        f"https://zenmarket.jp/en/yahoo.aspx/getProducts?q={alert['name']}&sort=new&order=desc",
        json={"page": 1},
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        },
    )

    content = json.loads(res.json()["d"])

    for item in content["Items"]:
        if bot.d.synced.find_one(name=item["AuctionID"]):
            info("[yahoo] already synced — up to date")
            continue

        embed = Embed()
        embed.color = Color(0x09B1BA)
        embed.title = translator.translate(item["Title"]) or item["Title"] or "Unknown"

        if item["AuctionID"]:
            embed.url = (
                "https://zenmarket.jp/fr/auction.aspx?itemCode=" + item["AuctionID"]
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

        embed.set_footer(f"Source: Yahoo Auction — #{item['AuctionID']}")

        await bot.rest.create_message(alert["channel_id"], embed=embed)
        bot.d.synced.insert({"name": item["AuctionID"]})

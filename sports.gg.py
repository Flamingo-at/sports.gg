import asyncio
import aiohttp

from re import findall
from web3.auto import w3
from loguru import logger
from aiohttp import ClientSession
from random import choice, randint
from aiohttp_proxy import ProxyConnector


def random_tor_proxy():
    proxy_auth = str(randint(1, 0x7fffffff)) + ':' + str(randint(1, 0x7fffffff))
    proxies = f'socks5://{proxy_auth}@localhost:' + str(choice(tor_ports))
    return(proxies)


async def get_connector():
    connector = ProxyConnector.from_url(random_tor_proxy())
    return(connector)


async def create_email(client: ClientSession):
    try:
        response = await client.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
        email = (await response.json())[0]
        return email
    except:
        logger.error("Failed to create email")
        await asyncio.sleep(1)
        return await create_email(client)


async def check_email(client: ClientSession, login: str, domain: str, count: int):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=getMessages&'
                                    f'login={login}&domain={domain}')
        email_id = (await response.json())[0]['id']
        return email_id
    except:
        while count < 15:
            count += 1
            await asyncio.sleep(1)
            return await check_email(client, login, domain, count)
        logger.error('Emails not found')
        raise Exception()


async def get_code(client: ClientSession, login: str, domain: str, email_id):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=readMessage&'
                                    f'login={login}&domain={domain}&id={email_id}')
        data = (await response.json())['body']
        code = findall(r"Your verification code: (\d{6})", data)[0]
        return code
    except:
        logger.error('Failed to get code')
        raise Exception()


def create_wallet():
    account = w3.eth.account.create()
    return(str(account.address), str(account.privateKey.hex()))


async def worker():
    while True:
        try:
            async with aiohttp.ClientSession(connector = await get_connector()) as client:

                logger.info('Create email')
                email = await create_email(client)

                logger.info('Sending email')
                response = await client.get(
                    f'https://api.sports.gg/v1/auth/otp-code?email={email}')
                if 'OK' not in await response.text():
                	raise Exception()

                logger.info('Check email')
                email_id = await check_email(client, email.split('@')[0], email.split('@')[1], 0)

                logger.info('Get code')
                code = await get_code(client, email.split('@')[0], email.split('@')[1], email_id)

                logger.info('Confirm email')
                response = await client.get(
                    f'https://api.sports.gg/v1/auth/token?email={email}&code={code}')              
                token = (await response.json())['access']['token']

                logger.info('Add ref')
                response = await client.patch('https://api.sports.gg/v1/user/me',
                                          json={
                                              "referrer": ref
                                          }, headers={'authorization': 'Bearer ' + token})
                if 'OK' not in await response.text():
                	raise Exception()

                address, private_key = create_wallet()

                logger.info('Add wallet')
                response = await client.patch('https://api.sports.gg/v1/user/me',
                                          json={
                                              "wallet": address
                                          }, headers={'authorization': 'Bearer ' + token})
                if 'OK' not in await response.text():
                	raise Exception()

        except:
            logger.error('Error\n')
        else:
            with open('registered.txt', 'a', encoding='utf-8') as f:
                f.write(f'{email}:{address}:{private_key}\n')
            logger.success('Successfully\n')

        await asyncio.sleep(delay)


async def main():
    tasks = [asyncio.create_task(worker()) for _ in range(int(1))]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    tor_ports = [9150]

    print("Bot sports.gg @flamingoat\n")
    
    ref = input('Ref code: ')
    delay = int(input('Delay(sec): '))

    asyncio.run(main())

import logging
import random
from threading import Semaphore
from selenium.webdriver.chrome.options import Options
from .models import Clicker, AccountLog
from apps.seleniumCore import Selenium
from selenium import webdriver
from django.utils import timezone
from django.db.models import F
from django.db import transaction
import time
import zipfile

logger = logging.getLogger(__name__)
max_open_browsers = 16
browser_semaphore = Semaphore(max_open_browsers)

proxies = [
    {"host": "38.152.246.58", "port": "9709", "user": "NvuvDZ", "pass": "L2p8Ad"},
    {"host": "213.226.78.43", "port": "8000", "user": "LDRxSP", "pass": "5sGbyN"},
    # Добавьте другие прокси
]

def get_random_proxy():
    return random.choice(proxies)

def configure_selenium_with_proxy(proxy):
    chrome_options = Options()

    manifest_json = f"""
    {{
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"
        ],
        "background": {{
            "scripts": ["background.js"]
        }},
        "minimum_chrome_version":"22.0.0"
    }}
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{proxy['host']}",
                port: parseInt({proxy['port']})
            }},
            bypassList: ["localhost"]
            }}
        }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy['user']}",
                password: "{proxy['pass']}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """

    pluginfile = 'proxy_auth_plugin.zip'
    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    chrome_options.add_extension(pluginfile)

    selenium = Selenium()
    selenium.driver = webdriver.Chrome(options=chrome_options)
    return selenium

def check_and_process_clicker_for_account(account):
    logger.info(f'Запуск обработки кликеров для аккаунта: {account.number}')
    with browser_semaphore:
        clickers = Clicker.objects.filter(status='pending').exclude(completed_count=F('count')).select_for_update()

        proxy = get_random_proxy()
        selenium = configure_selenium_with_proxy(proxy)

        try:
            selenium.open("https://www.wildberries.ru")

            selenium.add_cookies(account.cookies)
            selenium.set_token(account.token)
            processed_urls = AccountLog.objects.filter(account=account).values_list('url', flat=True)
            account_clickers = clickers.exclude(url__in=processed_urls)[:5]

            if not account_clickers:
                logger.info(f'Для аккаунта {account.number} нет новых кликеров')
                return

            for clicker in account_clickers:
                logger.info(f'Аккаунт {account.number} переходит по ссылке {clicker.url}')

                # Обновляем куки перед каждым переходом
                process_clicker(selenium, account, clicker)
                completed_count  = clicker.completed_count + 1
                clicker.completed_count = completed_count
                clicker.save()

                if clicker.completed_count >= clicker.count:
                    clicker.status = 'completed'
                    clicker.save()

                time.sleep(random.randint(5, 10))

        except Exception as e:
            logger.error(f'Ошибка обработки аккаунта {account.number}: {e}')
        finally:
            selenium.driver.quit()

        logger.info(f'Завершение обработки кликеров для аккаунта {account.number}')

def process_clicker(selenium, account, clicker):
    from .models import AccountLog

    try:
        # Обновляем куки перед каждым переходом
        selenium.add_cookies(account.cookies)
        selenium.open(clicker.url)

        time.sleep(random.randint(3, 7))

        smooth_scroll(selenium, duration=5)

        if selenium.has_elements("body"):
            AccountLog.objects.create(account=account, url=clicker.url, date=timezone.now())
            logger.info(f'Аккаунт {account.number} успешно прошел по ссылке {clicker.url}')
        else:
            logger.warning(f'Аккаунт {account.number} не смог пройти по ссылке {clicker.url}')

    except Exception as e:
        logger.error(f"Ошибка при обработке кликера {clicker.url} для аккаунта {account.number}: {e}")


# Функция плавного скроллинга страницы до конца
def smooth_scroll(selenium, duration=2):
    try:
        scroll_script = """
        const scrollToBottom = () => {
            let distance = 100;
            let delay = 20;
            let timer = setInterval(() => {
                window.scrollBy(0, distance);
                if ((window.innerHeight + window.scrollY) >= document.body.scrollHeight) {
                    clearInterval(timer);
                }
            }, delay);
        };
        scrollToBottom();
        """
        selenium.driver.execute_script(scroll_script)
        time.sleep(duration)

    except Exception as e:
        logger.error(f"Ошибка при плавном скроллинге: {e}")

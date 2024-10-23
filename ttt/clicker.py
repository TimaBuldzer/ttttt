import logging
import random
from threading import Semaphore
from selenium.webdriver.chrome.options import Options
from .models import Clicker, AccountLog
from apps.seleniumCore import Selenium
from selenium import webdriver
from django.utils import timezone
from django.db.models import F
import time
import zipfile

logger = logging.getLogger(__name__)
max_open_browsers = 16
browser_semaphore = Semaphore(max_open_browsers)

proxies = [
    {"host": "78.153.151.198", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "138.124.186.154", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.150.9", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.150.138", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.151.128", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "80.66.72.95", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.151.69", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.150.222", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.151.84", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "78.153.150.50", "port": "8000", "user": "ceLYFS", "pass": "EhJgu7"},
    {"host": "193.233.127.134", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.55", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.127.202", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.244", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.150", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.127.139", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.50", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.238", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "193.233.126.38", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"},
    {"host": "46.161.21.32", "port": "8000", "user": "sQtoD0", "pass": "JZE4CJ"}
]


def get_random_proxy():
    return random.choice(proxies)

def configure_selenium_with_proxy(proxy):
    chrome_options = Options()

    # Включение headless режима
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Проверка данных прокси перед использованием
    if not isinstance(proxy, dict):
        logger.error(f"Неверный формат данных прокси: {proxy}")
        raise ValueError("Ожидался словарь для прокси данных")
    
    logger.info(f"Используем прокси: {proxy}")
    
    # Создание расширения для прокси
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

    # Создание экземпляра Selenium с headless режимом
    selenium = Selenium()
    selenium.driver = webdriver.Chrome(options=chrome_options)
    return selenium

def check_and_process_clicker_for_account(account):
    logger.info(f'Запуск обработки кликеров для аккаунта: {account.number}')
    
    with browser_semaphore:
        clickers = Clicker.objects.filter(status='pending').exclude(completed_count=F('count')).select_for_update()
        proxy = get_random_proxy()
        
        # Проверяем корректность данных аккаунта перед использованием
        if not isinstance(account, dict) and not hasattr(account, 'cookies'):
            logger.error(f"Неверные данные аккаунта: {account}")
            raise ValueError("Ожидался объект с куки")

        # Логируем данные перед запуском Selenium
        logger.info(f"Прокси: {proxy}, Куки: {account.cookies}")
        
        selenium = configure_selenium_with_proxy(proxy)

        try:
            processed_urls = AccountLog.objects.filter(account=account).values_list('url', flat=True)
            account_clickers = clickers.exclude(url__in=processed_urls)[:5]

            if not account_clickers:
                logger.info(f'Для аккаунта {account.number} нет новых кликеров')
                return

            for clicker in account_clickers:
                logger.info(f'Аккаунт {account.number} переходит по ссылке {clicker.url}')

                # Открываем нужную страницу (товар/целевая ссылка)
                selenium.open(clicker.url)

                # Добавляем куки и токен после открытия страницы
                selenium.add_cookies(account.cookies)
                selenium.set_token(account.token)

                # Перезагружаем страницу, чтобы куки и токен применились
                selenium.driver.refresh()

                # Переход по ссылке и обработка кликера
                process_clicker(selenium, account, clicker)
                
                clicker.completed_count += 1
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
        # Переход по ссылке (с учетом ранее добавленных куков)
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

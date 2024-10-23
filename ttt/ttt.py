def add_cookies(self, cookies: typing.List[dict]):
    """
    Добавляет куки в браузер.
    """
    for cookie in cookies:
        # Проверяем, что cookie действительно является словарём
        if not isinstance(cookie, dict):
            logger.error(f"Неверный формат кука: {cookie}, ожидается словарь")
            continue

        try:
            selenium_cookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', False),
                'httpOnly': cookie.get('httpOnly', False),
            }

            # Удаляем ключ 'domain', если он присутствует, чтобы избежать проблем с соответствием домена
            selenium_cookie.pop('domain', None)

            # Добавляем куки в браузер через Selenium
            self.driver.add_cookie(selenium_cookie)

        except KeyError as e:
            # Логируем ошибку, если в куке отсутствует какой-то обязательный ключ ('name' или 'value')
            logger.error(f"Ошибка: отсутствует обязательный ключ {e} в куке {cookie}")
        except Exception as e:
            # Логируем любую другую ошибку
            logger.error(f"Ошибка при добавлении кука {cookie}: {e}")

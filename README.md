# INCY Direct rules

[![Build and publish](https://github.com/Poliklot/incy-direct-rules/actions/workflows/build.yml/badge.svg)](https://github.com/Poliklot/incy-direct-rules/actions/workflows/build.yml)

Личный открытый список Direct-исключений для INCY. Домены хранятся по блокам с комментариями, а GitHub Actions проверяет их и собирает профиль маршрутизации.

**[Подключить профиль и посмотреть блоки](https://poliklot.github.io/incy-direct-rules/)** · **[Редактировать списки](rules/direct/)** · **[Статус сборки](https://github.com/Poliklot/incy-direct-rules/actions)**

## Подключение к INCY

1. Сохрани или экспортируй текущий профиль маршрутизации, чтобы было легко вернуться назад.
2. Открой [страницу подключения](https://poliklot.github.io/incy-direct-rules/) и нажми **«Добавить профиль в INCY»**. Если кнопка не работает, скопируй полную ссылку ниже и импортируй её из буфера обмена в разделе профилей маршрутизации:

   ```text
   incy://autorouting/add/https://poliklot.github.io/incy-direct-rules/profile.json
   ```

3. В INCY появится отдельный профиль **Poliklot Direct** с источником обновлений. Импорт использует `add`, а не `onadd`: он **не активирует профиль автоматически**.
4. Сравни DNS и прочие настройки с текущим профилем. Если всё подходит, выбери новый профиль и переподключи VPN.

**Это целый профиль, а не дополнение к существующему Direct.** Он не объединяет правила текущего профиля и не содержит серверов или VPN-подписки. У профилей с одинаковым `Name` INCY обновляет существующую запись: не используй это имя для другого профиля.

Autorouting привязывает профиль к URL и обновляет его по интервалу. По документации INCY, интервал по умолчанию — 24 часа; проверка готовности обновления выполняется каждые 30 минут. Для немедленного применения изменений используй **«Обновить сейчас»** в секции **«Источник обновлений»** и затем переподключи VPN. Обычный `routing/add` не обеспечивает автообновление.

## Что делает профиль

| Настройка | Поведение |
| --- | --- |
| Домены из `rules/direct/*.txt` | Direct: напрямую, без прокси |
| Прочий трафик | Proxy (`GlobalProxy: "true"`) |
| DNS для Proxy | Cloudflare DoH: `https://cloudflare-dns.com/dns-query` |
| DNS для Direct | Google DoH: `https://dns.google/dns-query` |
| IP-исключения и блокировки | Не добавляются |
| Стратегия доменов | `AsIs` |
| FakeDNS профиля | Выключен (`"false"`); системный режим VPN DNS настраивается отдельно в INCY |

Это базовые настройки нового профиля, **не экспорт твоих текущих настроек**. Они явно записаны в [`profile.base.json`](profile.base.json). При необходимости меняй DNS там, а не в редакторе удалённого профиля INCY: следующая синхронизация может перезаписать локальные изменения. Настройки туннеля и системный обход LAN остаются вне этого репозитория.

В стартовом списке **42 уникальных домена в 9 блоках**. Убраны только точные повторы `alfabank.ru`, `github.com`, `api.github.com`. Поддомены оставлены явно, даже если уже покрываются родительским доменом: это сохраняет пояснения и историю требований. Написание `hightesst.ru`, `yastatic-net.ru` и `goloom.strm.yandex.net` не исправлялось автоматически.

Не добавляются `.ru`, географические категории, все IP страны, весь `apple.com`, весь `mail.ru` или другие широкие исключения сверх предоставленного списка.

## Блоки и комментарии

| Файл | Назначение |
| --- | --- |
| [`banks-telecom.txt`](rules/direct/banks-telecom.txt) | Банки и связь |
| [`work-tools.txt`](rules/direct/work-tools.txt) | Bitrix24, Kaiten, Yonote |
| [`hosting-projects.txt`](rules/direct/hosting-projects.txt) | Хостинг и отдельные сайты |
| [`github.txt`](rules/direct/github.txt) | GitHub, API, ресурсы, загрузки и Pages |
| [`development.txt`](rules/direct/development.txt) | Godot и npm registry |
| [`hugging-face.txt`](rules/direct/hugging-face.txt) | Hugging Face и конкретный CDN |
| [`apple.txt`](rules/direct/apple.txt) | Отдельные сервисы Apple |
| [`yandex.txt`](rules/direct/yandex.txt) | Яндекс и ресурсы |
| [`vk-avito.txt`](rules/direct/vk-avito.txt) | VK, Mail и Авито |

Пример файла:

```text
# Название блока
# Описание: почему эти ресурсы должны идти напрямую.
example.com  # Сайт вместе с поддоменами
domain:example.net  # Явная запись с тем же поведением
full:api.example.org  # Только это точное имя
```

- Одна запись на строку. Первая непустая строка — `# Название блока`.
- Комментарии отдельными строками описывают блок; комментарий после домена объясняет конкретную запись.
- Обычный домен собирается в `domain:example.com`: совпадают домен и его поддомены, **не** `notexample.com` или `example.com.evil.org`.
- `full:` ограничивает правило точным именем. `domain:` можно написать явно.
- Только DNS-домены. Без `https://`, пути, порта, IP, `*`, `regexp`, `keyword` и `geosite`. Международные домены записывай в punycode (`xn--...`).
- Точный дубль после нормализации регистра и `domain:` останавливает сборку с указанием обоих файлов и строк. Некорректные записи и пустые блоки тоже останавливают сборку.

**«Модули» здесь — файлы исходных списков.** INCY получает плоский `DirectSites`; блоки и комментарии доступны в репозитории и на странице подключения, не обещаются в интерфейсе самого приложения.

### Самый простой способ изменить список

1. На странице подключения раскрой блок и нажми **«Редактировать этот блок на GitHub»** — или открой его файл в репозитории и нажми значок карандаша.
2. Добавь, удали или прокомментируй строки.
3. Сохрани изменение в `main` либо через pull request. Новый блок создаётся как новый `rules/direct/короткое-имя.txt`; регистрировать его нигде не надо.
4. Дождись зелёного **Build and publish INCY Direct** в Actions.
5. Обнови профиль в INCY.

Откат: переключись на сохранённый старый профиль в INCY. Для отката опубликованного списка восстанови нужные строки обычным новым коммитом в `main` и дождись сборки; переписывать Git-историю не требуется.

## Сборка и публикация

Python 3.10+ и стандартная библиотека: без npm, pip-зависимостей, ручной сборки `.dat` или внешних списков.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py --updated-at "$(git show -s --format=%ct HEAD)" --revision "$(git rev-parse HEAD)"
```

В Actions используется Python 3.12. Проверки выполняются для pull requests, push в `main` и ручного запуска. **Публикуется только `main`, после успешных тестов и сборки**. SHA actions закреплены; checkout не сохраняет credentials. У build только `contents: read`, у deploy только `pages: write` и `id-token: write`. Секреты и PAT не нужны. Workflow ничего не коммитит и не пушит. Публикации одной ветки выполняются последовательно.

GitHub Pages должен быть настроен: **Settings → Pages → Build and deployment → Source → GitHub Actions**. Workflow публикует только содержимое `dist/`, не исходники, `.git` или локальные файлы. PR не получает разрешений на публикацию. Ошибка проверки не заменяет предыдущий опубликованный профиль.

| Публикуемый файл | Назначение |
| --- | --- |
| [`profile.json`](https://poliklot.github.io/incy-direct-rules/profile.json) | Профиль INCY для Autorouting |
| [`direct.txt`](https://poliklot.github.io/incy-direct-rules/direct.txt) | Плоский нормализованный список, не профиль INCY |
| [`profile.json.sha256`](https://poliklot.github.io/incy-direct-rules/profile.json.sha256) | SHA-256 байтов профиля |
| [`build.json`](https://poliklot.github.io/incy-direct-rules/build.json) | Commit SHA, timestamp, количество блоков/правил и хеш |
| [`index.html`](https://poliklot.github.io/incy-direct-rules/) | Подключение, блоки, комментарии и ссылки редактирования |

`LastUpdated` берётся из времени исходного коммита, а не времени запуска workflow: повторная сборка того же исходника даёт одинаковые байты. `dist/` не хранится в Git. Для локального предпросмотра без коммита можно передать текущий положительный Unix timestamp без `--revision`: receipt будет помечен `local`.

## Приватность и ограничения

- Репозиторий и страница публичные: список доменов и комментарии видны всем. Не добавляй VPN-ключи, ссылки на подписку, credentials, секреты и закрытые клиентские данные.
- Direct — сознательный обход VPN. Сайты видят твой исходный IP; это не список анонимности, доступности или доверенных ресурсов.
- `github.io` и `githubusercontent.com` включают пользовательские сайты/контент; широкие правила сохранены из исходного списка, а не рекомендованы всем.
- DNS-серверы тоже являются внешними сервисами. Согласуй выбор с собственными требованиями к приватности.
- Совместимость формата основана на официальной документации; импорт и реальную маршрутизацию нужно проверить на своей установленной версии INCY. Сборщик не проверяет доступность доменов и не угадывает дополнительные CDN.
- Неофициальный проект, не связан с командой INCY. Лицензия — [MIT](LICENSE).

## Источники формата

- [INCY Routing](https://docs.incy.cc/routing/) — структура профиля, `DirectSites`, DNS и строковые flags.
- [INCY Autorouting](https://docs.incy.cc/autorouting/) — `add`, `onadd`, URL-источник и автообновление.
- [Xray Routing](https://xtls.github.io/en/config/routing.html#ruleobject) — различие `domain:` и `full:`.
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — публикация артефакта через Actions.

# Poliklot Direct: модули для INCY

[![Build and publish](https://github.com/Poliklot/incy-direct-rules/actions/workflows/build.yml/badge.svg)](https://github.com/Poliklot/incy-direct-rules/actions/workflows/build.yml)

Direct-правила по сервисам: **43 доменные записи в 9 независимых модулях**, с комментариями и публичной сборкой через GitHub Actions. Это личный открытый набор, не универсальная рекомендация для всех пользователей.

**[Выбрать модули](https://poliklot.github.io/incy-direct-rules/)** · **[Исходные блоки](rules/direct/)** · **[GitHub Actions](https://github.com/Poliklot/incy-direct-rules/actions)**

## Как устроено

- Публичный репозиторий содержит только общие доменные правила и комментарии.
- Actions проверяет их, собирает стандартные `.module` и публикует на GitHub Pages.
- INCY подключает модули отдельно от профиля маршрутизации. Ваш профиль, личные IP, DNS и VPN-подписки остаются на устройстве.
- Сборщик **вообще не читает личные профили**. Личные IP не передаются в Actions, не хранятся в GitHub Secrets и не попадают в артефакты.

Модуль содержит только `[Rule]` и правила `DIRECT`. Без DNS, IP-исключений, скриптов, MITM, установки сертификатов, подмены контента и широких географических категорий.

## Подключение

1. Сохраните или экспортируйте рабочий профиль маршрутизации. Оставьте его выбранным в INCY.
2. На [странице модулей](https://poliklot.github.io/incy-direct-rules/) выберите нужные блоки. Кнопка **«Добавить и включить»** использует `incy://module/onadd/{url}` и включает модуль — это намеренное добавление Direct-исключений, а не импорт нового профиля.
3. Если кнопка не работает, скопируйте URL файла и откройте **Туннель → Модули → Добавить**, вставьте URL и нажмите **«Импорт»**. Проверьте статус модуля, затем переподключите VPN.
4. После изменения правил дождитесь зелёного Actions и обновите модуль из его источника в INCY. Автообновление по расписанию зависит от версии клиента и **не считается подтверждённым** этой сборкой.

Каждый блок включается и выключается отдельно. Есть и [общий модуль](https://poliklot.github.io/incy-direct-rules/modules/all.module) со всеми записями: используйте **его либо отдельные блоки**, чтобы не дублировать правила. В общем наборе есть конкретные рабочие порталы и сайты из исходного списка — подключайте его только после просмотра содержимого.

### Личные исключения

Личные серверные IP держите только в своём профиле INCY или локальном модуле без публичного источника. Их не нужно включать в общественную сборку. Публичный модуль не заменяет профиль и не требует удаления личных IP.

Если домены уже есть в Direct рабочего профиля, сначала можно оставить их там: новые модули будут дублировать исключения. После проверки при желании удалите только перенесённые доменные записи — **не личные IP и не другие настройки**. Применение и приоритет конфликтующих правил других модулей необходимо проверить на своей версии приложения.

Откат: выключите добавленные модули и переподключите VPN. Исходный профиль остаётся на месте.

### Переход со старой версии проекта

Раньше проект публиковал полный `profile.json` для Autorouting. Этот способ подключения **снят с публикации**: новая сборка удаляет старый JSON и публикует только модули. Уже скачанный профиль сам от этого не становится личным или объединённым.

Если вы импортировали старый **Poliklot Direct**, вернитесь к своему сохранённому профилю и подключите модули отдельно. У старого импортированного профиля можно отвязать источник обновлений; не используйте прежний URL для установки проекта. Никакого массового изменения настроек приложения workflow не выполняет.

## Блоки

| Исходный файл | Назначение | Модуль |
| --- | --- | --- |
| [banks-telecom.txt](rules/direct/banks-telecom.txt) | Банки и связь | [banks-telecom.module](https://poliklot.github.io/incy-direct-rules/modules/banks-telecom.module) |
| [work-tools.txt](rules/direct/work-tools.txt) | Bitrix24, Kaiten, Yonote | [work-tools.module](https://poliklot.github.io/incy-direct-rules/modules/work-tools.module) |
| [hosting-projects.txt](rules/direct/hosting-projects.txt) | Хостинг и отдельные сайты | [hosting-projects.module](https://poliklot.github.io/incy-direct-rules/modules/hosting-projects.module) |
| [github.txt](rules/direct/github.txt) | GitHub и загрузки | [github.module](https://poliklot.github.io/incy-direct-rules/modules/github.module) |
| [development.txt](rules/direct/development.txt) | Godot и npm registry | [development.module](https://poliklot.github.io/incy-direct-rules/modules/development.module) |
| [hugging-face.txt](rules/direct/hugging-face.txt) | Hugging Face и CDN | [hugging-face.module](https://poliklot.github.io/incy-direct-rules/modules/hugging-face.module) |
| [apple.txt](rules/direct/apple.txt) | Отдельные сервисы Apple | [apple.module](https://poliklot.github.io/incy-direct-rules/modules/apple.module) |
| [yandex.txt](rules/direct/yandex.txt) | Яндекс и ресурсы | [yandex.module](https://poliklot.github.io/incy-direct-rules/modules/yandex.module) |
| [vk-avito.txt](rules/direct/vk-avito.txt) | VK, Mail, RuStore и Авито | [vk-avito.module](https://poliklot.github.io/incy-direct-rules/modules/vk-avito.module) |

Написание `hightesst.ru`, `yastatic-net.ru`, `goloom.strm.yandex.net` сохранено. Явно перечисленные поддомены тоже сохранены. Из первоначальных 45 строк убраны только повторы `alfabank.ru`, `github.com`, `api.github.com`.

## Редактирование

Откройте файл блока на GitHub, нажмите карандаш и добавьте домены с объяснениями:

```text
# Название блока
# Почему эти ресурсы должны идти напрямую.
example.com  # Домен и его поддомены
full:api.example.org  # Только точное имя
```

- Один домен на строку, первая непустая строка — `# Название блока`.
- Комментарии блока и конкретных записей попадут в `.module` и на страницу подключения. В файле модуля комментарии ставятся на отдельные строки.
- Новый блок — новый `rules/direct/короткое-имя.txt` в lowercase-kebab-case. Нигде не нужно регистрировать его; имя `all` зарезервировано.
- Сохраните изменение в `main` или через pull request. Actions выполнит проверки и сборку; при ошибке предыдущая публикация остаётся доступной.
- Дубль результирующего правила без учёта регистра останавливает сборку с указанием файлов и строк. `example.com` и `domain:example.com` теперь эквивалентны; `full:example.com` — отдельное точное правило.
- Допускаются DNS-домены и punycode. URL, IP, CIDR, wildcard, regex, keyword и geosite не принимаются. Личные данные нельзя добавлять даже в комментарии.

### Семантика нового формата

| Исходная запись | Правило `.module` | Сопоставление |
| --- | --- | --- |
| `example.com` | `DOMAIN-SUFFIX,example.com,DIRECT` | Домен и поддомены |
| `domain:example.com` | `DOMAIN-SUFFIX,example.com,DIRECT` | Домен и поддомены |
| `full:example.com` | `DOMAIN,example.com,DIRECT` | Точное имя |

Это явная семантика **новых модулей**, а не обещание побайтовой или поведенческой идентичности старому `DirectSites`. Сборщик не меняет написание или регистр доменов. Он не создаёт подстрочных Direct-правил `DOMAIN-KEYWORD`, поддержку которых в INCY не проверяли.

## Сборка

Python 3.10+ и стандартная библиотека, без npm/pip, собственного сервера или сборки `.dat`:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py --updated-at "$(git show -s --format=%ct HEAD)" --revision "$(git rev-parse HEAD)"
actionlint
git diff --check
```

Для локально изменённых исходников используйте текущий положительный Unix timestamp без `--revision`: версия будет `local`, а не SHA старого коммита.

`dist/` — управляемая временная папка, не хранится в Git. Сборка сначала проверяет все входные данные и пишет новую папку, затем заменяет предыдущий результат целиком: удалённые блоки и прежний `profile.json` не остаются в публикации. Произвольные непустые папки и исходники заменять нельзя. Пользовательский `--output` должен быть новой/пустой папкой или результатом предыдущей сборки этого сборщика.

| Файл | Назначение |
| --- | --- |
| `modules/<блок>.module` | Отдельный модуль |
| `modules/all.module` | Объединение всех блоков |
| `modules/*.module.sha256` | SHA-256 точных байтов модуля |
| `build.json` | SHA исходников, timestamp, количества и хеши модулей |
| `direct.txt` | Исходные доменные записи без комментариев, не файл для импорта |
| `index.html` | Каталог, поиск, ссылки подключения, копирование URL и пояснения |

Проверки запускаются на pull requests, push в `main` и вручную. Публикуется только `main`, после успешных тестов и сборки. Actions закреплены по SHA; checkout не сохраняет credentials. Build имеет только `contents: read`, deploy — `pages: write` и `id-token: write`. Секреты и PAT не нужны; workflow ничего не коммитит и не пушит. Публикации выполняются последовательно.

Pages: **Settings → Pages → Source → GitHub Actions**. Повторная сборка одного SHA и timestamp даёт одинаковые файлы. Время на странице показывается в МСК, данные сборки используют Unix timestamp.

## Приватность и совместимость

- Репозиторий, комментарии и файлы Pages публичные. Никогда не добавляйте личные серверные IP, ключи, subscriptions, credentials или закрытые клиентские данные. Public DNS домена всё равно может раскрывать адрес его сервера; этот проект не скрывает DNS.
- Direct сознательно обходит VPN: сайты видят ваш исходный IP. Это не список анонимности или доверенных ресурсов.
- `github.io` и `githubusercontent.com` включают пользовательский контент; широкие доменные записи сохранены из исходного списка, а не рекомендованы всем.
- В установленном INCY **2.6.2 на macOS (Apple-версия)** проверены импорт `.module` по URL, метаданные, источник и ручное обновление на одном правиле для зарезервированного `validation.invalid`. Тестовый модуль оставлен выключенным, рабочий профиль не менялся. Интерфейс также заявляет поддержку `.sgmodule`. Это не проверка реального сетевого трафика и не гарантия всех версий/платформ; scheduled автообновление пока не подтверждено.
- Неофициальный проект, не связан с разработчиками INCY. Лицензия [MIT](LICENSE).

## Источники

- [INCY](https://github.com/INCY-DEV/incy-platforms) — официальный проект, версии и платформы.
- [INCY Routing](https://docs.incy.cc/routing/) и [Autorouting](https://docs.incy.cc/autorouting/) — профили маршрутизации; не путать с модулями.
- [Surge Module](https://manual.nssurge.com/profile/module.html) — стандартный формат `.sgmodule`.
- [Surge Rules](https://manual.nssurge.com/rules/domain.html) — `DOMAIN` и `DOMAIN-SUFFIX`.
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — публикация через Actions.

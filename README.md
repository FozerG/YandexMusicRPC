# **<img src="./assets/YMRPC_ico.ico" alt="[DISCORD RPC]" width="30"/> &nbsp;Yandex Music Discord Rich Presence**
[![TotalDownloads](https://img.shields.io/github/downloads/FozerG/YandexMusicRPC/total)](https://github.com/FozerG/YandexMusicRPC/releases "Download") [![LastRelease](https://img.shields.io/github/v/release/FozerG/YandexMusicRPC)](https://github.com/FozerG/YandexMusicRPC/releases "Download") [![CodeOpen](https://img.shields.io/github/languages/top/FozerG/YandexMusicRPC)](https://github.com/FozerG/YandexMusicRPC/blob/main/main.py "Show code") [![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/FozerG/YandexMusicRPC/releases "Download")

> [!WARNING]
> Репозиторий переведён в режим **read-only** и больше не поддерживается. Его функциональность объединена с [WinYandexMusicRPC](https://github.com/FozerG/WinYandexMusicRPC).
>
> Для скачивания актуальной версии используйте [релизы WinYandexMusicRPC](https://github.com/FozerG/WinYandexMusicRPC/releases).

<details>
<summary>Архивная документация YandexMusicRPC</summary>

**Discord RPC для показа текущего трека играющего в Яндекс Музыке с любого устройства.**  

<img src="https://github.com/user-attachments/assets/11d3b758-d211-4645-ab30-4e2f4393a5ab" alt="discord" width="340">

Этот проект представляет собой форк [WinYandexMusicRPC](https://github.com/FozerG/WinYandexMusicRPC), но с совершенно иной концепцией работы. Скрипт получает данные о текущем воспроизводимом треке, статусе паузы и позиции трека напрямую через серверы Яндекса. Это первый в своем роде скрипт, который поддерживает «Моя волна» и способен отображать музыку в статусе даже при воспроизведении на других устройствах, таких как Mac, iPhone или Android.

Однако, существуют некоторые ограничения:

- Для работы требуется авторизация в аккаунте Яндекса (войти можно через настройки программы).
- Это всё ещё **недостаточно стабильно**, многое зависит от Яндекса, и в любой момент всё может сломаться.
- Необходимо использовать совместимые версии приложения Яндекс.Музыка для каждого из устройств.
  - iOS : >= 6.97
  - Android : >= 2024.11.2
  - Widnows : >= 5.82.0 [(Только новое приложение)](https://music.yandex.ru/download/)
  - macOS : >= 5.82.0
  - Браузер : В ближайшее время заработает полноценно. Возможно, уже сейчас функционирует.

## Требования для запуска скрипта
Скрипт предназначен для работы исключительно в средах Windows 10 и Windows 11. Однако, при внесении соответствующих изменений в код, его можно адаптировать для других операционных систем. На данный момент я не имею возможности выполнить портирование.

Если вы не будете использовать ехе файл то:
1. Python <3.14, >=3.10

## Как скачать и использовать Exe?
1. Скачиваем [актуальную версию WinYandexMusicRPC](https://github.com/FozerG/WinYandexMusicRPC/releases).
  
2. Открываем YandexMusicRPC

3. После запуска скрипта щёлкните правой кнопкой мыши на его значок в системном трее и выполните вход в аккаунт Яндекса. Затем откройте окно скрипта, чтобы убедиться, что он работает корректно.

## Как использовать main.py?

1. Открываем терминал и идем в папку где находится файл `requirements.txt`.
2. Пишем `pip install -r requirements.txt` для того что бы установить зависимости.
3. В терминал пишем `python main.py`

>Чтобы скомпилировать скрипт с помощью [Pyinstaller](https://pypi.org/project/pyinstaller/), выполните данную команду:  
`pyinstaller --noconfirm main.spec`

------------
## Баги
Баги всегда существуют, но сначала их надо найти 🫡  
Если вы нашли ошибку, то не стесняйтесь сообщать о ней в [Issues](https://github.com/FozerG/YandexMusicRPC/issues)

------------
Пожалуйста, покажите вашу заинтересованность в этом проекте, что бы я мог его обновлять по мере возможности.

>Код не идеален, так как Python не является моим основным языком, и скрипт писался для личного использования. Однако он может стать основой для ваших собственных скриптов.

>За основу был взят код [WinYandexMusicRPC](https://github.com/FozerG/WinYandexMusicRPC)  
>Используется [Yandex Music API](https://github.com/MarshalX/yandex-music-api)   

</details>

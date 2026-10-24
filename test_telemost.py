
import asyncio
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import (
    Frame,
    Page,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# ============================================================
# CONFIGURATION
# ============================================================

# Ссылка на существующую конференцию
MEETING_URL = "https://telemost.yandex.ru/j/14551457830291"

# Имя участника
AGENT_NAME = "Ебень Обыкновенный"

# Playwright Server из Docker Compose
BROWSER_WS_URL = "ws://localhost:3000/ws/replace-with-long-random-secret"

# Docker Compose
PROJECT_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = "docker-compose.yml"
BROWSER_SERVICE = "meeting-browser"

# Audio
AUDIO_SOURCE = "meeting_output.monitor"
RECORD_SECONDS = 60
SAMPLE_RATE = 16000
CHANNELS = 1

# Timing
JOIN_TIMEOUT_SECONDS = 90

# Output
OUTPUT_DIR = PROJECT_ROOT / "data" / "recordings"
DEBUG_SCREENSHOT = OUTPUT_DIR / "telemost_debug.png"


# ============================================================
# BROWSER HELPERS
# ============================================================


def get_entry_frame(page: Page) -> Frame | None:
    """Найти iframe подключения к Телемосту."""
    for frame in page.frames:
        if "/private-join/" in frame.url and not frame.is_detached():
            return frame
    return None


async def has_guest_form(page: Page) -> bool:
    """Проверить, отображается ли форма гостевого входа."""
    frame = get_entry_frame(page)
    root = frame or page

    fields = root.locator(
        'input[data-testid="orb-textinput-input"][type="text"]'
    )

    for i in range(await fields.count()):
        if await fields.nth(i).is_visible():
            return True

    return False


async def fill_guest_name(page: Page) -> bool:
    """Заполнить имя гостя через стабильный data-testid."""
    frame = get_entry_frame(page)
    root = frame or page

    fields = root.locator(
        'input[data-testid="orb-textinput-input"][type="text"]'
    )

    for i in range(await fields.count()):
        field = fields.nth(i)

        if not await field.is_visible():
            continue

        current_value = await field.input_value()

        # Не трогаем произвольные текстовые поля.
        if current_value not in ("", "Гость", AGENT_NAME):
            continue

        if current_value != AGENT_NAME:
            await field.fill(AGENT_NAME)
            print(f"[Telemost] Имя установлено: {AGENT_NAME}")

        return True

    return False


async def click_button(
    root: Page | Frame,
    pattern: str,
) -> bool:
    """Нажать доступную кнопку без обхода проверки перекрытий."""
    for role in ("button", "link"):
        buttons = root.get_by_role(
            role,
            name=re.compile(pattern, re.IGNORECASE),
        )

        for index in range(await buttons.count()):
            button = buttons.nth(index)

            if not await button.is_visible():
                continue

            if not await button.is_enabled():
                continue

            try:
                await button.click(timeout=1500)
                return True

            except PlaywrightTimeoutError:
                # Кнопка может быть перекрыта другим экраном.
                # Не используем force=True.
                continue

    return False


async def mute_microphone(page: Page) -> None:
    """Выключить микрофон в доступном интерфейсе."""
    pattern = (
        r"выключить микрофон|"
        r"отключить микрофон|"
        r"mute microphone|"
        r"turn off microphone"
    )

    frame = get_entry_frame(page)

    # Сначала работаем внутри iframe.
    if frame is not None:
        if await click_button(frame, pattern):
            print("[Telemost] Микрофон выключен")
            return

        # Основная страница перекрыта экраном входа.
        cover = page.locator(".yamb-meeting-entry-cover")

        if await cover.count() and await cover.first.is_visible():
            return

    if await click_button(page, pattern):
        print("[Telemost] Микрофон выключен")


async def is_waiting_for_admission(page: Page) -> bool:
    pattern = re.compile(
        r"ожидани[ея] допуска|"
        r"ожидани[ея] подтверждения|"
        r"организатор.*(?:впустит|допустит)|"
        r"waiting for (?:the )?host|"
        r"waiting for approval",
        re.IGNORECASE,
    )

    frame = get_entry_frame(page)

    for root in (frame, page):
        if root is None:
            continue

        try:
            text = await root.locator("body").inner_text(
                timeout=2000
            )
            if pattern.search(text):
                return True
        except PlaywrightTimeoutError:
            pass

    return False


async def has_leave_button(root: Page | Frame) -> bool:
    """Найти видимую кнопку завершения звонка."""
    buttons = root.get_by_role(
        "button",
        name=re.compile(
            r"покинуть|"
            r"выйти из звонка|"
            r"завершить звонок|"
            r"leave call|"
            r"hang up",
            re.IGNORECASE,
        ),
    )

    for i in range(await buttons.count()):
        if await buttons.nth(i).is_visible():
            return True

    return False


async def is_connected(
    page: Page,
    join_clicked: bool,
) -> bool:
    """Проверить подключение, исключив экран входа."""
    if not join_clicked:
        return False

    if await has_guest_form(page):
        return False

    if await is_waiting_for_admission(page):
        return False

    frame = get_entry_frame(page)

    # Если интерфейс звонка находится внутри iframe.
    if frame is not None:
        if await has_leave_button(frame):
            return True

    # Не принимаем перекрытые кнопки основной страницы
    # за доказательство успешного подключения.
    cover = page.locator(".yamb-meeting-entry-cover")

    if await cover.count():
        if await cover.first.is_visible():
            return False

    return await has_leave_button(page)


async def dump_controls(page: Page) -> None:
    """Вывести кнопки для диагностики изменений UI."""
    frame = get_entry_frame(page)

    for name, root in (("iframe", frame), ("page", page)):
        if root is None:
            continue

        try:
            controls = await root.locator("button").evaluate_all(
                """elements => elements
                    .filter(el => el.getClientRects().length)
                    .map(el => ({
                        text: (el.innerText || "").trim(),
                        aria: el.getAttribute("aria-label")
                    }))
                    .slice(0, 30)
                """
            )

            print(f"[Debug] {name} buttons: {controls}")

        except Exception as exc:
            print(f"[Debug] Cannot inspect {name}: {exc}")


async def join_meeting(page: Page) -> bool:
    """Пройти экран подключения Телемоста."""
    print("[Telemost] Открываем конференцию...")

    await page.goto(
        MEETING_URL,
        wait_until="domcontentloaded",
        timeout=45000,
    )

    deadline = (
        asyncio.get_running_loop().time()
        + JOIN_TIMEOUT_SECONDS
    )

    join_clicked = False
    waiting_logged = False

    while asyncio.get_running_loop().time() < deadline:
        frame = get_entry_frame(page)
        root = frame or page

        if await is_connected(page, join_clicked):
            print("[Telemost] Подключение подтверждено")
            return True

        if await is_waiting_for_admission(page):
            if not waiting_logged:
                print("[Telemost] Ожидаем допуска организатора")
                waiting_logged = True

            await asyncio.sleep(2)
            continue

        # После нажатия Join ждём результата и не нажимаем
        # кнопку повторно.
        if join_clicked:
            await asyncio.sleep(2)
            continue

        # На экране предварительного подключения.
        await fill_guest_name(page)
        await mute_microphone(page)

        if await click_button(
            root,
            r"продолжить в браузере|"
            r"остаться в браузере|"
            r"continue in browser|"
            r"join in browser",
        ):
            print("[Telemost] Продолжаем в браузере")
            await asyncio.sleep(2)
            continue

        if await click_button(
            root,
            r"войти как гость|"
            r"продолжить без входа|"
            r"join as guest",
        ):
            print("[Telemost] Выбран гостевой вход")
            await asyncio.sleep(2)
            continue

        if await click_button(
            root,
            r"^подключиться(?: к звонку)?$|"
            r"^присоединиться$|"
            r"^join(?: meeting| call)?$",
        ):
            print("[Telemost] Нажата кнопка подключения")
            join_clicked = True
            await asyncio.sleep(2)
            continue

        await asyncio.sleep(2)

    await dump_controls(page)

    raise TimeoutError(
        "Не удалось подтвердить подключение к Телемосту. "
        "Проверь telemost_debug.png и выведенные кнопки."
    )


async def is_waiting_for_admission(page: Page) -> bool:
    """Определить комнату ожидания по тексту страницы."""

    body = await page.locator("body").inner_text(
        timeout=5000
    )

    return bool(
        re.search(
            r"ожидани[ея] допуска|"
            r"ожидани[ея] подтверждения|"
            r"организатор.*(?:впустит|допустит)|"
            r"waiting for (?:the )?host|"
            r"waiting for approval",
            body,
            re.IGNORECASE,
        )
    )

# ============================================================
# RECORDING
# ============================================================


async def record_audio() -> Path:
    """Записать PulseAudio monitor через FFmpeg в Docker."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = (
        f"telemost_{datetime.now():%Y%m%d_%H%M%S}.wav"
    )

    output_path = OUTPUT_DIR / filename
    container_path = f"/recordings/{filename}"

    command = [
        "docker", "compose",
        "-f", str(PROJECT_ROOT / COMPOSE_FILE),
        "exec", "-T",
        BROWSER_SERVICE,
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-nostdin",
        "-y",
        "-f", "pulse",
        "-i", AUDIO_SOURCE,
        "-t", str(RECORD_SECONDS),
        "-ac", str(CHANNELS),
        "-ar", str(SAMPLE_RATE),
        "-c:a", "pcm_s16le",
        container_path,
    ]

    print()
    print("[Recorder] Начинаем запись")
    print(f"[Recorder] Источник: {AUDIO_SOURCE}")
    print(f"[Recorder] Длительность: {RECORD_SECONDS} сек")
    print(f"[Recorder] Файл: {output_path}")
    print("[Recorder] Говори в конференции!")
    print()

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=RECORD_SECONDS + 30,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise TimeoutError("FFmpeg не завершился вовремя")

    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg error:\n{stderr.decode(errors='replace')}"
        )

    if not output_path.exists():
        raise FileNotFoundError(
            f"Файл записи не появился: {output_path}"
        )

    print("[Recorder] Запись завершена")
    print(
        f"[Recorder] Размер: "
        f"{output_path.stat().st_size / 1024:.1f} KiB"
    )

    return output_path


# ============================================================
# MAIN
# ============================================================

async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        print("[Browser] Подключаемся к Playwright Server")

        browser = await playwright.chromium.connect(
            BROWSER_WS_URL,
            timeout=30000,
        )

        context = None

        try:
            context = await browser.new_context(
                viewport={
                    "width": 1920,
                    "height": 1080,
                },
                permissions=["microphone", "camera"],
                locale="ru-RU",
            )

            page = await context.new_page()

            try:
                confirmed = await join_meeting(page)

                # Снимок страницы для проверки реального
                # состояния конференции.
                await page.screenshot(
                    path=str(DEBUG_SCREENSHOT)
                )

                print(
                    f"[Debug] Screenshot: {DEBUG_SCREENSHOT}"
                )

                if not confirmed:
                    print(
                        "[Warning] Проверь, что бот "
                        "действительно находится в звонке."
                    )

                await mute_microphone(page)

                output_path = await record_audio()

                print()
                print("=" * 55)
                print("TEST COMPLETED")
                print(f"Audio: {output_path}")
                print("=" * 55)

            except Exception:
                if not page.is_closed():
                    await page.screenshot(
                        path=str(DEBUG_SCREENSHOT),
                        timeout=5000,
                    )
                    print(
                        f"[Debug] Screenshot: {DEBUG_SCREENSHOT}"
                    )
                raise

        finally:
            if context is not None:
                await context.close()

            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[System] Остановлено пользователем")
    except Exception as exc:
        print(f"\n[Error] {type(exc).__name__}: {exc}")
        raise

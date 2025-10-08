"""
Automation runner that mirrors automation.py but drives the flow through the
Gemini Computer Use preview tooling (Playwright-based environment).

Steps performed by the agent:
    1. Ensure the HTML harness is reachable (start the lightweight server only when targeting localhost).
    2. Log in to the portal with test/test credentials.
    3. Populate the notes textarea with the provided note.
    4. Attach the configured PDF asset to the upload input via a custom computer-use tool.
    5. Submit the upload form and report the success message.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal, Optional
from urllib.parse import urlparse

import termcolor
from dotenv import load_dotenv
from google import genai
from google.genai import types
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console
from rich.table import Table


PORT = 8765
HOST = "127.0.0.1"

PLAYWRIGHT_SCREEN_SIZE = (1440, 900)
MAX_RECENT_TURN_WITH_SCREENSHOTS = 3

console = Console()

SCREENSHOT_FUNCTIONS = {
    "open_web_browser",
    "click_at",
    "hover_at",
    "type_text_at",
    "scroll_document",
    "scroll_at",
    "wait_5_seconds",
    "go_back",
    "go_forward",
    "search",
    "navigate",
    "key_combination",
    "drag_and_drop",
}


@contextmanager
def serve_test_app(root: Path) -> Iterator[str]:
    """
    Spin up a lightweight HTTP server so the agent can reach the HTML page.
    Returns the URL for index.html and ensures the server is cleaned up.
    """

    result_dir = root / "result"
    result_dir.mkdir(exist_ok=True)

    class AutomationHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            # Suppress default stdout logging noise during agent runs.
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/upload":
                self.send_error(404, "Unsupported endpoint")
                return

            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_error(400, "Expected multipart/form-data")
                return

            content_length = self.headers.get("Content-Length")
            if not content_length:
                self.send_error(411, "Missing Content-Length")
                return

            try:
                length = int(content_length)
            except ValueError:
                self.send_error(400, "Invalid Content-Length")
                return

            body = self.rfile.read(length)
            boundary_match = re.search("boundary=([^;]+)", content_type)
            if not boundary_match:
                self.send_error(400, "Missing multipart boundary")
                return

            boundary = boundary_match.group(1).strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]

            try:
                fields, files = self._parse_multipart(body, boundary)
            except ValueError as exc:
                self.send_error(400, str(exc))
                return

            if "file" not in files:
                self.send_error(400, "Missing file field")
                return

            filename, file_bytes = files["file"]
            if not filename:
                self.send_error(400, "File missing filename")
                return

            safe_name = os.path.basename(filename)
            target_path = result_dir / safe_name
            with target_path.open("wb") as output:
                output.write(file_bytes)

            note_value = fields.get("note", "")
            if note_value:
                note_path = result_dir / f"{target_path.stem}_note.txt"
                note_path.write_text(note_value, encoding="utf-8")

            payload = {"status": "ok", "filename": safe_name}
            if note_value:
                payload["note_saved"] = True

            body_json = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_json)))
            self.end_headers()
            self.wfile.write(body_json)

        @staticmethod
        def _parse_multipart(body: bytes, boundary: str) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
            boundary_bytes = f"--{boundary}".encode("utf-8")
            parts = body.split(boundary_bytes)
            fields: dict[str, str] = {}
            files: dict[str, tuple[str, bytes]] = {}

            for part in parts:
                if not part or part in (b"--", b"--\r\n"):
                    continue
                part = part.lstrip(b"\r\n")
                if part.endswith(b"\r\n"):
                    part = part[:-2]
                if part.endswith(b"--"):
                    part = part[:-2]

                header_blob, sep, data = part.partition(b"\r\n\r\n")
                if not sep:
                    continue
                data = data.rstrip(b"\r\n")

                header_text = header_blob.decode("utf-8", errors="ignore")
                headers = {}
                for line in header_text.split("\r\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.lower().strip()] = value.strip()

                disposition = headers.get("content-disposition", "")
                if not disposition:
                    continue

                disp_parts = disposition.split(";")
                if not disp_parts:
                    continue

                attrs = {}
                for item in disp_parts[1:]:
                    if "=" in item:
                        key, val = item.strip().split("=", 1)
                        attrs[key] = val.strip('"')

                field_name = attrs.get("name")
                if not field_name:
                    continue

                filename = attrs.get("filename")
                if filename is not None:
                    files[field_name] = (filename, data)
                else:
                    value = data.decode("utf-8", errors="ignore")
                    fields[field_name] = value

            if not parts:
                raise ValueError("Malformed multipart payload")
            return fields, files

    httpd = ThreadingHTTPServer((HOST, PORT), AutomationHandler)
    httpd.daemon_threads = True

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{HOST}:{PORT}/index.html"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


@dataclass
class EnvState:
    screenshot: bytes
    url: str


PLAYWRIGHT_KEY_MAP = {
    "backspace": "Backspace",
    "tab": "Tab",
    "return": "Enter",
    "enter": "Enter",
    "shift": "Shift",
    "control": "ControlOrMeta",
    "alt": "Alt",
    "escape": "Escape",
    "space": "Space",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "end": "End",
    "home": "Home",
    "left": "ArrowLeft",
    "up": "ArrowUp",
    "right": "ArrowRight",
    "down": "ArrowDown",
    "insert": "Insert",
    "delete": "Delete",
    "semicolon": ";",
    "equals": "=",
    "multiply": "Multiply",
    "add": "Add",
    "separator": "Separator",
    "subtract": "Subtract",
    "decimal": "Decimal",
    "divide": "Divide",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
    "command": "Meta",
}


class AutomationPlaywrightComputer:
    """Playwright-backed environment tailored for the Computer Use preview agent."""

    def __init__(
        self,
        screen_size: tuple[int, int],
        initial_url: str,
        search_engine_url: str = "https://www.google.com",
        highlight_mouse: bool = False,
    ):
        self._screen_size = screen_size
        self._initial_url = initial_url
        self._search_engine_url = search_engine_url
        self._highlight_mouse = highlight_mouse
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "AutomationPlaywrightComputer":
        print("Creating Playwright session...")
        headless_default = os.environ.get("PLAYWRIGHT_HEADLESS")
        headless = True
        if headless_default is not None:
            headless = headless_default.lower() in ("1", "true", "yes")

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-extensions",
                "--disable-file-system",
                "--disable-plugins",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
            ],
        )
        self._context = self._browser.new_context(
            viewport={"width": self._screen_size[0], "height": self._screen_size[1]}
        )
        self._page = self._context.new_page()
        self._context.on("page", self._handle_new_page)
        self._page.goto(self._initial_url)
        termcolor.cprint(
            "Started local Playwright environment.",
            color="green",
            attrs=["bold"],
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright:
            self._playwright.stop()

    def _handle_new_page(self, new_page: Page) -> None:
        if not self._page:
            return
        new_url = new_page.url
        new_page.close()
        self._page.goto(new_url)

    def open_web_browser(self) -> EnvState:
        return self.current_state()

    def click_at(self, x: int, y: int) -> EnvState:
        self._assert_page()
        self.highlight_mouse(x, y)
        self._page.mouse.click(x, y)
        self._page.wait_for_load_state()
        return self.current_state()

    def hover_at(self, x: int, y: int) -> EnvState:
        self._assert_page()
        self.highlight_mouse(x, y)
        self._page.mouse.move(x, y)
        self._page.wait_for_load_state()
        return self.current_state()

    def type_text_at(
        self,
        x: int,
        y: int,
        text: str,
        press_enter: bool,
        clear_before_typing: bool,
    ) -> EnvState:
        self._assert_page()
        self.highlight_mouse(x, y)
        self._page.mouse.click(x, y)
        self._page.wait_for_load_state()

        if clear_before_typing:
            modifier = "Command" if sys.platform == "darwin" else "Control"
            self.key_combination([modifier, "A"])
            self.key_combination(["Delete"])

        self._page.keyboard.type(text)
        self._page.wait_for_load_state()

        if press_enter:
            self.key_combination(["Enter"])
            self._page.wait_for_load_state()
        return self.current_state()

    def scroll_document(
        self, direction: Literal["up", "down", "left", "right"]
    ) -> EnvState:
        if direction == "down":
            return self.key_combination(["PageDown"])
        if direction == "up":
            return self.key_combination(["PageUp"])
        if direction in ("left", "right"):
            return self._horizontal_document_scroll(direction)
        raise ValueError(f"Unsupported direction: {direction}")

    def _horizontal_document_scroll(
        self, direction: Literal["left", "right"]
    ) -> EnvState:
        self._assert_page()
        amount = self.screen_size()[0] // 2
        sign = "-" if direction == "left" else ""
        self._page.evaluate(f"window.scrollBy({sign}{amount}, 0);")
        self._page.wait_for_load_state()
        return self.current_state()

    def scroll_at(
        self,
        x: int,
        y: int,
        direction: Literal["up", "down", "left", "right"],
        magnitude: int,
    ) -> EnvState:
        self._assert_page()
        self.highlight_mouse(x, y)
        self._page.mouse.move(x, y)
        self._page.wait_for_load_state()

        dx = 0
        dy = 0
        if direction == "up":
            dy = -magnitude
        elif direction == "down":
            dy = magnitude
        elif direction == "left":
            dx = -magnitude
        elif direction == "right":
            dx = magnitude
        else:
            raise ValueError(f"Unsupported direction: {direction}")

        self._page.mouse.wheel(dx, dy)
        self._page.wait_for_load_state()
        return self.current_state()

    def wait_5_seconds(self) -> EnvState:
        time.sleep(5)
        return self.current_state()

    def go_back(self) -> EnvState:
        self._assert_page()
        self._page.go_back()
        self._page.wait_for_load_state()
        return self.current_state()

    def go_forward(self) -> EnvState:
        self._assert_page()
        self._page.go_forward()
        self._page.wait_for_load_state()
        return self.current_state()

    def search(self) -> EnvState:
        return self.navigate(self._search_engine_url)

    def navigate(self, url: str) -> EnvState:
        self._assert_page()
        normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
        self._page.goto(normalized)
        self._page.wait_for_load_state()
        return self.current_state()

    def key_combination(self, keys: list[str]) -> EnvState:
        self._assert_page()
        canonical = [PLAYWRIGHT_KEY_MAP.get(k.lower(), k) for k in keys]
        for key in canonical[:-1]:
            self._page.keyboard.down(key)
        self._page.keyboard.press(canonical[-1])
        for key in reversed(canonical[:-1]):
            self._page.keyboard.up(key)
        self._page.wait_for_load_state()
        return self.current_state()

    def drag_and_drop(
        self, x: int, y: int, destination_x: int, destination_y: int
    ) -> EnvState:
        self._assert_page()
        self.highlight_mouse(x, y)
        self._page.mouse.move(x, y)
        self._page.mouse.down()
        self._page.wait_for_load_state()
        self.highlight_mouse(destination_x, destination_y)
        self._page.mouse.move(destination_x, destination_y)
        self._page.mouse.up()
        self._page.wait_for_load_state()
        return self.current_state()

    def current_state(self) -> EnvState:
        self._assert_page()
        self._page.wait_for_load_state()
        time.sleep(0.5)
        screenshot = self._page.screenshot(type="png", full_page=False)
        return EnvState(screenshot=screenshot, url=self._page.url)

    def screen_size(self) -> tuple[int, int]:
        if not self._page:
            return self._screen_size
        viewport = self._page.viewport_size
        if viewport:
            return viewport["width"], viewport["height"]
        return self._screen_size

    def highlight_mouse(self, x: int, y: int) -> None:
        if not self._highlight_mouse or not self._page:
            return
        self._page.evaluate(
            f"""
        () => {{
            const element_id = "playwright-feedback-circle";
            let div = document.getElementById(element_id);
            if (!div) {{
                div = document.createElement('div');
                div.id = element_id;
                div.style.pointerEvents = 'none';
                div.style.border = '4px solid red';
                div.style.borderRadius = '50%';
                div.style.width = '20px';
                div.style.height = '20px';
                div.style.position = 'fixed';
                div.style.zIndex = '9999';
                document.body.appendChild(div);
            }}
            div.hidden = false;
            div.style.left = {x} - 10 + 'px';
            div.style.top = {y} - 10 + 'px';
            setTimeout(() => {{
                div.hidden = true;
            }}, 2000);
        }}
        """
        )
        time.sleep(1)

    def attach_file_to_input(self, selector: str, file_path: str) -> EnvState:
        self._assert_page()
        resolved = Path(file_path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        target_selector = selector
        locator = self._page.locator(target_selector)
        try:
            locator.wait_for(state="attached", timeout=5000)
        except PlaywrightTimeoutError:
            fallback_selector = "input[type='file']"
            if target_selector != fallback_selector:
                locator = self._page.locator(fallback_selector)
                locator.wait_for(state="attached", timeout=5000)
                target_selector = fallback_selector
            else:
                raise
        locator = self._page.locator(target_selector)
        locator.set_input_files(str(resolved))
        self._page.wait_for_load_state()
        return self.current_state()

    def _assert_page(self) -> None:
        if not self._page:
            raise RuntimeError("Playwright page is not initialized.")


def multiply_numbers(x: float, y: float) -> dict:
    """Multiplies two numbers."""
    return {"result": x * y}


def set_file_input(selector: str, file_path: str) -> dict:
    """
    Custom tool schema: attaches the file at file_path to the provided CSS selector.
    The implementation lives in AutomationBrowserAgent.handle_action.
    """
    return {"status": "queued"}


class AutomationBrowserAgent:
    def __init__(
        self,
        browser_computer: AutomationPlaywrightComputer,
        query: str,
        model_name: str,
        verbose: bool = True,
    ):
        self._browser_computer = browser_computer
        self._query = query
        self._model_name = model_name
        self._verbose = verbose
        self.final_reasoning = None
        self._client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            vertexai=os.environ.get("USE_VERTEXAI", "0").lower() in {"true", "1"},
            project=os.environ.get("VERTEXAI_PROJECT"),
            location=os.environ.get("VERTEXAI_LOCATION"),
        )
        self._contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=self._query),
                ],
            )
        ]

        custom_functions = [
            types.FunctionDeclaration.from_callable(
                client=self._client, callable=multiply_numbers
            ),
            types.FunctionDeclaration.from_callable(
                client=self._client, callable=set_file_input
            ),
        ]

        self._generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
                        excluded_predefined_functions=[],
                    ),
                ),
                types.Tool(function_declarations=custom_functions),
            ],
        )

    def handle_action(self, action: types.FunctionCall) -> EnvState | dict:
        if action.name == "open_web_browser":
            return self._browser_computer.open_web_browser()
        if action.name == "click_at":
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            return self._browser_computer.click_at(x=x, y=y)
        if action.name == "hover_at":
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            return self._browser_computer.hover_at(x=x, y=y)
        if action.name == "type_text_at":
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            press_enter = action.args.get("press_enter", False)
            clear_before_typing = action.args.get("clear_before_typing", True)
            return self._browser_computer.type_text_at(
                x=x,
                y=y,
                text=action.args["text"],
                press_enter=press_enter,
                clear_before_typing=clear_before_typing,
            )
        if action.name == "scroll_document":
            return self._browser_computer.scroll_document(action.args["direction"])
        if action.name == "scroll_at":
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            magnitude = action.args.get("magnitude", 800)
            direction = action.args["direction"]
            if direction in ("up", "down"):
                magnitude = self.denormalize_y(magnitude)
            elif direction in ("left", "right"):
                magnitude = self.denormalize_x(magnitude)
            else:
                raise ValueError(f"Unknown direction: {direction}")
            return self._browser_computer.scroll_at(
                x=x, y=y, direction=direction, magnitude=magnitude
            )
        if action.name == "wait_5_seconds":
            return self._browser_computer.wait_5_seconds()
        if action.name == "go_back":
            return self._browser_computer.go_back()
        if action.name == "go_forward":
            return self._browser_computer.go_forward()
        if action.name == "search":
            return self._browser_computer.search()
        if action.name == "navigate":
            return self._browser_computer.navigate(action.args["url"])
        if action.name == "key_combination":
            return self._browser_computer.key_combination(
                action.args["keys"].split("+")
            )
        if action.name == "drag_and_drop":
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            dest_x = self.denormalize_x(action.args["destination_x"])
            dest_y = self.denormalize_y(action.args["destination_y"])
            return self._browser_computer.drag_and_drop(
                x=x,
                y=y,
                destination_x=dest_x,
                destination_y=dest_y,
            )
        if action.name == multiply_numbers.__name__:
            return multiply_numbers(x=action.args["x"], y=action.args["y"])
        if action.name == set_file_input.__name__:
            selector = action.args["selector"]
            file_path = action.args["file_path"]
            return self._browser_computer.attach_file_to_input(selector, file_path)
        raise ValueError(f"Unsupported function: {action.name}")

    def get_model_response(
        self, max_retries: int = 5, base_delay_s: int = 1
    ) -> types.GenerateContentResponse:
        for attempt in range(max_retries):
            try:
                return self._client.models.generate_content(
                    model=self._model_name,
                    contents=self._contents,
                    config=self._generate_content_config,
                )
            except Exception as exc:  # pragma: no cover - network retries
                if attempt < max_retries - 1:
                    delay = base_delay_s * (2**attempt)
                    termcolor.cprint(
                        f"Generate content failed ({exc}). Retrying in {delay}s...",
                        color="yellow",
                    )
                    time.sleep(delay)
                else:
                    termcolor.cprint(
                        "Generate content failed after max retries.",
                        color="red",
                    )
                    raise

    def get_text(self, candidate: types.Candidate) -> Optional[str]:
        if not candidate.content or not candidate.content.parts:
            return None
        text_parts = []
        for part in candidate.content.parts:
            if part.text:
                text_parts.append(part.text)
        return " ".join(text_parts) or None

    def extract_function_calls(
        self, candidate: types.Candidate
    ) -> list[types.FunctionCall]:
        if not candidate.content or not candidate.content.parts:
            return []
        calls = []
        for part in candidate.content.parts:
            if part.function_call:
                calls.append(part.function_call)
        return calls

    def run_one_iteration(self) -> Literal["COMPLETE", "CONTINUE"]:
        if self._verbose:
            with console.status(
                "Generating response from Google Computer Use...", spinner_style=None
            ):
                try:
                    response = self.get_model_response()
                except Exception:
                    return "COMPLETE"
        else:
            try:
                response = self.get_model_response()
            except Exception:
                return "COMPLETE"

        if not response.candidates:
            raise ValueError("Empty response from model.")

        candidate = response.candidates[0]
        if candidate.content:
            self._contents.append(candidate.content)

        reasoning = self.get_text(candidate)
        function_calls = self.extract_function_calls(candidate)

        if (
            not function_calls
            and not reasoning
            and candidate.finish_reason == types.FinishReason.MALFORMED_FUNCTION_CALL
        ):
            return "CONTINUE"

        if not function_calls:
            print(f"Agent Loop Complete: {reasoning}")
            self.final_reasoning = reasoning
            return "COMPLETE"

        function_call_strs = []
        for function_call in function_calls:
            function_call_str = f"Name: {function_call.name}"
            if function_call.args:
                function_call_str += "\nArgs:"
                for key, value in function_call.args.items():
                    function_call_str += f"\n  {key}: {value}"
            function_call_strs.append(function_call_str)

        table = Table(expand=True)
        table.add_column(
            "Google Computer Use Reasoning", header_style="magenta", ratio=1
        )
        table.add_column("Function Call(s)", header_style="cyan", ratio=1)
        table.add_row(reasoning, "\n".join(function_call_strs))
        if self._verbose:
            console.print(table)
            print()

        function_responses = []
        for function_call in function_calls:
            extra_fields: dict[str, Any] = {}
            safety = function_call.args.get("safety_decision") if function_call.args else None
            if safety:
                decision = self._get_safety_confirmation(safety)
                if decision == "TERMINATE":
                    print("Terminating agent loop")
                    return "COMPLETE"
                extra_fields["safety_acknowledgement"] = "true"
            if self._verbose:
                with console.status(
                    "Sending command to Computer...", spinner_style=None
                ):
                    response_payload = self.handle_action(function_call)
            else:
                response_payload = self.handle_action(function_call)

            if isinstance(response_payload, EnvState):
                function_responses.append(
                    types.FunctionResponse(
                        name=function_call.name,
                        response={
                            "url": response_payload.url,
                            **extra_fields,
                        },
                        parts=[
                            types.FunctionResponsePart(
                                inline_data=types.FunctionResponseBlob(
                                    mime_type="image/png", data=response_payload.screenshot
                                )
                            )
                        ],
                    )
                )
            else:
                function_responses.append(
                    types.FunctionResponse(
                        name=function_call.name,
                        response={**response_payload, **extra_fields},
                    )
                )

        self._contents.append(
            types.Content(
                role="user",
                parts=[types.Part(function_response=fr) for fr in function_responses],
            )
        )

        turn_with_screenshots_found = 0
        for content in reversed(self._contents):
            if content.role != "user" or not content.parts:
                continue
            has_screenshot = False
            for part in content.parts:
                if (
                    part.function_response
                    and part.function_response.parts
                    and part.function_response.name in SCREENSHOT_FUNCTIONS
                ):
                    has_screenshot = True
                    break
            if has_screenshot:
                turn_with_screenshots_found += 1
                if turn_with_screenshots_found > MAX_RECENT_TURN_WITH_SCREENSHOTS:
                    for part in content.parts:
                        if (
                            part.function_response
                            and part.function_response.parts
                            and part.function_response.name in SCREENSHOT_FUNCTIONS
                        ):
                            part.function_response.parts = None

        return "CONTINUE"

    def _get_safety_confirmation(
        self, safety: dict[str, Any]
    ) -> Literal["CONTINUE", "TERMINATE"]:
        if safety.get("decision") != "require_confirmation":
            raise ValueError("Unknown safety decision.")
        termcolor.cprint(
            "Safety service requires explicit confirmation!",
            color="yellow",
            attrs=["bold"],
        )
        print(safety.get("explanation"))
        decision = ""
        while decision.lower() not in {"y", "n", "ye", "yes", "no"}:
            decision = input("Do you wish to proceed? [Yes]/[No]\n")
        if decision.lower() in {"n", "no"}:
            return "TERMINATE"
        return "CONTINUE"

    def agent_loop(self) -> None:
        status: Literal["COMPLETE", "CONTINUE"] = "CONTINUE"
        while status == "CONTINUE":
            status = self.run_one_iteration()

    def denormalize_x(self, x: int) -> int:
        return int(x / 1000 * self._browser_computer.screen_size()[0])

    def denormalize_y(self, y: int) -> int:
        return int(y / 1000 * self._browser_computer.screen_size()[1])


def _resolve_pdf_path(base_dir: Path, pdf_source: str | None) -> Path:
    """
    Resolve the PDF the agent should upload.

    The PDF can be referenced via:
    - None / relative path: resolves against the project directory.
    - Absolute filesystem path.
    - gs://bucket/path/to/file.pdf (downloaded into a temp directory).
    """

    if not pdf_source:
        raise RuntimeError(
            "PDF source must be provided via --pdf-uri CLI flag or PDF_URI environment variable."
        )

    parsed = urlparse(pdf_source)
    if parsed.scheme == "gs":
        bucket_name = parsed.netloc
        blob_name = parsed.path.lstrip("/")
        if not bucket_name or not blob_name:
            raise ValueError("GCS URI must include bucket and object name, e.g. gs://bucket/path/file.pdf")

        try:
            from google.cloud import storage  # type: ignore import
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ImportError(
                "google-cloud-storage is required to download PDFs from GCS. "
                "Add it to requirements or provide a local path."
            ) from exc

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if not blob.exists():
            raise FileNotFoundError(f"GCS object gs://{bucket_name}/{blob_name} does not exist")

        temp_dir = Path(tempfile.mkdtemp(prefix="automation_pdf_"))
        local_path = temp_dir / Path(blob_name).name
        blob.download_to_filename(local_path)
        return local_path

    pdf_path = Path(pdf_source)
    if not pdf_path.is_absolute():
        pdf_path = (base_dir / pdf_path).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"Expected PDF payload at {pdf_path}")

    return pdf_path


def run_agent(
    target_url: str | None = None,
    note_text: str | None = None,
    pdf_source: str | None = None,
) -> Optional[str]:
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir

    load_dotenv()
    load_dotenv(base_dir / ".env")
    load_dotenv(script_dir / ".env")

    pdf_path = _resolve_pdf_path(base_dir, pdf_source)
    pdf_path_str = str(pdf_path)
    print(f"Using PDF asset at {pdf_path_str}")

    resolved_url = target_url or os.getenv(
        "AUTOMATION_TARGET_URL",
        "https://browser-use-demo-24173060393.us-central1.run.app/",
    )

    if resolved_url.startswith("http://127.0.0.1") or resolved_url.startswith("http://localhost"):
        context_manager = serve_test_app(base_dir)
    else:
        context_manager = contextlib.nullcontext(resolved_url)  # type: ignore[arg-type]

    os.environ.setdefault("PLAYWRIGHT_HEADLESS", "1")

    vertex_project = (
        os.getenv("VERTEXAI_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("PROJECT_ID")
        or os.getenv("GCLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
    )
    vertex_location = (
        os.getenv("VERTEXAI_LOCATION")
        or os.getenv("GOOGLE_CLOUD_REGION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or "us-central1"
    )

    requested_use_vertex = os.getenv("USE_VERTEXAI")
    if requested_use_vertex is None:
        use_vertex_ai = vertex_project is not None
    else:
        use_vertex_ai = requested_use_vertex.lower() in {"1", "true", "yes"}

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if use_vertex_ai:
        if not vertex_project:
            raise RuntimeError(
                "Vertex AI execution requires a project. Set VERTEXAI_PROJECT or GOOGLE_CLOUD_PROJECT."
            )
        os.environ["USE_VERTEXAI"] = "1"
        os.environ.setdefault("VERTEXAI_PROJECT", vertex_project)
        os.environ.setdefault("VERTEXAI_LOCATION", vertex_location)
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", vertex_project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", vertex_location)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
    else:
        if not api_key:
            raise RuntimeError(
                "Provide GEMINI_API_KEY / GOOGLE_API_KEY or configure Vertex AI credentials."
            )
        os.environ["USE_VERTEXAI"] = "0"
        os.environ["GEMINI_API_KEY"] = api_key

    model_name = os.getenv("GEMINI_COMPUTER_USE_MODEL") or "gemini-2.5-computer-use-preview-10-2025"

    with context_manager as url:
        final_note = note_text or "Automated upload triggered by Gemini Computer Use agent."
        task = (
            "You are interacting with the automation portal.\n"
            f"1. Navigate to {url}.\n"
            "2. Log in using username `test` and password `test`.\n"
            "3. After the app appears, focus the textarea labelled Notes and replace its contents with the provided note.\n"
            f"4. Use the custom tool `set_file_input(selector, file_path)` with selector `input[type='file']` and file_path `{pdf_path_str}` to attach the PDF.\n"
            "5. Submit the upload form and confirm the success banner references the uploaded filename.\n"
            "6. Report the final status message from the page."
            f"\nThe note you must enter is: {final_note}"
        )

        with AutomationPlaywrightComputer(
            screen_size=PLAYWRIGHT_SCREEN_SIZE,
            initial_url=url,
        ) as computer:
            agent = AutomationBrowserAgent(
                browser_computer=computer,
                query=task,
                model_name=model_name,
            )
            agent.agent_loop()

            # Persist reasoning trace for debugging.
            run_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            reasoning_log: list[dict[str, Any]] = []
            for content in getattr(agent, "_contents", []):
                if content.role != "model" or not content.parts:
                    continue

                reasoning_texts: list[str] = []
                function_calls: list[dict[str, Any]] = []

                for part in content.parts:
                    if part.text:
                        reasoning_texts.append(part.text)
                    if part.function_call:
                        fc = part.function_call
                        fc_args = dict(fc.args) if fc.args else {}
                        function_calls.append(
                            {
                                "name": fc.name,
                                "args": fc_args,
                            }
                        )

                if reasoning_texts or function_calls:
                    reasoning_log.append(
                        {
                            "reasoning": "\n\n".join(reasoning_texts) if reasoning_texts else None,
                            "function_calls": function_calls,
                        }
                    )

            run_record = {
                "timestamp": run_timestamp,
                "target_url": url,
                "note": final_note,
                "final_reasoning": agent.final_reasoning,
                "steps": reasoning_log,
            }

            result_dir = base_dir / "result"
            result_dir.mkdir(exist_ok=True)
            run_path = result_dir / f"computer_use_run_{int(time.time())}.json"
            run_path.write_text(json.dumps(run_record, indent=2), encoding="utf-8")

            return agent.final_reasoning


def main() -> None:
    result = run_agent()
    if result:
        print(result)


if __name__ == "__main__":
    main()

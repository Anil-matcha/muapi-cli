"""muapi auth — configure API key and inspect identity."""
import os
import re
import subprocess
import sys
import webbrowser

import httpx
import typer
from rich.prompt import Confirm, Prompt

from ..config import BASE_URL, _CONFIG_FILE, delete_api_key, get_api_key, get_key_info, save_api_key
from .. import exitcodes
from ..utils import console, error_exit, out

app = typer.Typer(help="Manage authentication and API key.")

_AUTH_BASE = BASE_URL.replace("/api/v1", "")
_ACCESS_KEYS_URL = "https://muapi.ai/access-keys"

LINKS = {
    "dashboard":   "https://muapi.ai/dashboard",
    "access-keys": _ACCESS_KEYS_URL,
    "models":      "https://muapi.ai/models",
    "docs":        "https://muapi.ai/docs",
    "pricing":     "https://muapi.ai/pricing",
}


def _mask(key: str) -> str:
    if len(key) < 12:
        return "••••"
    return key[:8] + "…" + key[-4:]


def _looks_like_key(s: str) -> bool:
    s = s.strip()
    return bool(re.match(r'^[A-Za-z0-9_\-]{20,}$', s) and '\n' not in s)


def _read_clipboard() -> str | None:
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            return r.stdout.strip() or None
        if sys.platform.startswith("linux"):
            for cmd in (["xclip", "-o"], ["xsel", "--clipboard", "--output"]):
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                    if r.returncode == 0:
                        return r.stdout.strip() or None
                except FileNotFoundError:
                    continue
        if sys.platform == "win32":
            r = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
            )
            return r.stdout.strip() or None
    except Exception:
        pass
    return None


def _validate_key(api_key: str) -> tuple[bool, str]:
    """Validate key against the live API. Returns (ok, error_msg)."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/account/balance",
            headers={"x-api-key": api_key},
            timeout=15.0,
        )
        if resp.status_code in (401, 403):
            return False, "API rejected the key (401/403)."
        if resp.status_code >= 400:
            return False, f"API returned {resp.status_code}."
        return True, ""
    except httpx.RequestError as e:
        return False, f"Could not reach {BASE_URL}: {e}"


def _find_project_config() -> str | None:
    """Walk up from CWD looking for muapi.json."""
    from pathlib import Path
    d = Path.cwd()
    while True:
        candidate = d / "muapi.json"
        if candidate.exists():
            return str(candidate)
        parent = d.parent
        if parent == d:
            return None
        d = parent


def _do_save(api_key: str) -> None:
    with console.status("[dim]Validating with api.muapi.ai…[/dim]"):
        ok, reason = _validate_key(api_key)

    if not ok:
        console.print(f"[bold red]✖[/bold red] {reason}")
        console.print()
        console.print(f"[dim]  Double-check at [/dim][cyan]{_ACCESS_KEYS_URL}[/cyan]")
        console.print("[dim]  Or set [/dim][cyan]MUAPI_API_KEY[/cyan][dim] in your shell and skip this step.[/dim]\n")
        raise typer.Exit(exitcodes.AUTH_ERROR)

    location = save_api_key(api_key)
    location_display = "OS keychain" if location == "keychain" else str(_CONFIG_FILE)
    console.print("[bold green]✔[/bold green] Signed in.")
    console.print()
    console.print(f"  [dim]Key:    [/dim][green]{_mask(api_key)}[/green]")
    console.print(f"  [dim]Stored: [/dim][cyan]{location_display}[/cyan]")
    console.print()
    console.print("[bold]Try it:[/bold]")
    console.print("  [cyan]muapi account balance[/cyan]")
    console.print("  [cyan]muapi image generate -p \"a cyberpunk skyline at golden hour\"[/cyan]")
    console.print("  [cyan]muapi video generate -p \"drone shot over snowy peaks\" --model kling-master[/cyan]")
    console.print()


@app.command("login")
def login(
    email: str = typer.Option(..., "--email", "-e", help="Your muapi.ai email address"),
    password: str = typer.Option(None, "--password", "-p", help="Password (will prompt if omitted)"),
):
    """Log in with email + password and save an API key automatically."""
    if not password:
        password = Prompt.ask("[bold]Password[/bold]", password=True, console=console)
    if not password:
        error_exit("Password is required.", exitcodes.AUTH_ERROR)

    try:
        resp = httpx.post(
            f"{_AUTH_BASE}/api/auth/cli/login",
            json={"email": email, "password": password, "username": ""},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 401:
        error_exit("Invalid email or password.", exitcodes.AUTH_ERROR)
    if resp.status_code == 403:
        error_exit("Email not verified. Check your inbox.", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Login failed: {resp.text}", exitcodes.AUTH_ERROR)

    data = resp.json()
    api_key = data.get("api_key", "")
    if not api_key:
        error_exit("No API key in response. Please try again.", exitcodes.AUTH_ERROR)

    location = save_api_key(api_key)
    console.print(f"[green]Logged in as {data.get('email', email)}. API key saved to {location}.[/green]")


@app.command("register")
def register(
    email: str = typer.Option(..., "--email", "-e", help="Email address to register"),
    password: str = typer.Option(None, "--password", "-p", help="Password (will prompt if omitted)"),
    username: str = typer.Option("", "--username", "-u", help="Display name (optional)"),
):
    """Create a new muapi.ai account and verify via email OTP."""
    if not password:
        password = Prompt.ask("[bold]Choose a password[/bold]", password=True, console=console)
        confirm = Prompt.ask("[bold]Confirm password[/bold]", password=True, console=console)
        if password != confirm:
            error_exit("Passwords do not match.", exitcodes.VALIDATION)
    if not password:
        error_exit("Password is required.", exitcodes.VALIDATION)

    try:
        resp = httpx.post(
            f"{_AUTH_BASE}/api/auth/register",
            json={"email": email, "password": password, "username": username or email.split("@")[0]},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 400:
        error_exit(f"Registration failed: {resp.json().get('detail', resp.text)}", exitcodes.VALIDATION)
    if resp.status_code >= 400:
        error_exit(f"Registration failed: {resp.text}", exitcodes.ERROR)

    detail = resp.json().get("detail", "OTP sent to your email.")
    console.print(f"[green]{detail}[/green]")
    console.print("Check your inbox, then run: [bold]muapi auth verify --email {email} --otp <OTP>[/bold]")


@app.command("verify")
def verify(
    email: str = typer.Option(..., "--email", "-e", help="Email address used during registration"),
    otp: str = typer.Option(..., "--otp", "-o", help="OTP code from your email"),
):
    """Verify your email OTP after registration, then save an API key."""
    try:
        resp = httpx.post(
            f"{_AUTH_BASE}/api/auth/verify-otp",
            json={"email": email, "otp": otp},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 401:
        error_exit("Invalid or expired OTP.", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Verification failed: {resp.text}", exitcodes.AUTH_ERROR)

    console.print("[green]Email verified! You can now log in.[/green]")
    console.print(f"Run: [bold]muapi auth login --email {email}[/bold]")


@app.command("forgot-password")
def forgot_password(
    email: str = typer.Option(..., "--email", "-e", help="Email address on your account"),
):
    """Send a password reset OTP to your email."""
    try:
        resp = httpx.post(
            f"{_AUTH_BASE}/api/auth/forgot-password",
            json={"email": email},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 404:
        error_exit("No account found for that email.", exitcodes.NOT_FOUND)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    console.print(f"[green]{resp.json().get('detail', 'OTP sent to your email.')}[/green]")
    console.print(f"Then run: [bold]muapi auth reset-password --email {email} --otp <OTP> --password <new>[/bold]")


@app.command("reset-password")
def reset_password(
    email: str = typer.Option(..., "--email", "-e", help="Your email address"),
    otp: str = typer.Option(..., "--otp", "-o", help="OTP from the reset email"),
    password: str = typer.Option(None, "--password", "-p", help="New password (will prompt if omitted)"),
):
    """Reset your password using an OTP sent to your email."""
    if not password:
        password = Prompt.ask("[bold]New password[/bold]", password=True, console=console)
        confirm = Prompt.ask("[bold]Confirm new password[/bold]", password=True, console=console)
        if password != confirm:
            error_exit("Passwords do not match.", exitcodes.VALIDATION)
    if not password:
        error_exit("Password is required.", exitcodes.VALIDATION)

    try:
        resp = httpx.post(
            f"{_AUTH_BASE}/api/auth/reset-password",
            json={"email": email, "otp": otp, "password": password},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 401:
        error_exit("Invalid or expired OTP.", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    console.print(f"[green]{resp.json().get('detail', 'Password reset successfully.')}[/green]")
    console.print(f"Run: [bold]muapi auth login --email {email}[/bold]")


@app.command("configure")
def configure(
    api_key: str = typer.Option(None, "--api-key", "-k", help="API key (skips all prompts)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Skip opening the access-keys page"),
):
    """Save your muapi API key — opens browser, detects clipboard, validates before saving."""
    if api_key:
        _do_save(api_key.strip())
        return

    console.print()
    console.print("[bold magenta]  Welcome to muapi.[/bold magenta]")
    console.print("[dim]  Sign in once and you're set on this machine.[/dim]\n")

    if not no_browser:
        console.print(f"[bold]  1.[/bold] Opening [cyan]{_ACCESS_KEYS_URL}[/cyan]")
        try:
            webbrowser.open(_ACCESS_KEYS_URL)
        except Exception:
            console.print("[dim]     (browser launch failed — open the link manually)[/dim]")
        console.print("[bold]  2.[/bold] Copy your API key")
        console.print("[bold]  3.[/bold] Paste below — we'll validate it automatically\n")

    # Clipboard detection
    detected: str | None = None
    clip = _read_clipboard()
    if clip and _looks_like_key(clip):
        detected = clip

    if detected:
        use_it = Confirm.ask(
            f"  Detected a key on your clipboard ({_mask(detected)}). Use it?",
            default=True,
            console=console,
        )
        if use_it:
            api_key = detected

    if not api_key:
        api_key = Prompt.ask("[bold]  Paste your API key[/bold]", password=True, console=console)
        api_key = api_key.strip()

    if not api_key:
        error_exit("No API key provided.", exitcodes.AUTH_ERROR)

    _do_save(api_key)


@app.command("status")
def status():
    """Show the active API key, config location, base URL, and quick links."""
    key, source = get_key_info()

    console.print()
    console.print("[bold]muapi CLI status[/bold]")
    if key:
        console.print(f"  [dim]API key:  [/dim][green]{_mask(key)}[/green]")
    else:
        console.print(f"  [dim]API key:  [/dim][red]not set — run [bold]muapi auth configure[/bold][/red]")
    console.print(f"  [dim]Source:   [/dim][cyan]{source}[/cyan]")
    console.print(f"  [dim]Base URL: [/dim][cyan]{BASE_URL}[/cyan]")
    console.print(f"  [dim]Config:   [/dim][cyan]{_CONFIG_FILE}[/cyan]")

    project_file = _find_project_config()
    if project_file:
        console.print(f"  [dim]Project:  [/dim][cyan]{project_file}[/cyan] [dim](muapi.json detected)[/dim]")

    console.print()
    console.print("[bold]Useful links[/bold]")
    width = max(len(k) for k in LINKS)
    for name, url in LINKS.items():
        console.print(f"  [dim]{name.ljust(width)}[/dim]  [cyan]{url}[/cyan]")
    console.print()
    console.print("[dim]Jump in your browser: [/dim][cyan]muapi open <target>[/cyan]")
    console.print()


@app.command("whoami")
def whoami():
    """Alias for [bold]muapi auth status[/bold]."""
    status()


@app.command("logout")
def logout():
    """Remove the stored API key."""
    delete_api_key()
    console.print("[green]API key removed.[/green]")

"""muapi account — check balance and top up credits."""
import json
import webbrowser

import httpx
import typer

from .. import exitcodes
from ..config import BASE_URL, get_api_key
from ..utils import console, error_exit, out

app = typer.Typer(help="Manage your muapi.ai account balance and credits.")


def _headers() -> dict:
    key = get_api_key()
    if not key:
        error_exit("No API key configured. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    return {"x-api-key": key}


@app.command("balance")
def balance(
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print raw JSON"),
):
    """Show your current account balance."""
    try:
        resp = httpx.get(f"{BASE_URL}/account/balance", headers=_headers(), timeout=30.0)
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 401 or resp.status_code == 403:
        error_exit("Authentication failed. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    data = resp.json()
    if output_json:
        out.print_json(json.dumps(data))
    else:
        bal = data.get("balance", 0.0)
        currency = data.get("currency", "USD").upper()
        email = data.get("email", "")
        console.print(f"[bold]{email}[/bold]")
        console.print(f"Balance: [green bold]${bal:.4f} {currency}[/green bold]")


@app.command("topup")
def topup(
    amount: int = typer.Option(10, "--amount", "-a", help="Amount in USD to add (minimum $1)"),
    currency: str = typer.Option("usd", "--currency", "-c", help="Currency (default: usd)"),
    output_json: bool = typer.Option(False, "--output-json", "-j", help="Print checkout URL as JSON instead of opening browser"),
    no_open: bool = typer.Option(False, "--no-open", help="Print URL without opening browser"),
):
    """Add credits to your account via Stripe checkout."""
    if amount < 1:
        error_exit("Minimum topup amount is $1.", exitcodes.VALIDATION)

    try:
        resp = httpx.post(
            f"{BASE_URL}/account/topup",
            json={"amount": amount, "currency": currency.lower()},
            headers=_headers(),
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        error_exit(f"Network error: {exc}", exitcodes.ERROR)

    if resp.status_code == 401 or resp.status_code == 403:
        error_exit("Authentication failed. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    if resp.status_code == 402:
        error_exit("Billing error. Please contact support.", exitcodes.BILLING_ERROR)
    if resp.status_code >= 400:
        error_exit(f"Request failed: {resp.text}", exitcodes.ERROR)

    data = resp.json()
    checkout_url = data.get("checkout_url", "")

    if output_json:
        out.print_json(json.dumps(data))
        return

    console.print(f"Checkout URL: [bold blue]{checkout_url}[/bold blue]")

    if not no_open:
        console.print("Opening browser for payment…")
        webbrowser.open(checkout_url)
    else:
        console.print("Open the URL above to complete payment.")

"""muapi workflow — list, create, run, and visualize AI workflows."""
import json
import time
from typing import Optional

import httpx
import typer

from .. import exitcodes
from ..config import BASE_URL, get_api_key
from ..utils import console, error_exit, out

app = typer.Typer(help="Build, run, and visualize multi-step AI workflows.")

# Workflow router is at /workflow, not /api/v1
_WORKFLOW_BASE = BASE_URL.replace("/api/v1", "") + "/workflow"
_POLL_INTERVAL = 4
_MAX_WAIT = 600


def _headers() -> dict:
    key = get_api_key()
    if not key:
        error_exit("No API key configured. Run: muapi auth configure", exitcodes.AUTH_ERROR)
    return {"x-api-key": key, "Content-Type": "application/json"}


def _get(path: str) -> dict:
    resp = httpx.get(f"{_WORKFLOW_BASE}/{path.lstrip('/')}", headers=_headers(), timeout=30.0)
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(resp.text, request=resp.request, response=resp)
    return resp.json()


def _post(path: str, body: dict) -> dict:
    resp = httpx.post(f"{_WORKFLOW_BASE}/{path.lstrip('/')}", json=body, headers=_headers(), timeout=60.0)
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(resp.text, request=resp.request, response=resp)
    return resp.json()


# ── ASCII visualization ────────────────────────────────────────────────────────

def _visualize(workflow: dict) -> None:
    """Render a workflow node graph in the terminal using Rich."""
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text

    nodes_raw = workflow.get("nodes") or workflow.get("data", {}).get("nodes") or []
    if not nodes_raw:
        console.print("[dim]No nodes found in workflow.[/dim]")
        return

    # Build adjacency: {node_id: [downstream_ids]}
    id_to_node = {n["id"]: n for n in nodes_raw}
    downstream: dict[str, list] = {n["id"]: [] for n in nodes_raw}
    upstream: dict[str, list] = {n["id"]: n.get("inputs", []) for n in nodes_raw}

    for node in nodes_raw:
        for parent_id in node.get("inputs", []):
            if parent_id in downstream:
                downstream[parent_id].append(node["id"])

    # Topological sort (Kahn's algorithm)
    in_degree = {n["id"]: len(n.get("inputs", [])) for n in nodes_raw}
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    levels: list[list[str]] = []
    visited = set()

    while queue:
        levels.append(queue[:])
        next_q = []
        for nid in queue:
            visited.add(nid)
            for child in downstream.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_q.append(child)
        queue = next_q

    # Render level by level
    console.print(f"\n[bold]Workflow:[/bold] {workflow.get('name', workflow.get('id', ''))}")
    console.print(f"[dim]{len(nodes_raw)} nodes[/dim]\n")

    for level_idx, level in enumerate(levels):
        panels = []
        for nid in level:
            node = id_to_node[nid]
            ntype = node.get("type", "?")
            params = node.get("params", {})
            # Show first 2 non-empty params for brevity
            param_lines = [f"[dim]{k}[/dim]: {str(v)[:40]}"
                           for k, v in params.items()
                           if v and k not in ("webhook_url",)][:2]
            body = Text()
            body.append(f"[{ntype}]\n", style="bold cyan")
            body.append(f"id: {nid}\n", style="dim")
            for pl in param_lines:
                body.append(pl + "\n")
            panels.append(Panel(body, expand=False, border_style="blue"))

        console.print(Columns(panels, equal=False, expand=False))

        # Draw connectors between levels
        if level_idx < len(levels) - 1:
            # Show which nodes connect forward
            arrows = []
            for nid in level:
                children = downstream.get(nid, [])
                if children:
                    arrows.append(f"[dim]{nid}[/dim] [bold]──►[/bold] {', '.join(children)}")
            if arrows:
                for a in arrows:
                    console.print(f"    {a}")
            console.print()


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("list")
def list_workflows(
    limit: Optional[int] = typer.Option(None, "--limit", help="Max workflows to show"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """List all your saved workflows."""
    try:
        data = _get("get-workflow-defs")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    workflows = data if isinstance(data, list) else data.get("workflows", [data])
    if limit:
        workflows = workflows[:limit]

    if output_json:
        out.print_json(json.dumps(workflows))
        return

    if not workflows:
        console.print("[dim]No workflows found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description", style="italic")
    table.add_column("Nodes", justify="right")
    table.add_column("Created")
    for w in workflows:
        nodes = w.get("nodes") or w.get("data", {}).get("nodes") or []
        desc = w.get("description") or ""
        if len(desc) > 50: desc = desc[:47] + "..."
        table.add_row(
            str(w.get("id", "")),
            w.get("name", "(unnamed)"),
            w.get("category", "General"),
            desc,
            str(len(nodes)),
            str(w.get("created_at", ""))[:10],
        )
    console.print(table)


@app.command("discover")
def discover_workflows(
    query: Optional[str] = typer.Argument(None, help="Optional search intent (ignored locally, used for LLM context)"),
    limit: int = typer.Option(50, "--limit", help="Max matches to return for the LLM to analyze"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """
    List workflows with their descriptions so an AI agent can find the best match.
    """
    try:
        data = _get("get-workflow-defs")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    workflows = data if isinstance(data, list) else data.get("workflows", [data])
    
    # We rely on the calling LLM agent to do the semantic matching, so we return all available ones.
    matches = workflows

    if output_json:
        out.print_json(json.dumps(matches[:limit]))
        return

    if not matches:
        console.print(f"[dim]No workflows found in your account.[/dim]")
        return

    if query:
        console.print(f"[bold]Evaluating workflows for:[/bold] '{query}'")
    else:
        console.print(f"[bold]Workflows available for discovery:[/bold]")

    from rich.table import Table
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description", style="italic")
    for w in matches[:limit]:
        desc = w.get("description") or ""
        if len(desc) > 80: desc = desc[:77] + "..."
        table.add_row(
            str(w.get("id")), 
            w.get("name"),
            w.get("category", "General"),
            desc
        )
    console.print(table)
    
    if matches:
        console.print(f"\n[green]Best Match ID:[/green] [bold]{matches[0].get('id')}[/bold]")


@app.command("templates")
def list_templates(
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """List available workflow templates."""
    try:
        data = _get("get-template-workflows")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    templates = data if isinstance(data, list) else data.get("workflows", [])
    if output_json:
        out.print_json(json.dumps(templates))
        return

    from rich.table import Table
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name")
    table.add_column("Nodes", justify="right")
    for t in templates:
        nodes = t.get("nodes") or t.get("data", {}).get("nodes") or []
        table.add_row(str(t.get("id", "")), t.get("name", ""), str(len(nodes)))
    console.print(table)


@app.command("get")
def get_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    no_viz: bool = typer.Option(False, "--no-viz", help="Skip ASCII visualization"),
):
    """Get a workflow definition and visualize its node graph."""
    try:
        data = _get(f"get-workflow-def/{workflow_id}")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    if output_json:
        out.print_json(json.dumps(data))
        return

    if not no_viz:
        _visualize(data)

    # Also show API inputs
    try:
        inputs = _get(f"{workflow_id}/api-inputs")
        if inputs:
            console.print("\n[bold]API Inputs:[/bold]")
            from rich.table import Table
            t = Table(show_header=True, header_style="bold")
            t.add_column("Node ID")
            t.add_column("Parameter")
            t.add_column("Type")
            t.add_column("Required")
            for node_id, params in (inputs.get("inputs") or {}).items():
                for param, meta in (params or {}).items():
                    t.add_row(node_id, param,
                              meta.get("type", "any"),
                              "[green]yes[/green]" if meta.get("required") else "no")
            console.print(t)
    except Exception:
        pass


@app.command("create")
def create_workflow(
    prompt: str = typer.Argument(..., help="Describe the workflow you want to build"),
    name: str = typer.Option("", "--name", "-n", help="Workflow name (optional)"),
    sync: bool = typer.Option(True, "--sync/--async", help="Wait for generation (default: on)"),
    view: bool = typer.Option(False, "--view", help="Open workflow in browser after creation"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Generate a new workflow from a text description using the AI architect.

    Examples:

    \\b
    muapi workflow create "take a text prompt, generate an image with flux, then upscale it"
    muapi workflow create "text prompt → video with kling → add lipsync audio"
    """
    body = {"prompt": prompt, "sync": sync}
    if name:
        body["name"] = name

    try:
        data = _post("architect", body)
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    # If async, returns request_id to poll
    if not sync and "request_id" in data:
        if output_json:
            out.print_json(json.dumps(data))
        else:
            console.print(f"[green]Workflow generation started.[/green] request_id: [bold]{data['request_id']}[/bold]")
            console.print(f"Poll: [bold]muapi workflow poll {data['request_id']}[/bold]")
        return

    if output_json:
        out.print_json(json.dumps(data))
        return

    wf = data.get("workflow") or data
    console.print(f"[green]Workflow created:[/green] [bold]{wf.get('id', '')}[/bold]  {wf.get('name', '')}")
    if view:
        import webbrowser
        url = _WORKFLOW_BASE.replace("/workflow", "") + f"/workflow/{wf.get('id')}"
        console.print(f"[dim]Opening:[/dim] {url}")
        webbrowser.open(url)
    _visualize(wf)


@app.command("edit")
def edit_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID to edit"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Describe the change to make"),
    sync: bool = typer.Option(True, "--sync/--async"),
    view: bool = typer.Option(False, "--view", help="Open workflow in browser after edit"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Edit an existing workflow using natural language.

    Examples:

    \\b
    muapi workflow edit abc123 --prompt "add a face-swap step after the image generation"
    muapi workflow edit abc123 --prompt "change the video model to veo3"
    """
    body = {"prompt": prompt, "workflow_id": workflow_id, "sync": sync}

    try:
        data = _post("architect", body)
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    if not sync and "request_id" in data:
        if output_json:
            out.print_json(json.dumps(data))
        else:
            console.print(f"[green]Edit started.[/green] request_id: [bold]{data['request_id']}[/bold]")
        return

    if output_json:
        out.print_json(json.dumps(data))
        return

    wf = data.get("workflow") or data
    console.print(f"[green]Workflow updated:[/green] [bold]{wf.get('id', '')}[/bold]")
    if view:
        import webbrowser
        url = _WORKFLOW_BASE.replace("/workflow", "") + f"/workflow/{wf.get('id')}"
        console.print(f"[dim]Opening:[/dim] {url}")
        webbrowser.open(url)
    _visualize(wf)


@app.command("poll")
def poll_architect(
    request_id: str = typer.Argument(..., help="request_id from async workflow create/edit"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Poll an async workflow generation until complete."""
    deadline = time.time() + _MAX_WAIT
    last_status = ""
    while time.time() < deadline:
        try:
            data = _get(f"poll-architect/{request_id}/result")
        except httpx.HTTPStatusError as e:
            error_exit(str(e), exitcodes.ERROR)

        status = data.get("status", "")
        if status != last_status:
            console.print(f"[dim]status: {status}[/dim]")
            last_status = status

        if status == "completed":
            if output_json:
                out.print_json(json.dumps(data))
            else:
                wf = data.get("workflow") or data.get("outputs", [{}])[0] if data.get("outputs") else data
                console.print("[green]Workflow ready.[/green]")
                _visualize(wf if isinstance(wf, dict) else data)
            return
        if status == "failed":
            error_exit(f"Workflow generation failed: {data.get('error', 'unknown')}", exitcodes.ERROR)

        time.sleep(_POLL_INTERVAL)

    error_exit(f"Timed out waiting for workflow generation.", exitcodes.TIMEOUT)


@app.command("run")
def run_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID to run"),
    webhook: str = typer.Option("", "--webhook", help="Webhook URL for completion notification"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Poll until complete (default: on)"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    download: str = typer.Option("", "--download", "-d", help="Directory to download output files"),
):
    """Start a workflow run (uses last saved inputs)."""
    body = {}
    if webhook:
        body["webhook_url"] = webhook

    try:
        data = _post(f"{workflow_id}/run", body)
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    run_id = data.get("run_id") or data.get("id")
    if not run_id:
        if output_json:
            out.print_json(json.dumps(data))
        else:
            console.print(data)
        return

    console.print(f"[green]Run started.[/green] run_id: [bold]{run_id}[/bold]")

    if not wait:
        if output_json:
            out.print_json(json.dumps(data))
        return

    _wait_for_run(run_id, output_json=output_json, download=download)


@app.command("execute")
def execute_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    input: list[str] = typer.Option([], "--input", "-i",
        help="Input as node_id.param=value (repeatable). E.g. --input node1.prompt='a cat'"),
    webhook: str = typer.Option("", "--webhook"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    download: str = typer.Option("", "--download", "-d"),
):
    """Execute a workflow with specific inputs.

    Examples:

    \\b
    muapi workflow execute abc123 --input "node1.prompt=a glowing crystal"
    muapi workflow execute abc123 --input "text-1.prompt=sunset" --input "img-gen.model=flux-dev"
    """
    # Parse --input node_id.param=value into nested dict
    inputs: dict = {}
    for item in input:
        if "=" not in item or "." not in item.split("=")[0]:
            error_exit(f"Invalid --input format: '{item}'. Use node_id.param=value", exitcodes.VALIDATION)
        key, value = item.split("=", 1)
        node_id, param = key.split(".", 1)
        inputs.setdefault(node_id, {})[param] = value

    body: dict = {"inputs": inputs}
    if webhook:
        body["webhook_url"] = webhook

    try:
        data = _post(f"{workflow_id}/api-execute", body)
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    run_id = data.get("run_id") or data.get("id")
    if not run_id:
        if output_json:
            out.print_json(json.dumps(data))
        else:
            console.print(data)
        return

    console.print(f"[green]Execution started.[/green] run_id: [bold]{run_id}[/bold]")

    if not wait:
        if output_json:
            out.print_json(json.dumps(data))
        return

    _wait_for_run(run_id, output_json=output_json, download=download)


@app.command("run-interactive")
def interactive_run(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    webhook: str = typer.Option("", "--webhook"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    download: str = typer.Option("", "--download", "-d"),
):
    """Run a workflow and interactively prompt for required inputs."""
    try:
        # 1. Fetch Input Schema
        inputs_resp = _get(f"{workflow_id}/api-inputs")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    # Note: schema structure from server is nested
    input_props = inputs_resp.get("input_data", {}).get("properties", {})
    if not input_props:
        console.print("[yellow]This workflow has no interactive input nodes.[/yellow]")
        run_workflow(workflow_id, webhook=webhook, wait=wait, download=download)
        return

    console.print(f"[bold]Interactive Run:[/bold] {workflow_id}")
    console.print("[dim]Please provide values for the following inputs:[/dim]\n")

    input_pairs = []
    for node_id, meta in input_props.items():
        title = meta.get("title", node_id)
        desc = meta.get("description", "")
        example = meta.get("examples", [""])[0] if meta.get("examples") else ""
        name = meta.get("name", "value")

        prompt_str = f"[bold cyan]* {title}[/bold cyan] ({node_id})"
        if desc:
            prompt_str += f"\n  [dim]{desc}[/dim]"
        if example:
            prompt_str += f"\n  [dim]Example: {example}[/dim]"
        
        console.print(prompt_str)
        val = typer.prompt(f"  Enter {title}")
        
        # Format as expected by 'execute' command logic
        input_pairs.append(f"{node_id}.{name}={val}")

    # 2. Reuse execute_workflow logic
    execute_workflow(
        workflow_id=workflow_id,
        input=input_pairs,
        webhook=webhook,
        wait=wait,
        download=download
    )


@app.command("status")
def run_status(
    run_id: str = typer.Argument(..., help="Run ID"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
):
    """Get the current node-by-node status of a workflow run."""
    try:
        data = _get(f"run/{run_id}/status")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    if output_json:
        out.print_json(json.dumps(data))
        return

    _print_run_status(data)


@app.command("outputs")
def run_outputs(
    run_id: str = typer.Argument(..., help="Run ID"),
    output_json: bool = typer.Option(False, "--output-json", "-j"),
    download: str = typer.Option("", "--download", "-d", help="Download output files to directory"),
):
    """Get the final outputs of a completed workflow run."""
    try:
        data = _get(f"run/{run_id}/api-outputs")
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)

    if output_json:
        out.print_json(json.dumps(data))
        return

    urls = _extract_output_urls(data)
    if urls:
        console.print("[bold green]Outputs:[/bold green]")
        for url in urls:
            console.print(f"  {url}")
        if download:
            _download_urls(urls, download)
    else:
        console.print(data)


@app.command("delete")
def delete_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a workflow definition."""
    if not yes:
        typer.confirm(f"Delete workflow {workflow_id}?", abort=True)
    try:
        data = _get(f"delete-workflow-def/{workflow_id}")  # DELETE verb needed
    except Exception:
        # Try DELETE method
        resp = httpx.delete(
            f"{_WORKFLOW_BASE}/delete-workflow-def/{workflow_id}",
            headers=_headers(), timeout=30.0
        )
        if resp.status_code >= 400:
            error_exit(resp.text, exitcodes.ERROR)
        data = resp.json()
    console.print(f"[green]Workflow {workflow_id} deleted.[/green]")


@app.command("rename")
def rename_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    name: str = typer.Option(..., "--name", "-n", help="New name"),
):
    """Rename a workflow."""
    try:
        data = _post(f"update-name/{workflow_id}", {"name": name})
    except httpx.HTTPStatusError as e:
        error_exit(str(e), exitcodes.ERROR)
    console.print(f"[green]Renamed to:[/green] {name}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_run_status(data: dict) -> None:
    """Pretty-print node-by-node run status."""
    from rich.table import Table
    nodes = data.get("nodes") or data.get("node_statuses") or []
    if isinstance(nodes, dict):
        flat_nodes = []
        for v in nodes.values():
            if isinstance(v, list):
                flat_nodes.extend(v)
            else:
                flat_nodes.append(v)
        nodes = flat_nodes
        
    overall = data.get("status", "")

    console.print(f"[bold]Run status:[/bold] {overall}")
    if not nodes:
        console.print(data)
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Node ID")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Output")
    for n in nodes:
        status = n.get("status", "")
        color = "green" if status == "completed" else "yellow" if status == "processing" else "red" if status == "failed" else "dim"
        outputs = n.get("outputs") or []
        out_str = outputs[0][:60] + "…" if outputs else ""
        table.add_row(
            n.get("id", ""),
            n.get("type", ""),
            f"[{color}]{status}[/{color}]",
            out_str,
        )
    console.print(table)


def _extract_output_urls(data: dict) -> list[str]:
    urls = []
    outputs = data.get("outputs") or []
    for item in outputs:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            # Handle both formats: {"outputs": [...]} and {"value": "url"}
            if item.get("outputs"):
                urls.extend(item["outputs"])
            elif item.get("value"):
                urls.append(item["value"])
    return urls


def _download_urls(urls: list[str], dest: str) -> None:
    import pathlib
    pathlib.Path(dest).mkdir(parents=True, exist_ok=True)
    for url in urls:
        fname = url.split("?")[0].split("/")[-1] or "output"
        path = pathlib.Path(dest) / fname
        console.print(f"  Downloading → {path}")
        with httpx.Client() as c:
            r = c.get(url, follow_redirects=True, timeout=120.0)
            path.write_bytes(r.content)


def _wait_for_run(run_id: str, output_json: bool = False, download: str = "") -> None:
    """Poll run/{run_id}/status until done, then fetch outputs."""
    deadline = time.time() + _MAX_WAIT
    last_status = ""

    with console.status("[dim]Waiting for workflow run…[/dim]") as spinner:
        while time.time() < deadline:
            try:
                data = _get(f"run/{run_id}/status")
            except httpx.HTTPStatusError as e:
                error_exit(str(e), exitcodes.ERROR)

            status = data.get("status", "")
            if status != last_status:
                spinner.update(f"[dim]{status}[/dim]")
                last_status = status

            if status == "completed":
                spinner.stop()
                _print_run_status(data)
                # Fetch API outputs
                try:
                    out_data = _get(f"run/{run_id}/api-outputs")
                    urls = _extract_output_urls(out_data)
                    if urls:
                        console.print("\n[bold green]Outputs:[/bold green]")
                        for url in urls:
                            console.print(f"  {url}")
                        if download:
                            _download_urls(urls, download)
                    elif output_json:
                        out.print_json(json.dumps(out_data))
                except Exception:
                    pass
                return

            if status == "failed":
                spinner.stop()
                _print_run_status(data)
                error_exit("Workflow run failed.", exitcodes.ERROR)

            time.sleep(_POLL_INTERVAL)

    error_exit(f"Timed out after {_MAX_WAIT}s. Run ID: {run_id}", exitcodes.TIMEOUT)

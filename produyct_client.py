import asyncio
import sys
from mcp import Client, StdioServerParameters
from mcp.client import ClientRequestContext
from mcp.types import ElicitRequestParams, ElicitRequestURLParams, ElicitResult, TextContent

async def handle_elicitation(context: ClientRequestContext, params: ElicitRequestParams) -> ElicitResult:
    """Called when a tool result says input_required with an elicitation/create request."""
    print("[CLIENT] the server is asking the user for input.", flush=True)

    if isinstance(params, ElicitRequestURLParams):          # URL mode
        print(f"  {params.message}\n  Open this link to continue: {params.url}")
        ok = input("  Open it? [y/N]: ").strip().lower() == "y"
        return ElicitResult(action="accept" if ok else "decline")

    print(f"\n  {params.message}")                           # form mode
    choice = input("  Proceed? [Enter = fill form,  d = decline,  c = cancel]: ").strip().lower()
    if choice == "d":
        return ElicitResult(action="decline")
    if choice == "c":
        return ElicitResult(action="cancel")
    return ElicitResult(action="accept", content=fill_form(params.requested_schema))

def fill_form(schema: dict) -> dict:
    """Build a console 'form' from the requestedSchema the server sent."""
    answers = {}
    for name, prop in schema["properties"].items():
        label = prop.get("description", name)
        default = prop.get("default")
        if "enum" in prop:
            label += f" {prop['enum']}"
        hint = f" [default: {default}]" if default is not None else ""
        raw = input(f"  - {label}{hint}: ").strip()
        if raw == "" and default is not None:
            answers[name] = default
        elif prop["type"] == "boolean":
            answers[name] = raw.lower() in ("y", "yes", "true", "1")
        elif prop["type"] == "integer":
            answers[name] = int(raw)
        elif prop["type"] == "number":
            answers[name] = float(raw)
        else:
            answers[name] = raw
    return answers

async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["product_server.py"])
    async with Client(params, elicitation_callback=handle_elicitation) as client:
        print(f"[CLIENT] connected (protocol {client.protocol_version}).")
        name = input("Product name [EcoBottle]: ").strip() or "EcoBottle"
        # The Client runs the input_required -> answer -> retry loop for you.
        result = await client.call_tool("launch_product", {"product_name": name})
        print("\n--- tool result ---")
        print("\n".join(b.text for b in result.content if isinstance(b, TextContent)))

if __name__ == "__main__":
    asyncio.run(main())

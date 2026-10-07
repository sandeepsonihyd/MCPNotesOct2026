"""
product_server.py - an MCP server that asks the user for input mid-call (elicitation).
"""
import sys
from typing import Literal
from pydantic import BaseModel, Field
from mcp.server import MCPServer
from mcp.server.elicitation import render_elicitation_schema
from mcp.server.mcpserver import Context
from mcp.types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult

mcp = MCPServer("product server")

def log(msg: str) -> None:
    """Narrate to STDERR (stdout is reserved for the MCP protocol)."""
    print(f"[SERVER] {msg}", file=sys.stderr, flush=True)

# The form the user will see. MCPServer turns this Pydantic model into the
# requestedSchema of the elicitation/create request (flat, primitive fields only).
class LaunchConfirmation(BaseModel):
    confirmLaunch: bool = Field(description="Confirm you want to launch this product")
    price: float = Field(default=29.99, ge=0, description="Retail price (USD)")
    initialStock: int = Field(default=100, ge=0, description="Initial stock quantity")
    shippingSpeed: Literal["standard", "priority", "overnight"] = Field(default="standard", description="Shipping speed to offer at launch")

LAUNCH_KEY = "launch_details"  # key of the question in input_requests / input_responses

@mcp.tool()
async def launch_product(product_name: str, ctx: Context) -> str | InputRequiredResult:
    """Launch a product, confirming pricing and inventory with the user first."""
    # Protocol 2026-07-28 has no server->client back-channel, so a tool can't
    # `await ctx.elicit()`. Instead the body runs twice: round 1 returns the
    # question, the client answers and retries, round 2 reads the answer.
    answer = (ctx.input_responses or {}).get(LAUNCH_KEY)

    if answer is None:
        log(f"asking the user to confirm launch details for '{product_name}'")
        return InputRequiredResult(
            input_requests={
                LAUNCH_KEY: ElicitRequest(
                    params=ElicitRequestFormParams(
                        message=f"Please confirm launch details for '{product_name}':",
                        requested_schema=render_elicitation_schema(LaunchConfirmation),
                    )
                )
            }
        )

    # --- you are now "halfway" through the tool, with the user's answer in hand ---
    if answer.action == "decline":
        return "User declined to provide launch details."
    if answer.action != "accept":
        return "User cancelled the launch flow."

    data = LaunchConfirmation.model_validate(answer.content)
    if not data.confirmLaunch:
        return "Launch not confirmed by user."
    log("user accepted, finalizing launch")
    return (
        f"Launched {product_name}! Price: ${data.price:.2f}, "
        f"Initial stock: {data.initialStock}, Shipping: {data.shippingSpeed}."
    )

if __name__ == "__main__":
    log("product-server starting on stdio...")
    mcp.run()  # stdio transport by default

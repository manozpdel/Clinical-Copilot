"""CLI entry point that prints a usage analytics summary."""

import asyncio

from app.core.logging import configure_logging, get_logger
from database.session import SessionLocal
from security.analytics import (
    average_latency_ms,
    average_tokens_per_request,
    daily_usage,
    monthly_usage,
    most_active_users,
    most_expensive_conversations,
    weekly_usage,
)


async def print_usage_report() -> None:
    """Fetch and print daily/weekly/monthly usage and top-user/conversation lists."""
    async with SessionLocal() as db:
        daily = await daily_usage(db)
        weekly = await weekly_usage(db)
        monthly = await monthly_usage(db)
        top_users = await most_active_users(db, limit=5)
        top_conversations = await most_expensive_conversations(db, limit=5)
        avg_latency = await average_latency_ms(db)
        avg_tokens = await average_tokens_per_request(db)

    print("-" * 40)
    print(f"Daily requests:   {daily.request_count}")
    print(f"Daily tokens:     {daily.total_tokens}")
    print(f"Daily cost:       ${daily.total_cost_usd:.4f}")
    print()
    print(f"Weekly requests:  {weekly.request_count}")
    print(f"Weekly tokens:    {weekly.total_tokens}")
    print(f"Weekly cost:      ${weekly.total_cost_usd:.4f}")
    print()
    print(f"Monthly requests: {monthly.request_count}")
    print(f"Monthly tokens:   {monthly.total_tokens}")
    print(f"Monthly cost:     ${monthly.total_cost_usd:.4f}")
    print()
    print(f"Average latency:  {avg_latency:.2f}ms")
    print(f"Average tokens:   {avg_tokens:.1f}")
    print("-" * 40)
    print("Most active users:")
    for user in top_users:
        print(f"  {user.user_id}: {user.request_count} requests, ${user.total_cost_usd:.4f}")
    print("Most expensive conversations:")
    for conversation in top_conversations:
        print(
            f"  {conversation.conversation_id}: "
            f"${conversation.total_cost_usd:.4f} ({conversation.request_count} requests)"
        )
    print("-" * 40)


def main() -> None:
    """Run and print the usage report."""
    configure_logging()
    get_logger(__name__)
    asyncio.run(print_usage_report())


if __name__ == "__main__":
    main()

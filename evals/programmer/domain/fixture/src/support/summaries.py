from support.tickets import Ticket


def format_digest_line(ticket: Ticket) -> str:
    """Return the line that represents `ticket` in the daily digest."""
    return f"#{ticket.id} {ticket.subject} ({len(ticket.messages)} messages)"

import logging
from typing import Dict, Union, List, cast, Any

import jira

import joft.models
import joft.base

# Type aliases for better readability
ReferencePoolType = Dict[str, Union[str, jira.Issue, List[Any]]]


def create_ticket(
    action: joft.models.CreateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Create a new JIRA ticket based on the action configuration.

    Args:
        action: The create ticket action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        jira.exceptions.JIRAError: If ticket creation fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)
    logging.debug(f"Creating new ticket of type: {action.fields['issuetype']['name']}")
    logging.debug(f"Payload:\n{action.fields}")

    new_issue: jira.Issue = jira_session.create_issue(action.fields)

    logging.info(f"New Jira ticket created: {new_issue.permalink()}")

    if action.object_id:
        reference_pool[action.object_id] = new_issue


def update_ticket(
    action: joft.models.UpdateTicketAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Update an existing JIRA ticket based on the action configuration.

    Args:
        action: The update ticket action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        Exception: If referenced ticket doesn't exist
        jira.exceptions.JIRAError: If ticket update fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = cast(jira.Issue, reference_pool[action.reference_id])

    logging.debug(f"Updating ticket '{ticket_to.key}'")
    logging.debug(f"Payload:\n{action.fields}")

    update_ops = action.fields.pop("update", None)
    if update_ops:
        ticket_to.update(action.fields, update=update_ops)
    else:
        ticket_to.update(action.fields)

    logging.info(f"Ticket '{ticket_to.key}' updated.")

    if action.object_id:
        reference_pool[action.object_id] = ticket_to


def link_issues(
    action: joft.models.LinkIssuesAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Create a link between two JIRA issues.

    Args:
        action: The link issues action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        jira.exceptions.JIRAError: If link creation fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    logging.info("Linking issues...")
    logging.info(f"Link type: {action.fields['type']}")
    logging.info(f"Linking From Issue: {action.fields['inward_issue']}")
    logging.info(f"Linking To Issue: {action.fields['outward_issue']}")

    jira_session.create_issue_link(
        action.fields["type"],
        action.fields["inward_issue"],
        action.fields["outward_issue"],
    )


def add_to_sprint(
    action: joft.models.AddToSprintAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Add a referenced JIRA issue to a sprint.

    The ``sprint`` field can be either:
    - ``"next"``: automatically resolves to the next future sprint on the board
      (the first future sprint by start date, or the active sprint as fallback).
    - A literal sprint name (e.g. ``"Sprint 50"``): looked up by exact name.

    Args:
        action: The add-to-sprint action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        Exception: If referenced ticket doesn't exist, sprint is not found,
            or the board has no eligible sprints
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket: jira.Issue = cast(jira.Issue, reference_pool[action.reference_id])

    if action.sprint == "next":
        sprint_data = _resolve_next_sprint(jira_session, action.board_id)
    else:
        sprints = jira_session.sprints_by_name(action.board_id, state="active,future")
        if action.sprint not in sprints:
            raise Exception(
                f"Sprint '{action.sprint}' not found on board {action.board_id}. "
                f"Available sprints: {list(sprints.keys())}"
            )
        sprint_data = sprints[action.sprint]

    sprint_id = sprint_data["id"]
    sprint_name = sprint_data["name"]

    logging.info(f"Adding '{ticket.key}' to sprint '{sprint_name}' (id={sprint_id})")
    jira_session.add_issues_to_sprint(sprint_id, [ticket.key])

    if action.object_id:
        reference_pool[action.object_id] = ticket


def _resolve_next_sprint(
    jira_session: jira.JIRA,
    board_id: int,
) -> Dict[str, Any]:
    """Resolve the next sprint on a board.

    Looks for future sprints first (sorted by startDate), falling back to the
    active sprint if no future sprints exist.

    Args:
        jira_session: Active JIRA client session
        board_id: The Jira board ID

    Returns:
        The raw sprint data dict containing at least 'id' and 'name'.

    Raises:
        Exception: If no future or active sprints exist on the board.
    """
    future_sprints = jira_session.sprints(board_id, state="future")
    if future_sprints:
        future_sprints.sort(
            key=lambda s: s.raw.get("startDate", "9999-12-31")
        )
        return future_sprints[0].raw

    active_sprints = jira_session.sprints(board_id, state="active")
    if active_sprints:
        return active_sprints[0].raw

    raise Exception(
        f"No future or active sprints found on board {board_id}."
    )


def transition_issue(
    action: joft.models.TransitionAction,
    jira_session: jira.JIRA,
    reference_pool: ReferencePoolType,
) -> None:
    """Transition a JIRA issue to a new status.

    Args:
        action: The transition action configuration
        jira_session: Active JIRA client session
        reference_pool: Dictionary containing referenced values for field substitution

    Raises:
        Exception: If referenced ticket doesn't exist
        jira.exceptions.JIRAError: If transition fails
    """
    joft.base.update_reference_pool(action.reference_data, reference_pool)
    joft.base.apply_reference_pool_to_payload(reference_pool, action.fields)

    if action.reference_id not in reference_pool:
        raise Exception(
            (
                f"Invalid reference id '{action.reference_id}'! "
                "You are referencing something that does not exist!"
            )
        )

    ticket_to: jira.Issue = cast(jira.Issue, reference_pool[action.reference_id])

    logging.info(f"Transitioning issue '{ticket_to.key}'...")
    logging.info(
        f"Changing status from '{ticket_to.fields.status}' to '{action.transition}'"
    )
    logging.info(f"With comment: \n{action.comment}")

    jira_session.transition_issue(
        ticket_to, action.transition, action.fields, action.comment
    )

    if action.object_id:
        reference_pool[action.object_id] = ticket_to

import unittest.mock

import pytest

import joft.actions
import joft.models


def test_create_ticket():
    """Testing the execution of the create-ticket action"""
    mock_jira_session = unittest.mock.MagicMock()
    create_ticket_template = {
        "object_id": "ticket",
        "type": "create-ticket",
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "summary": "Test the creation of ticket",
            "description": "Test the creation of ticket",
        },
    }
    mock_reference_pool = {}

    new_issue = unittest.mock.MagicMock()
    new_issue.key = "TEST-456"
    mock_jira_session.create_issue.side_effect = [new_issue]

    create_ticket_action = joft.models.CreateTicketAction(**create_ticket_template)
    joft.actions.create_ticket(
        create_ticket_action, mock_jira_session, mock_reference_pool
    )

    # Assertions
    mock_jira_session.create_issue.assert_called_once_with(create_ticket_action.fields)
    assert "ticket" in mock_reference_pool
    assert mock_reference_pool["ticket"].key == "TEST-456"


def test_create_ticket_with_references():
    """
    Testing the execution of the create-ticket action with references to a ticket already
    present in the reference_pool.
    """

    mock_jira_session = unittest.mock.MagicMock()
    create_ticket_template = {
        "object_id": "ticket",
        "type": "create-ticket",
        "reuse_data": [
            {"reference_id": "issue", "fields": ["key", "summary", "description"]},
        ],
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "summary": "${issue.key} - ${issue.summary}",
            "description": "${issue.description}",
        },
    }
    mock_reference_pool = {}

    mock_reference_issue = unittest.mock.MagicMock()
    mock_reference_issue.key = "TEST-123"
    mock_reference_issue.fields.summary = "Hello from referenced issue summary"
    mock_reference_issue.fields.description = "Hello from referenced issue description"

    mock_reference_pool["issue"] = mock_reference_issue

    def create_issue(fields):
        new_issue = unittest.mock.MagicMock()
        new_issue.key = "TEST-456"
        new_issue.fields.summary = fields["summary"]
        new_issue.fields.description = fields["description"]

        return new_issue

    mock_jira_session.create_issue = create_issue

    create_ticket_action = joft.models.CreateTicketAction(**create_ticket_template)
    joft.actions.create_ticket(
        create_ticket_action, mock_jira_session, mock_reference_pool
    )

    # Assertions
    assert "ticket" in mock_reference_pool

    assert mock_reference_pool["ticket"].key == "TEST-456"

    key = mock_reference_pool["issue"].key
    summary = mock_reference_pool["issue"].fields.summary
    description = mock_reference_pool["issue"].fields.description

    assert f"{key} - {summary}" == mock_reference_pool["ticket"].fields.summary
    assert description == mock_reference_pool["ticket"].fields.description


def test_reuse_data_must_be_list():
    create_ticket_template = {
        "object_id": "ticket",
        "type": "create-ticket",
        "reuse_data": {"reference_id": "test"},
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "summary": "${issue.key} - ${issue.summary}",
            "description": "${issue.description}",
        },
    }

    with pytest.raises(Exception) as ex:
        joft.models.CreateTicketAction(**create_ticket_template)

    # Assertions
    assert "must be a list" in ex.value.args[0]


def test_update_ticket():
    """We test the update-ticket action and it succesfull execution."""
    update_ticket_template = {
        "object_id": "update-story",
        "type": "update-ticket",
        "reference_id": "issue",
        "fields": {"customAfield_12311140": "test update"},
    }
    update_ticket_action = joft.models.UpdateTicketAction(**update_ticket_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_reference_pool = {}

    mock_reference_issue = unittest.mock.MagicMock()
    mock_reference_issue.key = "TEST-123"
    mock_reference_issue.fields.summary = "Hello from referenced issue summary"
    mock_reference_issue.fields.description = "Hello from referenced issue description"

    mock_reference_pool["issue"] = mock_reference_issue
    joft.actions.update_ticket(
        update_ticket_action, mock_jira_session, mock_reference_pool
    )

    mock_reference_issue.update.assert_called_once_with(update_ticket_action.fields)


def test_update_ticket_with_update_operations():
    """Test that the 'update' key is separated from fields and sent correctly."""
    update_ticket_template = {
        "object_id": "label-issue",
        "type": "update-ticket",
        "reference_id": "issue",
        "fields": {
            "update": {
                "labels": [{"add": "has-triaging-spike"}],
            },
        },
    }
    update_ticket_action = joft.models.UpdateTicketAction(**update_ticket_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_reference_issue = unittest.mock.MagicMock()
    mock_reference_issue.key = "RHEL-999"
    mock_reference_pool = {"issue": mock_reference_issue}

    joft.actions.update_ticket(
        update_ticket_action, mock_jira_session, mock_reference_pool
    )

    mock_reference_issue.update.assert_called_once_with(
        {}, update={"labels": [{"add": "has-triaging-spike"}]}
    )


def test_update_ticket_reference_invalid():
    """We should raise if a reference_id is invalid."""

    bad_reference_id = "bad_reference_id"

    update_ticket_template = {
        "object_id": "update-story",
        "type": "update-ticket",
        "reference_id": bad_reference_id,
        "fields": {"customAfield_12311140": "test update"},
    }
    update_ticket_action = joft.models.UpdateTicketAction(**update_ticket_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_reference_pool = {}

    with pytest.raises(Exception) as ex:
        joft.actions.update_ticket(
            update_ticket_action, mock_jira_session, mock_reference_pool
        )

    # Assertions
    assert "invalid reference id" in ex.value.args[0].lower()
    assert bad_reference_id in ex.value.args[0].lower()


def test_add_to_sprint_next():
    """Test that sprint: next resolves to the first future sprint."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "story-spike",
        "board_id": 9908,
        "sprint": "next",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_sprint = unittest.mock.MagicMock()
    mock_sprint.raw = {"id": 51, "name": "Sprint 51", "startDate": "2026-03-25"}
    mock_jira_session.sprints.return_value = [mock_sprint]

    mock_issue = unittest.mock.MagicMock()
    mock_issue.key = "SWM-100"
    mock_reference_pool = {"story-spike": mock_issue}

    joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    mock_jira_session.sprints.assert_called_once_with(9908, state="future")
    mock_jira_session.add_issues_to_sprint.assert_called_once_with(51, ["SWM-100"])


def test_add_to_sprint_next_falls_back_to_active():
    """Test that sprint: next falls back to active sprint when no future sprints exist."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "story-spike",
        "board_id": 9908,
        "sprint": "next",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_active_sprint = unittest.mock.MagicMock()
    mock_active_sprint.raw = {"id": 50, "name": "Sprint 50"}
    mock_jira_session.sprints.side_effect = [
        [],                       # future: none
        [mock_active_sprint],     # active: one
    ]

    mock_issue = unittest.mock.MagicMock()
    mock_issue.key = "SWM-100"
    mock_reference_pool = {"story-spike": mock_issue}

    joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    mock_jira_session.add_issues_to_sprint.assert_called_once_with(50, ["SWM-100"])


def test_add_to_sprint_next_no_sprints_raises():
    """Test that sprint: next raises when no future or active sprints exist."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "story-spike",
        "board_id": 9908,
        "sprint": "next",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_jira_session.sprints.side_effect = [[], []]

    mock_issue = unittest.mock.MagicMock()
    mock_reference_pool = {"story-spike": mock_issue}

    with pytest.raises(Exception) as ex:
        joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    assert "no future or active sprints" in ex.value.args[0].lower()


def test_add_to_sprint_by_name():
    """Test that an explicit sprint name is resolved by exact match."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "story-spike",
        "board_id": 9908,
        "sprint": "Sprint 50",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_jira_session.sprints_by_name.return_value = {
        "Sprint 50": {"id": 50, "name": "Sprint 50"},
    }

    mock_issue = unittest.mock.MagicMock()
    mock_issue.key = "SWM-100"
    mock_reference_pool = {"story-spike": mock_issue}

    joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    mock_jira_session.sprints_by_name.assert_called_once_with(9908, state="active,future")
    mock_jira_session.add_issues_to_sprint.assert_called_once_with(50, ["SWM-100"])


def test_add_to_sprint_unknown_name_raises():
    """Test that add-to-sprint raises when explicit sprint name is not found."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "story-spike",
        "board_id": 9908,
        "sprint": "Nonexistent Sprint",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_jira_session.sprints_by_name.return_value = {
        "Sprint 50": {"id": 50},
    }

    mock_issue = unittest.mock.MagicMock()
    mock_reference_pool = {"story-spike": mock_issue}

    with pytest.raises(Exception) as ex:
        joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    assert "Nonexistent Sprint" in ex.value.args[0]
    assert "not found" in ex.value.args[0].lower()


def test_add_to_sprint_invalid_reference_raises():
    """Test that add-to-sprint raises when reference_id is invalid."""
    action_template = {
        "type": "add-to-sprint",
        "object_id": "add-spike-to-sprint",
        "reference_id": "bad-ref",
        "board_id": 9908,
        "sprint": "next",
        "fields": {},
    }
    action = joft.models.AddToSprintAction(**action_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_reference_pool = {}

    with pytest.raises(Exception) as ex:
        joft.actions.add_to_sprint(action, mock_jira_session, mock_reference_pool)

    assert "invalid reference id" in ex.value.args[0].lower()
    assert "bad-ref" in ex.value.args[0].lower()


def test_link_ticket():
    """We test the link-issues action and it succesfull execution."""
    link_issue_template = {
        "type": "link-issues",
        "object_id": "link-bug-and-epic",
        "fields": {
            "type": "causes",
            "inward_issue": "TEST-123",
            "outward_issue": "TEST-456",
        },
    }

    link_issue_action = joft.models.LinkIssuesAction(**link_issue_template)

    mock_jira_session = unittest.mock.MagicMock()

    mock_reference_pool = {}

    joft.actions.link_issues(link_issue_action, mock_jira_session, mock_reference_pool)

    # Assertions
    link_type = link_issue_template["fields"]["type"]
    inward = link_issue_template["fields"]["inward_issue"]
    outward = link_issue_template["fields"]["outward_issue"]
    mock_jira_session.create_issue_link.assert_called_once_with(
        link_type, inward, outward
    )


def test_transition_ticket_invalid_ref_raise():
    """We transition a ticket to another status with comment"""

    bad_reference_id = "bad_ref"

    transition_issue_template = {
        "type": "transition",
        "object_id": "close-bug",
        "reference_id": bad_reference_id,
        "comment": "Closed bug by Joft",
        "transition": "Closed",
        "fields": {},
    }

    transition_action = joft.models.TransitionAction(**transition_issue_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_bug = unittest.mock.MagicMock()

    mock_reference_pool = {
        "bug": mock_bug,
    }

    with pytest.raises(Exception) as ex:
        joft.actions.transition_issue(
            transition_action, mock_jira_session, mock_reference_pool
        )

    # Assertions
    assert "invalid reference id" in ex.value.args[0].lower()
    assert bad_reference_id in ex.value.args[0].lower()


def test_transition_ticket():
    """We transition a ticket to another status with comment"""

    transition_issue_template = {
        "type": "transition",
        "object_id": "close-bug",
        "reference_id": "bug",
        "comment": "Closed bug by Joft",
        "transition": "Closed",
        "fields": {},
    }

    transition_action = joft.models.TransitionAction(**transition_issue_template)

    mock_jira_session = unittest.mock.MagicMock()
    mock_bug = unittest.mock.MagicMock()

    mock_reference_pool = {
        "bug": mock_bug,
    }

    joft.actions.transition_issue(
        transition_action, mock_jira_session, mock_reference_pool
    )

    # Assertions
    mock_jira_session.transition_issue.assert_called_once_with(
        mock_bug,
        transition_action.transition,
        transition_action.fields,
        transition_action.comment,
    )

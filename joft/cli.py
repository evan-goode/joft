import logging
import os
import sys
from typing import Dict, Any, Optional

import click
import jira

import joft.base
import joft.utils


if os.getenv("JOFT_DEBUG"):
    logging_level = logging.DEBUG
else:
    logging_level = logging.WARNING

def new_jira_session(ctx: Dict[str, Dict[str, any]]) -> jira.JIRA:
    server = ctx["jira"]["server"]
    if "pat_token" in server:
        logging.info("Authenticating with PAT (Personal Access Token)")
        token_args = {
            "token_auth": server["pat_token"]
        }
    elif "email" in server and "api_token" in server:
        logging.info(f"Authenticating as {server["email"]} using API token")
        token_args = {
            "basic_auth": (server["email"], server["api_token"])
        }
    return jira.JIRA(server["hostname"], **token_args)


@click.group()
@click.option("--config", help="Path to the config file.")
@click.pass_context
def main(ctx: click.Context, config: Optional[str] = None) -> None:
    """
    A CLI automation tool which interacts with a Jira instance and automates tasks.
    """
    ctx.obj = joft.utils.load_toml_app_config(config_path=config)


# TODO: refactor th CLI interface so it makes more sense
@main.command(name="validate")
@click.option("--template", help="File path to the template file.")
def validate(template: str) -> int:
    ret_code = joft.base.validate_template(template)
    sys.exit(ret_code)


@main.command(name="run")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def run(ctx: Dict[str, Dict[str, Any]], template: str) -> int:
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging_level)
    logging.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = new_jira_session(ctx)

    logging.info("Session established...")
    logging.info(f"Executing Jira template: {template}")

    ret_code = joft.base.execute_template(template, jira_session)

    sys.exit(ret_code)


@main.command(name="list-fields")
@click.option("--filter", "name_filter", default="", help="Case-insensitive substring to filter field names.")
@click.pass_obj
def list_fields(ctx: Dict[str, Dict[str, Any]], name_filter: str) -> None:
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging_level)
    jira_session = new_jira_session(ctx)
    print(joft.base.list_fields(jira_session, name_filter))


@main.command(name="list-issues")
@click.option("--template", help="File path to the template file.")
@click.pass_obj
def list_issues(ctx: Dict[str, Dict[str, Any]], template: str) -> None:
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging_level)
    logging.info(
        f"Establishing session with jira server: {ctx['jira']['server']['hostname']}:"
    )

    jira_session = new_jira_session(ctx)

    logging.info("Session established...")
    logging.info(f"Executing trigger from Jira template: {template}")

    print(joft.base.list_issues(template, jira_session))

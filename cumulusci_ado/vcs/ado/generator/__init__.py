class ADOReleaseNotesGenerator:
    def __init__(
        self,
        github,
        github_info,
        parser_config,
        current_tag,
        last_tag=None,
        link_pr=False,
        publish=False,
        has_issues=True,
        include_empty=False,
        version_id=None,
        trial_info=False,
        sandbox_date=None,
        production_date=None,
    ):
        pass

    def generate(self) -> str:
        # TODO: Implement the markdown logic
        return ""


class ADOParentPullRequestNotesGenerator:
    def __init__(self, github, repo, project_config):
        pass

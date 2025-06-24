from typing import Optional, Type

from cumulusci.utils.yaml.cumulusci_yml import VCSSourceModel, VCSSourceRelease
from cumulusci.vcs.vcs_source import VCSSource


class ADOSource(VCSSource):
    def __init__(self, project_config, spec: VCSSourceModel):
        super().__init__(project_config, spec)

    def __repr__(self):
        return f"<ADOSource {str(self)}>"

    def __str__(self):
        s = f"Azure DevOps: {self.repo.repo_owner}/{self.repo.repo_name}"
        if self.description:
            s += f" @ {self.description}"
        if self.commit != self.description:
            s += f" ({self.commit})"
        return s

    def __hash__(self):
        return hash((self.url, self.commit))

    @classmethod
    def source_model(cls) -> Type["ADOSourceModel"]:
        return ADOSourceModel

    def get_vcs_service(self):
        from cumulusci_ado.vcs.ado.service import get_ado_service_for_url

        return get_ado_service_for_url(self.project_config, self.url)

    def _set_additional_repo_config(self):
        from cumulusci.vcs.bootstrap import get_remote_project_config

        super()._set_additional_repo_config()
        self.repo.project_config = get_remote_project_config(
            self.repo, self.repo.default_branch
        )

    def get_ref(self):
        return self.spec.ref

    def get_tag(self):
        return "tags/" + (self.spec.tag or "")

    def get_branch(self):
        return "heads/" + (self.spec.branch or "")

    def get_release_tag(self):
        return "tags/" + (self.spec.release or "")


class ADOSourceModel(VCSSourceModel):
    """For backward compatibility."""

    azure_devops: str
    release: Optional[VCSSourceRelease]
    vcs: Optional[str]
    url: Optional[str]

    def __init__(self, **kwargs):
        # For backward compatibility, we need to set the vcs and url attributes
        # if they are not already set.
        super().__init__(**kwargs)
        self.vcs = "azure_devops"
        self.url = kwargs.get("azure_devops", None)

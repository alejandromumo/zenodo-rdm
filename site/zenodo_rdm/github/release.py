# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Zenodo-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Zenodo-RDM release class."""

import json

from flask import current_app
from invenio_github.errors import CustomGitHubMetadataError
from invenio_rdm_records.services.github.metadata import RDMReleaseMetadata
from invenio_rdm_records.services.github.release import RDMGithubRelease

from zenodo_rdm.github.schemas import CitationMetadataSchema
from zenodo_rdm.legacy.deserializers.schemas import LegacySchema


class ZenodoReleaseMetadata(RDMReleaseMetadata):
    """Zenodo release metadata class."""

    def load_extra_metadata(self):
        """Get extra metadata for ZenodoRDM."""
        zenodo_json_file_name = ".zenodo.json"
        try:
            content = self.rdm_release.retrieve_remote_file(zenodo_json_file_name)
            if not content:
                # File does not exists
                return {}
            legacy_data = {"metadata": json.loads(content.decoded.decode("utf-8"))}
            rdm_data = LegacySchema().load(legacy_data)
            return rdm_data["metadata"]
        except Exception as exc:
            current_app.logger.exception(str(exc))
            raise CustomGitHubMetadataError(
                f"Extra metadata failed for file {zenodo_json_file_name}"
            )

    def load_citation_metadata(self, data):
        """Load citation metadata for Zenodo using legacy->RDM serialization.

        Why overriding the whole method: for Zenodo-RDM, loading the CITATION.cff is not enough. We need to add an extra step
        to convert legacy Zenodo data to RDM.
        """
        if not data:
            return {}

        try:
            legacy_data = {"metadata": CitationMetadataSchema().load(data)}
            rdm_data = LegacySchema().load(legacy_data)
            return rdm_data["metadata"]
        except Exception as exc:
            current_app.logger.exception(str(exc))
            raise CustomGitHubMetadataError(f"Citation metadata serialization failed")


class ZenodoGithubRelease(RDMGithubRelease):
    """Zenodo Github release class.

    This class adds Zenodo specific metadata.
    """

    metadata_cls = ZenodoReleaseMetadata

    @property
    def metadata(self):
        """Extracts metadata to create a ZenodoRDM draft."""
        metadata = self.metadata_cls(self)
        output = metadata.default_metadata
        extra_metadata = metadata.extra_metadata

        # If `.zenodo.json` is there use it
        if extra_metadata:
            output.update(metadata.extra_metadata)
        # If not check for `CITATION.cff` and use
        else:
            citation_metadata = metadata.citation_metadata
            if citation_metadata:
                output.update(citation_metadata)

        return output

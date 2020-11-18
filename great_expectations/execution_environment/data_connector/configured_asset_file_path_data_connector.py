import copy
import logging
from typing import Dict, List, Optional, Union

import great_expectations.exceptions as ge_exceptions
from great_expectations.core.batch import BatchDefinition
from great_expectations.data_context.util import instantiate_class_from_config
from great_expectations.execution_engine import ExecutionEngine
from great_expectations.execution_environment.data_connector.asset.asset import Asset
from great_expectations.execution_environment.data_connector.file_path_data_connector import (
    FilePathDataConnector,
)

logger = logging.getLogger(__name__)


class ConfiguredAssetFilePathDataConnector(FilePathDataConnector):
    def __init__(
        self,
        name: str,
        execution_environment_name: str,
        assets: dict,
        execution_engine: Optional[ExecutionEngine] = None,
        default_regex: Optional[dict] = None,
        sorters: Optional[list] = None,
    ):
        logger.debug(f'Constructing ConfiguredAssetFilePathDataConnector "{name}".')
        super().__init__(
            name=name,
            execution_environment_name=execution_environment_name,
            execution_engine=execution_engine,
            default_regex=default_regex,
            sorters=sorters,
        )

        if assets is None:
            assets = {}
        _assets: Dict[str, Union[dict, Asset]] = assets
        self._assets = _assets
        self._build_assets_from_config(config=assets)

    @property
    def assets(self) -> Dict[str, Union[dict, Asset]]:
        return self._assets

    def _build_assets_from_config(self, config: Dict[str, dict]):
        for name, asset_config in config.items():
            if asset_config is None:
                asset_config = {}
            new_asset: Asset = self._build_asset_from_config(
                name=name, config=asset_config,
            )
            self.assets[name] = new_asset

    def _build_asset_from_config(self, name: str, config: dict):
        """Build an Asset using the provided configuration and return the newly-built Asset."""
        runtime_environment: dict = {"name": name, "data_connector": self}
        asset: Asset = instantiate_class_from_config(
            config=config,
            runtime_environment=runtime_environment,
            config_defaults={
                "module_name": "great_expectations.execution_environment.data_connector.asset",
                "class_name": "Asset",
            },
        )
        if not asset:
            raise ge_exceptions.ClassInstantiationError(
                module_name="great_expectations.execution_environment.data_connector.asset",
                package_name=None,
                class_name=config["class_name"],
            )
        return asset

    def get_available_data_asset_names(self) -> List[str]:
        """Return the list of asset names known by this data connector.

        Returns:
            A list of available names
        """
        return list(self.assets.keys())

    def _refresh_data_references_cache(self,):
        """
        """
        # Map data_references to batch_definitions
        self._data_references_cache = {}

        for data_asset_name in self.get_available_data_asset_names():
            self._data_references_cache[data_asset_name] = {}

            for data_reference in self._get_data_reference_list(
                data_asset_name=data_asset_name
            ):
                mapped_batch_definition_list: List[
                    BatchDefinition
                ] = self._map_data_reference_to_batch_definition_list(
                    data_reference=data_reference, data_asset_name=data_asset_name,
                )
                self._data_references_cache[data_asset_name][
                    data_reference
                ] = mapped_batch_definition_list

    def _get_data_reference_list(
        self, data_asset_name: Optional[str] = None
    ) -> List[str]:
        """List objects in the underlying data store to create a list of data_references.

        This method is used to refresh the cache.
        """
        asset: Optional[Asset] = self._get_asset(data_asset_name=data_asset_name)
        path_list: List[str] = self._get_data_reference_list_for_asset(asset=asset)
        return path_list

    def get_data_reference_list_count(self) -> int:
        if self._data_references_cache is None:
            raise ValueError(
                f"data references cache for {self.__class__.__name__} {self.name} has not yet been populated."
            )

        total_references: int = sum(
            [
                len(self._data_references_cache[data_asset_name])
                for data_asset_name in self._data_references_cache
            ]
        )

        return total_references

    def get_unmatched_data_references(self) -> List[str]:
        if self._data_references_cache is None:
            raise ValueError(
                '_data_references_cache is None.  Have you called "_refresh_data_references_cache()" yet?'
            )

        unmatched_data_references: List[str] = []
        for (
            data_asset_name,
            data_reference_sub_cache,
        ) in self._data_references_cache.items():
            unmatched_data_references += [
                k for k, v in data_reference_sub_cache.items() if v is None
            ]

        return unmatched_data_references

    def _get_batch_definition_list_from_cache(self) -> List[BatchDefinition]:
        batch_definition_list: List[BatchDefinition] = [
            batch_definitions[0]
            for data_reference_sub_cache in self._data_references_cache.values()
            for batch_definitions in data_reference_sub_cache.values()
            if batch_definitions is not None
        ]
        return batch_definition_list

    def _get_full_file_path(
        self, path: str, data_asset_name: Optional[str] = None
    ) -> str:
        asset: Optional[Asset] = None
        if data_asset_name:
            asset = self._get_asset(data_asset_name=data_asset_name)
        return self._get_full_file_path_for_asset(path=path, asset=asset)

    def _get_regex_config(self, data_asset_name: Optional[str] = None) -> dict:
        regex_config: dict = copy.deepcopy(self._default_regex)
        asset: Optional[Asset] = None
        if data_asset_name:
            asset = self._get_asset(data_asset_name=data_asset_name)
        if asset is not None:
            # Override the defaults
            if asset.pattern:
                regex_config["pattern"] = asset.pattern
            if asset.group_names:
                regex_config["group_names"] = asset.group_names
        return regex_config

    def _get_asset(self, data_asset_name: str) -> Asset:
        asset: Optional[Asset] = None
        if (
            data_asset_name is not None
            and self.assets
            and data_asset_name in self.assets
        ):
            asset = self.assets[data_asset_name]
        return asset

    def _get_data_reference_list_for_asset(self, asset: Optional[Asset]) -> List[str]:
        raise NotImplementedError

    def _get_full_file_path_for_asset(self, path: str, asset: Optional[Asset]) -> str:
        raise NotImplementedError

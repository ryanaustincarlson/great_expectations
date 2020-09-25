# -*- coding: utf-8 -*-

import logging
import copy
from typing import Union, List, Iterator
from ruamel.yaml.comments import CommentedMap
from great_expectations.data_context.types.base import (
    SorterConfig,
    sorterConfigSchema
)
from great_expectations.execution_environment.data_connector.data_connector import DataConnector
from great_expectations.execution_environment.data_connector.partitioner.partition import Partition
from great_expectations.execution_environment.data_connector.partitioner.sorter.sorter import Sorter
from great_expectations.core.id_dict import BatchSpec

from great_expectations.exceptions import ClassInstantiationError

from great_expectations.data_context.util import (
    instantiate_class_from_config,
)

logger = logging.getLogger(__name__)


class Partitioner(object):
    r"""
    Partitioners help
    """

    _batch_spec_type = BatchSpec  #TODO : is this really needed?
    # TODO: <Alex>What makes sense to have here, or is this even needed?</Alex>
    recognized_batch_definition_keys = {
        "sorters"
    }

    def __init__(
        self,
        name: str,
        data_connector: DataConnector,
        sorters: list = None,
        config_params: dict = None,
        **kwargs
    ):
        self._name = name
        self._data_connector = data_connector
        self._sorters = sorters
        self._config_params = config_params
        # TODO: <Alex></Alex>
        self._sorters_cache = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def data_connector(self) -> DataConnector:
        return self._data_connector

    @property
    def config_params(self) -> dict:
        return self._config_params

    # TODO: <Alex>Add typehints throughout.</Alex>
    @property
    def sorters(self) -> Union[List[Sorter], None]:
        if self._sorters:
            return [self.get_sorter(name=sorter_config["name"]) for sorter_config in self._sorters]
        return None

    # TODO: <Alex>Add typehints throughout</Alex>
    def get_sorter(self, name):
        """Get the (named) Sorter from a DataConnector)

        Args:
            name (str): name of Sorter

        Returns:
            Sorter (Sorter)
        """
        # TODO: <Alex>This could be made more efficient, but numbers of sorters is small and this pattern is useful.</Alex>
        if name in self._sorters_cache:
            return self._sorters_cache[name]
        else:
            sorter_names: list = [sorter_config["name"] for sorter_config in self._sorters]
            if name in sorter_names:
                sorter_config: dict = copy.deepcopy(
                    self._sorters[sorter_names.index(name)]
                )
            else:
                raise ValueError(
                    f'Unable to load sorter with the name "{name}" -- no configuration found or invalid configuration.'
                )
        sorter_config: CommentedMap = sorterConfigSchema.load(
            sorter_config
        )
        sorter: Sorter = self._build_sorter_from_config(
            name=name, config=sorter_config
        )
        self._sorters_cache[name] = sorter
        return sorter

    # TODO: <Alex>This is a good place to check that all defaults from base.py / Config Schemas are set properly.</Alex>
    @staticmethod
    def _build_sorter_from_config(name, config):
        """Build a Sorter using the provided configuration and return the newly-built Sorter."""
        # We convert from the type back to a dictionary for purposes of instantiation
        if isinstance(config, SorterConfig):
            config = sorterConfigSchema.dump(config)
        config.update({"name": name})
        sorter = instantiate_class_from_config(
            config=config,
            runtime_environment={},
            config_defaults={
                "module_name": "great_expectations.execution_environment.data_connector.partitioner.sorter"
            },
        )
        if not sorter:
            raise ClassInstantiationError(
                module_name="great_expectations.execution_environment.data_connector.partitioner.sorter",
                package_name=None,
                class_name=config["class_name"],
            )
        return sorter

    def get_sorted_partitions(self, partitions: List[Partition]) -> List[Partition]:
        sorters: Iterator[Sorter] = reversed(self.sorters)
        for sorter in sorters:
            partitions = sorter.get_sorted_partitions(partitions=partitions)
        return partitions

    def get_available_partitions(self, partition_name: str = None, data_asset_name: str = None) -> List[Partition]:
        raise NotImplementedError

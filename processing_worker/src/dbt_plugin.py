from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pyarrow as pa
from dbt.adapters.duckdb.plugins import BasePlugin
from dbt.adapters.duckdb.utils import TargetConfig

from .config import Settings, create_duckdb_connection
from .delta_ops import merge_delta


def _options(target_config: TargetConfig) -> Mapping[str, Any]:
    target_options = getattr(target_config, "options", None)
    if isinstance(target_options, Mapping):
        return target_options

    config = target_config.config
    if isinstance(config, Mapping):
        nested_options = config.get("delta_merge_options")
        if isinstance(nested_options, Mapping):
            return nested_options

    get_value = getattr(config, "get", None)
    if callable(get_value):
        nested_options = get_value("delta_merge_options")
        if isinstance(nested_options, Mapping):
            return nested_options
    raise TypeError("dbt model config must provide delta_merge_options")


class DeltaMergePlugin(BasePlugin):
    def initialize(self, plugin_config: dict[str, Any]) -> None:
        del plugin_config
        self.settings = Settings()

    def store(self, target_config: TargetConfig, df: pa.Table | None = None) -> None:
        options = _options(target_config)
        location = options.get("location")
        key_columns = options.get("key_columns")
        partition_by = options.get("partition_by", [])
        if not isinstance(location, str) or not location:
            raise ValueError("Delta merge plugin requires delta_merge_options.location")
        if not isinstance(key_columns, list) or not all(
            isinstance(column, str) and column for column in key_columns
        ):
            raise ValueError("Delta merge plugin requires a list of key_columns")
        if not isinstance(partition_by, list) or not all(
            isinstance(column, str) and column for column in partition_by
        ):
            raise ValueError(
                "Delta merge plugin partition_by must be a list of columns"
            )

        connection = create_duckdb_connection(self.settings)
        try:
            if df is None:
                file_location = target_config.location
                if file_location is None or file_location.format != "parquet":
                    raise ValueError(
                        "Delta merge plugin requires dbt external Parquet output"
                    )
                df = connection.execute(
                    "SELECT * FROM read_parquet(?)", [file_location.path]
                ).to_arrow_table()
        finally:
            connection.close()

        if df is None:
            raise RuntimeError("DuckDB did not return the model's Parquet data")
        if (
            df.num_rows == 1
            and df.num_columns
            and all(df.column(index).null_count == 1 for index in range(df.num_columns))
        ):
            df = df.slice(0, 0)

        merge_delta(df, location, key_columns, partition_by, self.settings)


Plugin = DeltaMergePlugin

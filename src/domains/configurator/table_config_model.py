# table_config_model.py
from dataclasses import dataclass

@dataclass
class ColumnConfig:
    name: str
    db_type: str
    size: str | None = None
    nullable: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: str | None = None
    default: str | None = None
    label: str | None = None
    function: str | None = None


@dataclass
class TableConfig:
    name: str
    columns: list[ColumnConfig]

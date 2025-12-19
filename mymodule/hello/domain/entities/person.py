from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Person:
    name: str = field(init=True)
    age: Optional[int] = None
    address: Optional[str] = None

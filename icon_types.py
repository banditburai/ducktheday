# Generated file - do not edit directly

from typing import Protocol
from ft_icon.icon import Icon

class IconClass(Protocol):
    """Available icon methods"""
    @classmethod
    def edit(cls, *args, **kwargs) -> Icon: ...

# Type hint for Icon class
IconType = IconClass

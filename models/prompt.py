from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Prompt(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)

    # Zusatzinfos
    description: str = ""
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    version: str = "v1.0"
    sample_output: str = ""
    related_ids: List[int] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

"""Схемы входящих запросов (Pydantic v2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ResourceKind = Literal["course", "lesson", "material", "portal", "page", "other"]
TriageStatus = Literal["open", "in_progress", "fixed", "wontfix", "false_positive"]
Schedule = Literal["off", "daily", "weekly"]
AuditStatus = Literal["pass", "fail", "na"]
MAX_HTML_CHARS = 3_000_000


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _check_url(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if not value.lower().startswith(("http://", "https://")) or len(value) > 2000:
        raise ValueError("Нужен адрес, начинающийся с http:// или https://")
    return value


class CollectionIn(_Base):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)


class CollectionPatch(_Base):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class ResourceIn(_Base):
    title: str = Field(min_length=1, max_length=200)
    kind: ResourceKind = "page"
    url: str | None = None
    html: str | None = Field(default=None, max_length=MAX_HTML_CHARS)
    collection_id: int | None = None
    notes: str = Field(default="", max_length=2000)
    schedule: Schedule = "off"

    _url = field_validator("url")(_check_url)

    @model_validator(mode="after")
    def _need_source(self) -> "ResourceIn":
        if not self.url and not (self.html and self.html.strip()):
            raise ValueError("Укажите адрес страницы или вставьте HTML")
        return self


class ResourcePatch(_Base):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kind: ResourceKind | None = None
    url: str | None = None
    html: str | None = Field(default=None, max_length=MAX_HTML_CHARS)
    collection_id: int | None = None
    notes: str | None = Field(default=None, max_length=2000)
    schedule: Schedule | None = None

    _url = field_validator("url")(_check_url)


class SaveAs(_Base):
    title: str = Field(min_length=1, max_length=200)
    kind: ResourceKind = "page"
    collection_id: int | None = None


class ScanIn(_Base):
    url: str | None = None
    html: str | None = Field(default=None, max_length=MAX_HTML_CHARS)
    resource_id: int | None = None
    save_as: SaveAs | None = None

    _url = field_validator("url")(_check_url)

    @model_validator(mode="after")
    def _one_source(self) -> "ScanIn":
        sources = [bool(self.url), bool(self.html and self.html.strip()), self.resource_id is not None]
        if sum(sources) != 1:
            raise ValueError("Передайте ровно одно: url, html или resource_id")
        if self.save_as and self.resource_id is not None:
            raise ValueError("save_as нельзя сочетать с resource_id")
        return self


class BatchIn(_Base):
    resource_ids: list[int] | None = Field(default=None, max_length=200)
    collection_id: int | None = None

    @model_validator(mode="after")
    def _one(self) -> "BatchIn":
        if (self.resource_ids is None) == (self.collection_id is None):
            raise ValueError("Передайте resource_ids или collection_id")
        return self


class TriageIn(_Base):
    status: TriageStatus
    note: str = Field(default="", max_length=500)


class ContrastIn(_Base):
    fg: str = Field(min_length=1, max_length=80)
    bg: str = Field(min_length=1, max_length=80)


class ReadabilityIn(_Base):
    text: str | None = Field(default=None, max_length=400_000)
    html: str | None = Field(default=None, max_length=MAX_HTML_CHARS)
    resource_id: int | None = None
    lang: Literal["ru", "en"] | None = None

    @model_validator(mode="after")
    def _one(self) -> "ReadabilityIn":
        if sum([bool(self.text and self.text.strip()), bool(self.html and self.html.strip()), self.resource_id is not None]) != 1:
            raise ValueError("Передайте ровно одно: text, html или resource_id")
        return self


class AuditIn(_Base):
    status: AuditStatus | None
    note: str = Field(default="", max_length=500)


class EventsRead(_Base):
    ids: list[int] | None = Field(default=None, max_length=500)  # None — отметить все


class CrawlDiscoverIn(_Base):
    url: str
    limit: int = Field(default=15, ge=1, le=50)
    depth: int = Field(default=1, ge=1, le=2)

    _url = field_validator("url")(_check_url)

    @field_validator("url")
    @classmethod
    def _required(cls, v: str | None) -> str | None:
        if not v:
            raise ValueError("Укажите адрес сайта")
        return v


class CrawlPage(_Base):
    url: str = Field(max_length=2000)
    title: str = Field(default="", max_length=200)

    _url = field_validator("url")(_check_url)


class CrawlImportIn(_Base):
    pages: list[CrawlPage] = Field(min_length=1, max_length=100)
    collection_id: int | None = None
    collection_name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: ResourceKind = "page"
    scan: bool = True
    schedule: Schedule = "off"

    @model_validator(mode="after")
    def _collection(self) -> "CrawlImportIn":
        if self.collection_id is not None and self.collection_name:
            raise ValueError("Передайте collection_id или collection_name, но не оба")
        return self


class QuizIn(_Base):
    answers: list[int] = Field(max_length=50)


class StatementQuery(_Base):
    organization: str = Field(default="", max_length=160)
    contact: str = Field(default="", max_length=160)

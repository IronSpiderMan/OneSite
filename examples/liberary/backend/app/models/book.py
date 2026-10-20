#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: book.py
# @Date: 2026/4/22 11:21
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Book(SQLModel, table=True):
    __onesite__ = {
        'translations': {
            "en": {
                "fields": {
                    "author_id": "Author"
                }
            },
            "zh": {
                "fields": {
                    "author_id": "作者"
                }
            }
        },
        'importable': True,
        'exportable': True,
        'import_key': 'title'
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(
        unique=True, 
        nullable=False,
        sa_column_kwargs={"info": {"site_props": {
                    "is_search_field": True
                }}}
    )
    published_at: datetime = Field(
        default_factory=datetime.utcnow, 
        sa_column_kwargs={"info": {"site_props": {
                    "permissions": "r",
                    "is_search_field": True
                }}}
    )

    author_id: int = Field(foreign_key="author.id")

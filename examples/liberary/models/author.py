#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: author.py
# @Date: 2026/4/22 11:24
from typing import Optional

from sqlmodel import SQLModel, Field


class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True, 
        nullable=False,
        sa_column_kwargs={"info": {"site_props": {
                    "is_search_field": True
                }}}
    )

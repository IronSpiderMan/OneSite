#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: subject.py
# @Date: 2026/4/23 10:51
from sqlmodel import SQLModel, Field


class BookSubjectLink(SQLModel, table=True):
    __onesite__ = {'is_link_table': True}

    id: int = Field(primary_key=True)

    book_id: int = Field(foreign_key='book.id')
    subject_id: int = Field(foreign_key='subject.id')

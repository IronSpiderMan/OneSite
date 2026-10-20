#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author: ZackFair
# @Desc: 
# @File: subject.py
# @Date: 2026/4/23 10:51
from sqlmodel import SQLModel, Field


class Subject(SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str = Field(unique=True, nullable=False)

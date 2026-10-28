"""Seed a local demo only; no subscriptions, calls or external notifications."""

import os
from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.db import engine
from app.models.category import Category
from app.models.rule import Rule, RuleSource
from app.models.alarm_record import AlarmRecord, AlarmStatus
from app.models.opcua_server import OpcuaServer
from app.models.opcua_node import OpcuaNode
from app.models.opcua_ac import OpcuaAc

NAMESPACE = "urn:onesite:alarmhub:demo"


def address(identifier):
    return f"nsu={NAMESPACE};s={identifier}"


async def init_resources(app: FastAPI) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        if (
            await session.exec(select(OpcuaServer).where(OpcuaServer.title == "本地锅炉 OPC UA"))
        ).first():
            return
        server = OpcuaServer(
            title="本地锅炉 OPC UA",
            endpoint=os.getenv("ALARMHUB_OPCUA_ENDPOINT", "opc.tcp://127.0.0.1:14860/alarmhub/"),
            description="示例模拟锅炉；Browse 中可继续添加压力、运行状态与高压条件",
        )
        category = Category(title="锅炉运行告警")
        session.add_all([server, category])
        await session.flush()
        node = OpcuaNode(
            title="锅炉温度", opcua_server_id=server.id, nodeid=address("Boiler01.Temperature")
        )
        ac = OpcuaAc(
            title="锅炉高温条件",
            opcua_server_id=server.id,
            condition_id=address("Boiler01.HighTemperature"),
        )
        session.add_all([node, ac])
        await session.flush()
        value_rule = Rule(
            title="锅炉温度阈值",
            category_id=category.id,
            source_type=RuleSource.value,
            opcua_node_id=node.id,
            threshold=80,
        )
        ac_rule = Rule(
            title="锅炉原生高温告警",
            category_id=category.id,
            source_type=RuleSource.ac,
            opcua_ac_id=ac.id,
        )
        session.add_all([value_rule, ac_rule])
        await session.flush()
        session.add(
            AlarmRecord(
                title="示例：锅炉温度告警已恢复",
                rule_id=value_rule.id,
                note="静态演示记录，非实时告警；用于查看 AlarmHub 风格的业务页面。",
                status=AlarmStatus.recovered,
            )
        )
        await session.commit()


async def destroy_resources(app: FastAPI) -> None:
    pass

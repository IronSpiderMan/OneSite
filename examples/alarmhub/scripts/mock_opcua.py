"""Local address space for browsing points and custom A&C condition objects."""

import argparse
import asyncio
from asyncua import Server, ua

NAMESPACE = "urn:onesite:alarmhub:demo"
DEFAULT_ENDPOINT = "opc.tcp://127.0.0.1:14860/alarmhub/"


async def make_server(endpoint=DEFAULT_ENDPOINT):
    server = Server()
    await server.init()
    server.set_endpoint(endpoint)
    server.set_server_name("AlarmHub Demo OPC UA")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    ns = await server.register_namespace(NAMESPACE)
    hub = await server.nodes.objects.add_object(ua.NodeId("AlarmHub", ns), "AlarmHub")
    boiler = await hub.add_object(ua.NodeId("Boiler01", ns), "Boiler01")
    await boiler.set_event_notifier([ua.EventNotifier.SubscribeToEvents])
    variables = {}
    for name, value in (("Temperature", 72.5), ("Pressure", 1.25), ("Running", True)):
        variables[name] = await boiler.add_variable(ua.NodeId(f"Boiler01.{name}", ns), name, value)
    condition_type = await server.get_node(ua.ObjectIds.ConditionType).add_object_type(
        ua.NodeId("BoilerAlarmType", ns), "BoilerAlarmType"
    )
    for name in ("HighTemperature", "HighPressure"):
        await boiler.add_object(ua.NodeId(f"Boiler01.{name}", ns), name, condition_type.nodeid)
    return server, variables


async def main(endpoint):
    server, variables = await make_server(endpoint)
    async with server:
        print(f"OPC UA demo ready: {endpoint}", flush=True)
        print(f"Browse: nsu={NAMESPACE};s=Boiler01", flush=True)
        tick = 0
        while True:
            await variables["Temperature"].write_value(72.5 + tick % 12)
            tick += 1
            await asyncio.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    try:
        asyncio.run(main(parser.parse_args().endpoint))
    except KeyboardInterrupt:
        pass

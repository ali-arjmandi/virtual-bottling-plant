"""Where each PLC → bridge value comes from inside the PLC (plc-io.yaml header comment)."""

from __future__ import annotations

from dataclasses import dataclass

from codegen.contracts import Device, Metric, PlcIo, SimSignal, SimUnit

SOURCE_TYPES = {"G_Alarms": "INT", "G_Comms": "BOOL"}


@dataclass(frozen=True)
class Source:
    expr: str      # e.g. G_In.TT202_OutTemp
    st_type: str   # BOOL | INT | UINT | UDINT | REAL | E_*


def sim_signals(units: list[SimUnit]) -> dict[str, SimSignal]:
    return {s.name: s for u in units for s in u.signals}


def metric_source(metric: Metric, device: Device, signals: dict[str, SimSignal]) -> Source:
    for name in (metric.name, f"{device.name}_{metric.name}"):
        if name in signals:
            return Source(signals[name].global_expr, signals[name].st_type)
    if metric.source:
        expr = metric.source.format(device=device.name)
        return Source(expr, "BOOL" if metric.type == "bool" else SOURCE_TYPES[expr.split(".")[0]])
    return Source(f"G_Status.{device.name}.{metric.name}", metric.st_type)


def resolve_status_fields(plc: PlcIo, signals: dict[str, SimSignal]) -> None:
    """Fills Device.status_fields: metrics the PLC logic itself must provide."""
    for device in plc.devices:
        device.status_fields = [
            m for m in device.metrics
            if metric_source(m, device, signals).expr.startswith("G_Status.")
        ]


def status_type_name(device: Device, plc: PlcIo) -> str:
    header_names = {m.name for m in plc.header}
    if device.has_header and {m.name for m in device.status_fields} <= header_names:
        return "ST_PackagingStatus"
    return f"ST_{device.name}Status"


def counter_source(counter: dict, signals: dict[str, SimSignal]) -> Source:
    name = counter["name"]
    if name in signals:
        return Source(signals[name].global_expr, signals[name].st_type)
    return Source(f"G_Counters.{name}", "UDINT")

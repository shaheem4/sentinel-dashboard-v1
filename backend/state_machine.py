"""Temporal NORMAL/WATCH/CRITICAL fusion logic for Sentinel V1."""

from __future__ import annotations

from collections.abc import Mapping


class StateMachine:
    """Require persistence before escalation and one clear reading to recover."""

    def __init__(self, critical_persistence: int = 2) -> None:
        if not isinstance(critical_persistence, int) or isinstance(critical_persistence, bool) or critical_persistence < 1:
            raise ValueError("critical_persistence must be a positive integer")
        self.state = "NORMAL"
        self.critical_persistence = critical_persistence
        self._persistent_anomalies = 0

    def update(self, flags: Mapping[str, bool]) -> str:
        anomaly_count = sum(bool(value) for value in flags.values())
        has_anomaly = anomaly_count > 0
        multi_sensor = anomaly_count >= 2

        if self.state == "NORMAL":
            self.state = "WATCH" if has_anomaly else "NORMAL"
            self._persistent_anomalies = 1 if multi_sensor else 0
        elif self.state == "WATCH":
            if not has_anomaly:
                self.state = "NORMAL"
                self._persistent_anomalies = 0
            elif multi_sensor:
                self._persistent_anomalies += 1
                if self._persistent_anomalies >= self.critical_persistence:
                    self.state = "CRITICAL"
            else:
                self._persistent_anomalies = 0
        else:
            if not has_anomaly:
                self.state = "NORMAL"
                self._persistent_anomalies = 0

        return self.state


def demo_sequence() -> list[str]:
    machine = StateMachine()
    sequence = [
        {},
        {"ml": True},
        {"ml": True, "vibration": True, "acoustic": True},
        {"ml": True, "vibration": True, "acoustic": True},
        {},
    ]
    return [machine.update(flags) for flags in sequence]


if __name__ == "__main__":
    print(" -> ".join(demo_sequence()))

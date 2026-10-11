"""Build the logical circuits and check their ideal splitting probabilities."""

import json
import math
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[1]


def build_circuit(theta_a, theta_b):
    """Prepare a singlet, choose the two measurement settings, then measure."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.x(1)
    circuit.z(0)
    circuit.ry(-2 * theta_a, 0)
    circuit.ry(-2 * theta_b, 1)
    return circuit


def main():
    plan = json.loads((ROOT / 'data/plan.json').read_text())
    for index, setting in enumerate(plan['settings']):
        theta_a, theta_b = setting['theta_a'], setting['theta_b']
        circuit = build_circuit(theta_a, theta_b)
        probabilities = Statevector.from_instruction(circuit).probabilities()

        # B's routing bit is flipped, so raw equal bits mean different servers.
        split_probability = float(probabilities[0] + probabilities[3])
        angle_a, angle_b = -2 * theta_a, -2 * theta_b
        expected = math.sin((angle_a - angle_b) / 2) ** 2
        if abs(split_probability - expected) >= 1e-12:
            raise ValueError(f'Circuit probability mismatch at setting {index}')

        circuit.measure([0, 1], [0, 1])
        if index == 0:
            print(circuit.draw(output='text'))
        print(
            'block', setting['block'],
            'inputs', setting['input_a'], setting['input_b'],
            'ideal split', split_probability,
        )
    print('All eight logical circuits verified. B is flipped after measurement.')


if __name__ == '__main__':
    main()

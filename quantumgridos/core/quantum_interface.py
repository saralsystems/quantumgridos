"""
QuantumGridOS - Main Interface Module
Real-time quantum-power systems integration
"""

import asyncio
import struct
import time
import numpy as np
from typing import Dict, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass
import logging
from queue import Queue
import json

logger = logging.getLogger(__name__)


@dataclass
class PowerSystemData:
    """Container for power system measurements"""

    timestamp: float
    bus_voltages: np.ndarray
    bus_angles: np.ndarray
    line_flows: np.ndarray
    generator_outputs: np.ndarray
    load_demands: np.ndarray

    def to_bytes(self) -> bytes:
        """Serialize to binary format for TCP transmission"""
        header = struct.pack("!dI", self.timestamp, len(self.bus_voltages))
        data = np.concatenate(
            [
                self.bus_voltages,
                self.bus_angles,
                self.line_flows,
                self.generator_outputs,
                self.load_demands,
            ]
        )
        return header + data.astype(np.float32).tobytes()

    @classmethod
    def from_bytes(cls, data: bytes):
        """Deserialize from binary format"""
        timestamp, n_buses = struct.unpack("!dI", data[:12])
        arrays = np.frombuffer(data[12:], dtype=np.float32)

        # Parse arrays based on expected sizes
        idx = 0
        bus_voltages = arrays[idx : idx + n_buses]
        idx += n_buses
        bus_angles = arrays[idx : idx + n_buses]
        idx += n_buses
        # Continue parsing...

        return cls(
            timestamp=timestamp,
            bus_voltages=bus_voltages,
            bus_angles=bus_angles,
            line_flows=arrays[idx:],
            generator_outputs=np.array([]),
            load_demands=np.array([]),
        )


class TCPPowerStreamHandler:
    """High-performance TCP handler for power systems data"""

    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.buffer_size = 65536  # 64KB buffer
        self._running = False
        self.latency_stats = []

    async def connect(self):
        """Establish TCP connection"""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self._running = True
            logger.info(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close TCP connection"""
        self._running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def receive_data(self) -> PowerSystemData:
        """Receive power system data from TCP stream"""
        if not self.reader:
            raise RuntimeError("Not connected")

        # Read header first (12 bytes)
        header = await self.reader.readexactly(12)
        timestamp, data_size = struct.unpack("!dI", header)

        # Read remaining data
        data = await self.reader.readexactly(data_size)

        # Track latency
        current_time = time.time()
        latency = current_time - timestamp
        self.latency_stats.append(latency)

        return PowerSystemData.from_bytes(header + data)

    async def send_result(self, result: Dict[str, Any]):
        """Send quantum computation result back"""
        if not self.writer:
            raise RuntimeError("Not connected")

        # Add timestamp
        result["timestamp"] = time.time()

        # Serialize
        data = json.dumps(result).encode()
        size = len(data)

        # Send size header then data
        self.writer.write(struct.pack("!I", size))
        self.writer.write(data)
        await self.writer.drain()

    async def stream(self) -> AsyncIterator[PowerSystemData]:
        """Async generator for continuous data streaming"""
        while self._running:
            try:
                data = await self.receive_data()
                yield data
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(0.01)  # Brief pause on error


class QuantumPowerInterface:
    """Main interface for quantum-power systems integration"""

    def __init__(
        self,
        quantum_backend: str = "qiskit_aer",
        tcp_host: str = "localhost",
        tcp_port: int = 5000,
        buffer_size: int = 100,
    ):

        self.quantum_backend = self._init_quantum_backend(quantum_backend)
        self.tcp_handler = TCPPowerStreamHandler(tcp_host, tcp_port)

        # Circular buffer for time synchronization
        self.data_buffer = []
        self.buffer_size = buffer_size
        self.result_queue = asyncio.Queue()

        # Time sync parameters
        self.time_offset = 0.0
        self.avg_quantum_delay = 0.0
        self.sync_alpha = 0.1  # EMA smoothing factor

    def _init_quantum_backend(self, backend_name: str):
        """Initialize quantum computing backend"""
        if backend_name == "qiskit_aer":
            from qiskit import Aer

            return Aer.get_backend("aer_simulator")
        elif backend_name == "ionq":
            # IonQ backend initialization
            pass
        elif backend_name == "rigetti":
            # Rigetti backend initialization
            pass
        else:
            raise ValueError(f"Unknown backend: {backend_name}")

    async def start(self):
        """Start the interface"""
        await self.tcp_handler.connect()

    async def stop(self):
        """Stop the interface"""
        await self.tcp_handler.disconnect()

    async def process_with_quantum(
        self, data: PowerSystemData, algorithm: str = "qaoa", **kwargs
    ) -> Dict[str, Any]:
        """Process power system data with quantum algorithm"""

        start_time = time.time()

        # Encode power system state to quantum
        quantum_state = self.encode_to_quantum(data)

        # Run quantum algorithm
        if algorithm == "qaoa":
            result = await self.run_qaoa_async(quantum_state, **kwargs)
        elif algorithm == "vqe":
            result = await self.run_vqe_async(quantum_state, **kwargs)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Decode result
        power_result = self.decode_to_power(result)

        # Update time sync statistics
        quantum_time = time.time() - start_time
        self.update_time_sync(quantum_time)

        return {
            "result": power_result,
            "quantum_time": quantum_time,
            "timestamp": data.timestamp,
            "algorithm": algorithm,
        }

    def encode_to_quantum(self, data: PowerSystemData) -> np.ndarray:
        """Encode power system data to quantum state

        Uses amplitude encoding for efficiency:
        - Normalize power system state vector
        - Map to quantum amplitudes
        """
        # Combine all measurements
        state_vector = np.concatenate(
            [
                data.bus_voltages,
                data.bus_angles / np.pi,  # Normalize angles
                (
                    data.line_flows / np.max(data.line_flows)
                    if np.max(data.line_flows) > 0
                    else data.line_flows
                ),
            ]
        )

        # Normalize for quantum amplitude encoding
        norm = np.linalg.norm(state_vector)
        if norm > 0:
            state_vector = state_vector / norm

        # Pad to nearest power of 2
        n_qubits = int(np.ceil(np.log2(len(state_vector))))
        padded_size = 2**n_qubits

        if len(state_vector) < padded_size:
            state_vector = np.pad(state_vector, (0, padded_size - len(state_vector)))

        return state_vector

    def decode_to_power(self, quantum_result: Dict) -> Dict[str, Any]:
        """Decode quantum result back to power system format"""

        # Extract solution bitstring
        counts = quantum_result.get("counts", {})

        # Find most probable solution
        best_solution = max(counts, key=counts.get) if counts else "0000"

        # Convert to power system decision
        # Example: bitstring represents generator on/off states
        generator_states = [int(bit) for bit in best_solution]

        return {
            "generator_states": generator_states,
            "objective_value": quantum_result.get("eigenvalue", 0),
            "confidence": counts.get(best_solution, 0) / sum(counts.values()) if counts else 0,
        }

    async def run_qaoa_async(self, state: np.ndarray, layers: int = 3) -> Dict:
        """Run QAOA algorithm asynchronously"""
        # This would integrate with actual quantum backend
        # Placeholder for demonstration
        await asyncio.sleep(0.01)  # Simulate quantum execution

        return {"counts": {"0011": 512, "1100": 488}, "eigenvalue": -3.14}

    async def run_vqe_async(self, state: np.ndarray, **kwargs) -> Dict:
        """Run VQE algorithm asynchronously"""
        await asyncio.sleep(0.01)  # Simulate quantum execution

        return {"counts": {"0101": 600, "1010": 400}, "eigenvalue": -2.71}

    def update_time_sync(self, quantum_delay: float):
        """Update time synchronization statistics"""
        # Exponential moving average
        self.avg_quantum_delay = (
            self.sync_alpha * quantum_delay + (1 - self.sync_alpha) * self.avg_quantum_delay
        )

    async def synchronized_stream_processor(self):
        """Process TCP stream with time synchronization"""

        async for data in self.tcp_handler.stream():
            # Add to buffer
            self.data_buffer.append(data)
            if len(self.data_buffer) > self.buffer_size:
                self.data_buffer.pop(0)

            # Process with quantum
            result = await self.process_with_quantum(data)

            # Apply time correction
            result["corrected_timestamp"] = data.timestamp + self.avg_quantum_delay

            # Send back result
            await self.tcp_handler.send_result(result)

            # Store in result queue
            await self.result_queue.put(result)

    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.tcp_handler.latency_stats:
            return {}

        latencies = np.array(self.tcp_handler.latency_stats)
        return {
            "mean": np.mean(latencies),
            "std": np.std(latencies),
            "min": np.min(latencies),
            "max": np.max(latencies),
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99),
        }

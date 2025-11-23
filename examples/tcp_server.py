"""
TCP Server Example for QuantumGridOS
Simulates a power system SCADA/EMS sending real-time data
"""

import asyncio
import struct
import json
import numpy as np
import time
import logging
from typing import Dict, List
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PowerSystemTCPServer:
    """Simulated SCADA/EMS TCP server"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.clients = []
        self.running = False

        # Simulation parameters
        self.n_buses = 14
        self.n_generators = 5
        self.n_lines = 20

        # State variables
        self.time_step = 0
        self.base_load = 250.0  # MW

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection"""

        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected from {addr}")
        self.clients.append(writer)

        try:
            while self.running:
                # Generate power system data
                data = self.generate_power_data()

                # Serialize data
                message = self.serialize_data(data)

                # Send to client
                writer.write(message)
                await writer.drain()

                # Wait for response (quantum result)
                try:
                    response_size = await asyncio.wait_for(reader.readexactly(4), timeout=1.0)
                    size = struct.unpack("!I", response_size)[0]

                    response_data = await reader.readexactly(size)
                    result = json.loads(response_data.decode())

                    logger.info(f"Received quantum result: {result.get('algorithm', 'unknown')}")

                    # Process quantum result (update control actions)
                    self.process_quantum_result(result)

                except asyncio.TimeoutError:
                    pass  # No response yet, continue
                except Exception as e:
                    logger.debug(f"Error reading response: {e}")

                # Update time step
                self.time_step += 1

                # Wait before next update (100ms real-time cycle)
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client disconnected: {addr}")

    def generate_power_data(self) -> Dict:
        """Generate realistic power system measurements"""

        current_time = time.time()

        # Time-varying load pattern (daily cycle)
        hour_of_day = (self.time_step * 0.1 / 3600) % 24
        load_factor = 0.7 + 0.3 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)

        # Bus voltages (p.u.)
        bus_voltages = np.random.normal(1.0, 0.02, self.n_buses)
        bus_voltages = np.clip(bus_voltages, 0.95, 1.05)

        # Bus angles (radians)
        bus_angles = np.random.normal(0, 0.1, self.n_buses)
        bus_angles[0] = 0  # Slack bus

        # Line flows (MW)
        line_flows = np.random.normal(50, 20, self.n_lines) * load_factor

        # Generator outputs (MW)
        generator_outputs = np.array(
            [
                100 * load_factor,  # Base load
                80 * load_factor,  # Intermediate
                60 * load_factor,  # Peaking
                150,  # Nuclear (constant)
                30 * np.random.random(),  # Renewable (variable)
            ]
        )

        # Load demands (MW)
        load_demands = np.random.normal(
            self.base_load * load_factor / self.n_buses, 10, self.n_buses
        )

        return {
            "timestamp": current_time,
            "time_step": self.time_step,
            "bus_voltages": bus_voltages.tolist(),
            "bus_angles": bus_angles.tolist(),
            "line_flows": line_flows.tolist(),
            "generator_outputs": generator_outputs.tolist(),
            "load_demands": load_demands.tolist(),
            "total_load": float(np.sum(load_demands)),
            "frequency": 50.0 + np.random.normal(0, 0.01),  # Hz
        }

    def serialize_data(self, data: Dict) -> bytes:
        """Serialize data for TCP transmission"""

        # Simple format: timestamp + arrays
        timestamp = data["timestamp"]

        # Flatten all arrays
        arrays = np.concatenate(
            [
                np.array(data["bus_voltages"]),
                np.array(data["bus_angles"]),
                np.array(data["line_flows"]),
                np.array(data["generator_outputs"]),
                np.array(data["load_demands"]),
            ]
        )

        # Pack header
        header = struct.pack("!dI", timestamp, len(arrays))

        # Pack data
        body = arrays.astype(np.float32).tobytes()

        return header + body

    def process_quantum_result(self, result: Dict):
        """Process quantum optimization result"""

        if "generator_states" in result["result"]:
            states = result["result"]["generator_states"]
            logger.info(f"Generator commitment: {states}")

            # Update generator setpoints based on quantum result
            # In real system, would send control commands

        if "partition" in result["result"]:
            partition = result["result"]["partition"]
            logger.info(
                f"Network partition updated: Area 1: {len(partition.get('set_1', []))} buses"
            )

    async def start(self):
        """Start TCP server"""

        self.running = True
        server = await asyncio.start_server(self.handle_client, self.host, self.port)

        addr = server.sockets[0].getsockname()
        logger.info(f"Power System TCP Server running on {addr[0]}:{addr[1]}")

        async with server:
            await server.serve_forever()

    def stop(self):
        """Stop server"""
        self.running = False
        logger.info("Stopping server...")


class PowerSystemDataGenerator:
    """Generate realistic power system scenarios"""

    def __init__(self):
        self.scenarios = {
            "normal": self.normal_operation,
            "peak_load": self.peak_load_scenario,
            "contingency": self.contingency_scenario,
            "renewable_ramp": self.renewable_ramp_scenario,
        }

    def normal_operation(self, t: float) -> Dict:
        """Normal operating conditions"""
        return {"load_factor": 0.7 + 0.1 * np.sin(t), "renewable_output": 0.3, "contingency": False}

    def peak_load_scenario(self, t: float) -> Dict:
        """Peak load conditions"""
        return {
            "load_factor": 0.95 + 0.05 * np.sin(t),
            "renewable_output": 0.1,
            "contingency": False,
        }

    def contingency_scenario(self, t: float) -> Dict:
        """N-1 contingency (line or generator outage)"""
        return {
            "load_factor": 0.8,
            "renewable_output": 0.2,
            "contingency": True,
            "outage_element": "Line_5" if t % 10 < 5 else "Gen_2",
        }

    def renewable_ramp_scenario(self, t: float) -> Dict:
        """Rapid renewable generation change"""
        return {
            "load_factor": 0.75,
            "renewable_output": 0.5 + 0.4 * np.sin(10 * t),  # Fast ramping
            "contingency": False,
        }

    def get_scenario(self, name: str, t: float) -> Dict:
        """Get scenario data"""
        if name in self.scenarios:
            return self.scenarios[name](t)
        return self.normal_operation(t)


async def test_client():
    """Test client for debugging"""

    reader, writer = await asyncio.open_connection("127.0.0.1", 5000)
    logger.info("Test client connected")

    try:
        while True:
            # Read data from server
            header = await reader.readexactly(12)
            timestamp, size = struct.unpack("!dI", header)

            data = await reader.readexactly(size * 4)  # float32
            arrays = np.frombuffer(data, dtype=np.float32)

            logger.info(f"Received data at {timestamp}: {len(arrays)} values")

            # Send mock quantum result
            result = {
                "timestamp": timestamp,
                "algorithm": "qaoa",
                "result": {"generator_states": [1, 0, 1, 1, 0], "objective_value": -123.45},
            }

            response = json.dumps(result).encode()
            writer.write(struct.pack("!I", len(response)))
            writer.write(response)
            await writer.drain()

            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="QuantumGridOS TCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=5000, help="Port number")
    parser.add_argument("--client", action="store_true", help="Run test client")

    args = parser.parse_args()

    if args.client:
        # Run test client
        asyncio.run(test_client())
    else:
        # Run server
        server = PowerSystemTCPServer(args.host, args.port)

        try:
            asyncio.run(server.start())
        except KeyboardInterrupt:
            server.stop()
            logger.info("Server stopped")


if __name__ == "__main__":
    main()

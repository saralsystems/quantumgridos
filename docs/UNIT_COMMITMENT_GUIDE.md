# Unit Commitment Optimization with QuantumGridOS

This guide demonstrates how to solve unit commitment problems using QuantumGridOS's quantum optimization algorithms.

## Overview

Unit commitment (UC) is a fundamental problem in power systems operations that determines which generators should be online (committed) and their output levels to meet electricity demand at minimum cost while satisfying operational constraints.

## Problem Formulation

### Objective
Minimize total generation cost:
```
min Σ (generation_cost + startup_cost)
```

### Constraints
- **Power balance**: Total generation = Demand
- **Generator limits**: pmin ≤ output ≤ pmax
- **Minimum up/down time**: Generators must stay on/off for minimum periods
- **Ramp rates**: Limited rate of power output change
- **Reserve requirements**: Extra capacity for reliability

## Example Usage

### Basic Single-Period Optimization

```python
from quantumgridos.algorithms.qaoa import PowerSystemQAOA, QAOAConfig

# Define generators
generators = [
    {
        "name": "Coal_Plant",
        "pmin": 100,
        "pmax": 400,
        "cost": 25,  # $/MWh
        "startup_cost": 5000,
        "bus": 1
    },
    {
        "name": "Gas_CCGT",
        "pmin": 50,
        "pmax": 250,
        "cost": 45,
        "startup_cost": 2000,
        "bus": 2
    },
    # ... more generators
]

# Set demand
demand = 500  # MW

# Configure and solve
qaoa = PowerSystemQAOA(QAOAConfig(layers=3, optimizer="COBYLA"))
result = qaoa.solve_unit_commitment(generators, demand)

# View results
print(f"Total cost: ${result['total_cost']:.2f}")
print(f"Total generation: {result['total_output']:.1f} MW")

for gen in result['schedule']:
    if gen['status']:
        print(f"{gen['generator']}: {gen['output']:.1f} MW @ ${gen['cost']:.2f}")
```

### Multi-Period Optimization

```python
# Create 24-hour demand profile
demand_profile = [
    360, 350, 340, 330, 340, 360,  # Night (low)
    420, 480, 540, 580, 600, 590,  # Morning ramp
    570, 550, 540, 550, 570, 630,  # Afternoon
    660, 650, 600, 550, 490, 420   # Evening peak & decline
]

# Solve for each hour
results = []
for hour, demand in enumerate(demand_profile):
    result = qaoa.solve_unit_commitment(generators, demand)
    results.append(result)
    print(f"Hour {hour}: Cost ${result['total_cost']:.2f}")
```

## Generator Types

The example includes realistic generator types:

### 1. **Coal Plants**
- Base load generation
- Low cost, high startup cost
- Slow ramp rates
- High minimum output

### 2. **Combined Cycle Gas Turbines (CCGT)**
- Mid-merit generation
- Moderate cost and flexibility
- Good ramp rates

### 3. **Gas Peakers**
- Peak load generation
- High cost, low startup cost
- Fast ramp rates
- Low minimum output

### 4. **Nuclear**
- Base load generation
- Very low cost, very high startup cost
- Very slow ramp rates
- Must run continuously

### 5. **Renewables (Wind/Solar)**
- Zero marginal cost
- Variable availability
- No startup costs
- Fast response

## Running the Example

```bash
# Activate virtual environment
source venv_311/bin/activate

# Run the example
python examples/unit_commitment_example.py
```

## Expected Output

```
============================================================
     QuantumGridOS - Unit Commitment Optimization
============================================================

System Configuration:
  Total generators: 9
  Total capacity: 2200.0 MW
  Peak demand: 660.0 MW
  Minimum demand: 360.0 MW

============================================================
Solving Unit Commitment: Evening Peak (Hour 18)
Demand: 660.0 MW
============================================================

Optimization Results:
  Total Generation: 680.5 MW
  Total Cost: $18,450.00
  Demand Met: True
  Reserve Margin: 20.5 MW

Generator Schedule:
  Generator             Status   Output (MW)  Cost ($)
  ------------------------------------------------------------
  Coal_Plant_1          ON       350.0        8750.00
  Gas_CCGT_1            ON       200.0        9000.00
  Gas_Peaker_1          ON       80.0         5200.00
  Nuclear_Plant         ON       50.0         750.00
  ...
```

## Customization

### Adjust QAOA Parameters

```python
qaoa_config = QAOAConfig(
    layers=5,           # More layers = better solution quality
    optimizer="COBYLA", # COBYLA, SPSA, or ADAM
    shots=4096,         # More shots = better statistics
    max_iter=200        # More iterations = better convergence
)
```

### Add Custom Constraints

Modify the generator definitions to include:
- Emission limits
- Fuel constraints
- Maintenance schedules
- Reserve requirements

### Scale the Problem

- **Small system**: 3-5 generators, single period
- **Medium system**: 5-10 generators, multiple periods
- **Large system**: 10+ generators, 24-hour optimization

## Performance Notes

- **Quantum advantage**: Most evident for 10+ generators
- **Computation time**: Increases with problem size and QAOA layers
- **Solution quality**: Improves with more shots and iterations
- **Classical comparison**: Use for benchmarking against classical solvers

## Troubleshooting

### Issue: "Demand not met"
- Check total capacity vs. demand
- Verify generator pmin/pmax values
- Increase reserve margin

### Issue: Slow optimization
- Reduce QAOA layers (try 2-3)
- Reduce shots (try 1024)
- Reduce max_iter (try 50-100)

### Issue: High costs
- Review generator cost parameters
- Check if expensive peakers are being used
- Verify demand profile is realistic

## Next Steps

1. **Integrate with real data**: Load actual generator specs and demand forecasts
2. **Add constraints**: Implement ramp rates, minimum up/down times
3. **Multi-objective**: Balance cost vs. emissions
4. **Stochastic UC**: Handle demand and renewable uncertainty
5. **Real-time**: Connect to live power system data

## References

- [Unit Commitment Problem](https://en.wikipedia.org/wiki/Unit_commitment_problem_in_electrical_power_production)
- [QAOA Algorithm](https://arxiv.org/abs/1411.4028)
- [Power Systems Optimization](https://www.springer.com/gp/book/9780387296982)

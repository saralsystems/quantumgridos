#!/usr/bin/env python3
"""
Unit Commitment Optimization Example
Demonstrates how to solve a unit commitment problem using QuantumGridOS
"""

import numpy as np
from quantumgridos.algorithms.qaoa import PowerSystemQAOA, QAOAConfig
from quantumgridos.power_systems.network import PowerNetwork
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_realistic_generators():
    """
    Create a realistic set of generators with different characteristics
    
    Returns:
        List of generator dictionaries with technical and economic parameters
    """
    generators = [
        {
            "name": "Coal_Plant_1",
            "type": "coal",
            "pmin": 100,      # Minimum power output (MW)
            "pmax": 400,      # Maximum power output (MW)
            "cost": 25,       # Cost per MWh ($)
            "startup_cost": 5000,  # Startup cost ($)
            "min_uptime": 4,  # Minimum up time (hours)
            "min_downtime": 4,  # Minimum down time (hours)
            "ramp_rate": 50,  # MW per hour
            "bus": 1
        },
        {
            "name": "Coal_Plant_2",
            "type": "coal",
            "pmin": 80,
            "pmax": 350,
            "cost": 28,
            "startup_cost": 4500,
            "min_uptime": 4,
            "min_downtime": 4,
            "ramp_rate": 45,
            "bus": 2
        },
        {
            "name": "Gas_CCGT_1",
            "type": "gas_ccgt",
            "pmin": 50,
            "pmax": 250,
            "cost": 45,
            "startup_cost": 2000,
            "min_uptime": 2,
            "min_downtime": 2,
            "ramp_rate": 80,
            "bus": 3
        },
        {
            "name": "Gas_CCGT_2",
            "type": "gas_ccgt",
            "pmin": 50,
            "pmax": 250,
            "cost": 48,
            "startup_cost": 2000,
            "min_uptime": 2,
            "min_downtime": 2,
            "ramp_rate": 80,
            "bus": 4
        },
        {
            "name": "Gas_Peaker_1",
            "type": "gas_peaker",
            "pmin": 20,
            "pmax": 100,
            "cost": 65,
            "startup_cost": 500,
            "min_uptime": 1,
            "min_downtime": 1,
            "ramp_rate": 100,
            "bus": 5
        },
        {
            "name": "Gas_Peaker_2",
            "type": "gas_peaker",
            "pmin": 20,
            "pmax": 100,
            "cost": 68,
            "startup_cost": 500,
            "min_uptime": 1,
            "min_downtime": 1,
            "ramp_rate": 100,
            "bus": 6
        },
        {
            "name": "Nuclear_Plant",
            "type": "nuclear",
            "pmin": 200,
            "pmax": 500,
            "cost": 15,
            "startup_cost": 10000,
            "min_uptime": 24,
            "min_downtime": 48,
            "ramp_rate": 20,
            "bus": 7
        },
        {
            "name": "Wind_Farm_1",
            "type": "wind",
            "pmin": 0,
            "pmax": 150,
            "cost": 0,
            "startup_cost": 0,
            "min_uptime": 0,
            "min_downtime": 0,
            "ramp_rate": 150,  # Wind can change quickly
            "bus": 8,
            "availability": 0.35  # 35% capacity factor
        },
        {
            "name": "Solar_Farm_1",
            "type": "solar",
            "pmin": 0,
            "pmax": 100,
            "cost": 0,
            "startup_cost": 0,
            "min_uptime": 0,
            "min_downtime": 0,
            "ramp_rate": 100,
            "bus": 9,
            "availability": 0.25  # 25% capacity factor (averaged over 24h)
        },
    ]
    
    return generators


def create_demand_profile():
    """
    Create a realistic 24-hour demand profile
    
    Returns:
        List of hourly demand values (MW)
    """
    # Typical daily load curve
    base_load = 600  # MW
    
    # Hourly demand pattern (multipliers)
    hourly_pattern = [
        0.70,  # 00:00 - Low overnight demand
        0.65,  # 01:00
        0.62,  # 02:00
        0.60,  # 03:00
        0.62,  # 04:00
        0.68,  # 05:00
        0.78,  # 06:00 - Morning ramp-up
        0.88,  # 07:00
        0.95,  # 08:00
        0.98,  # 09:00
        1.00,  # 10:00 - Peak morning
        0.98,  # 11:00
        0.95,  # 12:00
        0.92,  # 13:00
        0.90,  # 14:00
        0.92,  # 15:00
        0.95,  # 16:00
        1.05,  # 17:00 - Evening peak
        1.10,  # 18:00 - Maximum peak
        1.08,  # 19:00
        1.00,  # 20:00
        0.92,  # 21:00
        0.82,  # 22:00
        0.75,  # 23:00
    ]
    
    demand_profile = [base_load * multiplier for multiplier in hourly_pattern]
    
    return demand_profile


def solve_unit_commitment_single_period(generators, demand, period_name="Period 1"):
    """
    Solve unit commitment for a single time period
    
    Args:
        generators: List of generator dictionaries
        demand: Demand for this period (MW)
        period_name: Name/identifier for this period
        
    Returns:
        Dictionary with solution details
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Solving Unit Commitment: {period_name}")
    logger.info(f"Demand: {demand:.1f} MW")
    logger.info(f"{'='*60}")
    
    # Configure QAOA solver
    qaoa_config = QAOAConfig(
        layers=3,
        optimizer="COBYLA",
        shots=2048,
        max_iter=100
    )
    
    qaoa_solver = PowerSystemQAOA(qaoa_config)
    
    # Solve the unit commitment problem
    result = qaoa_solver.solve_unit_commitment(generators, demand)
    
    # Display results
    logger.info(f"\nOptimization Results:")
    logger.info(f"  Total Generation: {result['total_output']:.1f} MW")
    logger.info(f"  Total Cost: ${result['total_cost']:.2f}")
    logger.info(f"  Demand Met: {result['demand_met']}")
    logger.info(f"  Reserve Margin: {(result['total_output'] - demand):.1f} MW")
    
    logger.info(f"\nGenerator Schedule:")
    logger.info(f"  {'Generator':<20} {'Status':<8} {'Output (MW)':<12} {'Cost ($)':<10}")
    logger.info(f"  {'-'*60}")
    
    for gen_schedule in result['schedule']:
        status = "ON" if gen_schedule['status'] else "OFF"
        output = f"{gen_schedule['output']:.1f}" if gen_schedule['status'] else "0.0"
        cost = f"{gen_schedule['cost']:.2f}" if gen_schedule['status'] else "0.00"
        logger.info(f"  {gen_schedule['generator']:<20} {status:<8} {output:<12} {cost:<10}")
    
    return result


def solve_unit_commitment_multi_period(generators, demand_profile, selected_hours=None):
    """
    Solve unit commitment for multiple time periods
    
    Args:
        generators: List of generator dictionaries
        demand_profile: List of hourly demand values
        selected_hours: List of hour indices to solve (None = all hours)
        
    Returns:
        List of results for each period
    """
    if selected_hours is None:
        selected_hours = range(len(demand_profile))
    
    results = []
    total_cost = 0
    
    for hour in selected_hours:
        demand = demand_profile[hour]
        period_name = f"Hour {hour:02d}:00"
        
        result = solve_unit_commitment_single_period(
            generators, 
            demand, 
            period_name
        )
        
        results.append({
            'hour': hour,
            'demand': demand,
            'result': result
        })
        
        total_cost += result['total_cost']
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Multi-Period Summary")
    logger.info(f"{'='*60}")
    logger.info(f"Total periods solved: {len(selected_hours)}")
    logger.info(f"Total cost: ${total_cost:.2f}")
    logger.info(f"Average cost per period: ${total_cost/len(selected_hours):.2f}")
    
    return results


def analyze_generation_mix(results):
    """
    Analyze the generation mix across all periods
    
    Args:
        results: List of period results
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Generation Mix Analysis")
    logger.info(f"{'='*60}")
    
    # Aggregate statistics by generator type
    type_stats = {}
    
    for period_result in results:
        for gen_schedule in period_result['result']['schedule']:
            gen_name = gen_schedule['generator']
            
            # Find generator type
            gen_type = "unknown"
            for gen in create_realistic_generators():
                if gen['name'] == gen_name:
                    gen_type = gen['type']
                    break
            
            if gen_type not in type_stats:
                type_stats[gen_type] = {
                    'total_output': 0,
                    'total_cost': 0,
                    'hours_online': 0
                }
            
            if gen_schedule['status']:
                type_stats[gen_type]['total_output'] += gen_schedule['output']
                type_stats[gen_type]['total_cost'] += gen_schedule['cost']
                type_stats[gen_type]['hours_online'] += 1
    
    logger.info(f"\n{'Type':<15} {'Total Output (MWh)':<20} {'Total Cost ($)':<15} {'Hours Online':<15}")
    logger.info(f"{'-'*70}")
    
    for gen_type, stats in sorted(type_stats.items()):
        logger.info(
            f"{gen_type:<15} {stats['total_output']:<20.1f} "
            f"{stats['total_cost']:<15.2f} {stats['hours_online']:<15}"
        )


def main():
    """Main execution function"""
    
    print("\n" + "="*60)
    print("     QuantumGridOS - Unit Commitment Optimization")
    print("="*60)
    
    # Create generators and demand profile
    generators = create_realistic_generators()
    demand_profile = create_demand_profile()
    
    logger.info(f"\nSystem Configuration:")
    logger.info(f"  Total generators: {len(generators)}")
    logger.info(f"  Total capacity: {sum(g['pmax'] for g in generators):.1f} MW")
    logger.info(f"  Peak demand: {max(demand_profile):.1f} MW")
    logger.info(f"  Minimum demand: {min(demand_profile):.1f} MW")
    
    # Example 1: Solve for a single critical period (evening peak)
    logger.info(f"\n{'='*60}")
    logger.info(f"Example 1: Single Period Optimization (Evening Peak)")
    logger.info(f"{'='*60}")
    
    evening_peak_hour = 18  # 6 PM
    evening_demand = demand_profile[evening_peak_hour]
    
    single_result = solve_unit_commitment_single_period(
        generators,
        evening_demand,
        f"Evening Peak (Hour {evening_peak_hour})"
    )
    
    # Example 2: Solve for selected hours throughout the day
    logger.info(f"\n{'='*60}")
    logger.info(f"Example 2: Multi-Period Optimization (Selected Hours)")
    logger.info(f"{'='*60}")
    
    # Solve for key hours: midnight, morning, noon, evening peak, night
    selected_hours = [0, 6, 12, 18, 22]
    
    multi_results = solve_unit_commitment_multi_period(
        generators,
        demand_profile,
        selected_hours
    )
    
    # Analyze generation mix
    analyze_generation_mix(multi_results)
    
    print("\n" + "="*60)
    print("     Optimization Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
